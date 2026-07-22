# -*- coding: utf-8 -*-
"""
virtual_dataframe_table.py
===========================

Production-ready виджет таблицы для отображения больших `pandas.DataFrame`
(15 000 - 100 000+ строк) в PyQt5 с виртуализацией строк (windowing),
плавным попиксельным скроллом и постолбцовой фильтрацией.

Ключевая идея виртуализации:
    QTableView сам по себе не создаёт виджеты на каждую ячейку (в отличие
    от QTableWidget), поэтому он уже "виртуален" на уровне отрисовки.
    Узкое место - модель: если каждый вызов `data()` дёргает
    `DataFrame.iloc[row, col]` напрямую, это медленно на больших объёмах
    из-за накладных расходов pandas на скалярный доступ.

    Решение: модель хранит небольшое "окно" данных (текущий видимый
    диапазон строк + буфер 100-250 строк с каждой стороны) в виде списка
    python-кортежей (полученных через `itertuples`), и обслуживает `data()`
    из этого кэша. Кэш перестраивается только тогда, когда запрошенная
    строка выходит за его границы - как лениво (внутри `data()`), так и
    проактивно (при скролле, через `ensure_cache`).

Фильтры:
    На один столбец можно повесить НЕСКОЛЬКО условий одновременно
    (например, "price больше 100" И "price меньше 500" как два отдельных
    фильтра на одном столбце). Все условия по всем столбцам объединяются
    через AND. Активные фильтры отображаются в виде "чипов" над таблицей -
    каждый можно снять по отдельности одним кликом (быстрое управление).

Классы:
    PandasVirtualModel    - QAbstractTableModel с windowed-кэшем.
    FilterDialog          - диалог добавления условия фильтра для столбца.
    VirtualTableView      - настроенный QTableView + контекстное меню заголовка.
    VirtualDataFrameTable - виджет-контейнер: модель + вид + чипы + статус-бар.
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from PyQt5.QtCore import QAbstractTableModel, QDate, QModelIndex, QRect, QSize, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLayout,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPushButton,
    QSizePolicy,
    QTableView,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetItem,
)


# ======================================================================
# Наборы операций по типу столбца (общие константы для диалога и описаний)
# ======================================================================
TEXT_OPS: List[Tuple[str, str]] = [
    ("содержит", "contains"),
    ("равно", "eq"),
    ("начинается с", "startswith"),
    ("заканчивается на", "endswith"),
    ("не содержит", "not_contains"),
]
NUMERIC_OPS: List[Tuple[str, str]] = [
    ("равно", "eq"),
    ("не равно", "ne"),
    ("больше", "gt"),
    ("меньше", "lt"),
    ("больше или равно", "ge"),
    ("меньше или равно", "le"),
    ("между", "between"),
]
DATE_OPS: List[Tuple[str, str]] = [
    ("после", "after"),
    ("до", "before"),
    ("в эту дату", "on"),
    ("между датами", "between"),
    ("не равно дате", "ne"),
]
_OPS_BY_KIND: Dict[str, List[Tuple[str, str]]] = {"text": TEXT_OPS, "numeric": NUMERIC_OPS, "date": DATE_OPS}


def detect_column_kind(series: pd.Series) -> str:
    """Определить тип столбца: 'date' / 'numeric' / 'text'."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    return "text"


def describe_filter_spec(column: str, spec: Dict[str, Any]) -> str:
    """Короткое человекочитаемое описание фильтра для чипа/тултипа."""
    kind, op, value = spec["type"], spec["op"], spec["value"]
    label = next((lbl for lbl, code in _OPS_BY_KIND[kind] if code == op), op)
    if kind == "text":
        val_str = f'"{value}"'
    elif kind == "numeric":
        val_str = f"{value[0]:g}…{value[1]:g}" if op == "between" else f"{value:g}"
    else:
        val_str = f"{value[0].date()}…{value[1].date()}" if op == "between" else f"{value.date()}"
    return f"{column}: {label} {val_str}"


# ======================================================================
# 1. Модель данных с windowed-кэшем (виртуализация)
# ======================================================================
class PandasVirtualModel(QAbstractTableModel):
    """QAbstractTableModel, обслуживающий большие DataFrame через окно кэша.

    Полный DataFrame хранится в памяти целиком (`self._df`), но `data()`
    никогда не обращается к нему напрямую построчно - вместо этого читает
    из `self._cache_data`: списка кортежей строк в диапазоне
    [`self._cache_start`, `self._cache_end`).

    Кэш перестраивается:
        * лениво - если `data()` запросили строку вне текущего окна;
        * проактивно - методом `ensure_cache(first, last)`, который вызывает
          `VirtualTableView` на каждое событие скролла.

    Args:
        df: исходный DataFrame (индекс будет сброшен на 0..N-1).
        buffer: количество дополнительных строк, подгружаемых с каждой
            стороны видимого диапазона (по умолчанию 150, т.е. в
            рекомендуемых границах 100-250).
    """

    def __init__(self, df: pd.DataFrame, buffer: int = 150, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._buffer: int = buffer
        self._columns: List[str] = []
        self._df: pd.DataFrame = pd.DataFrame()
        self._cache_start: int = 0
        self._cache_end: int = 0
        self._cache_data: List[Tuple[Any, ...]] = []
        self.set_dataframe(df)

    # ------------------------------------------------------------------
    # Управление данными
    # ------------------------------------------------------------------
    def set_dataframe(self, df: pd.DataFrame) -> None:
        """Полностью заменить отображаемый DataFrame (например, после фильтра/сортировки)."""
        self.beginResetModel()
        self._df = df.reset_index(drop=True)
        self._columns = list(self._df.columns)
        self._cache_start = 0
        self._cache_end = 0
        self._cache_data = []
        self._rebuild_cache(0, min(len(self._df), max(1, self._buffer)) - 1 if len(self._df) else -1)
        self.endResetModel()

    def dataframe(self) -> pd.DataFrame:
        """Вернуть текущий (отфильтрованный/отсортированный) DataFrame."""
        return self._df

    # ------------------------------------------------------------------
    # Работа с кэшем ("окном" видимых данных)
    # ------------------------------------------------------------------
    def _rebuild_cache(self, first_row: int, last_row: int) -> None:
        """Перестроить кэш вокруг диапазона [first_row, last_row] с учётом буфера."""
        n = len(self._df)
        if n == 0 or first_row < 0 or last_row < 0:
            self._cache_start = 0
            self._cache_end = 0
            self._cache_data = []
            return
        start = max(0, first_row - self._buffer)
        end = min(n, last_row + self._buffer + 1)  # end - эксклюзивная граница
        chunk = self._df.iloc[start:end]
        # itertuples на срезе быстрее многократных iloc[row, col] на всём df
        self._cache_data = list(chunk.itertuples(index=False, name=None))
        self._cache_start = start
        self._cache_end = end

    def ensure_cache(self, first_visible_row: int, last_visible_row: int) -> None:
        """Проактивно обновить кэш, если видимый диапазон вышел за его границы.

        Вызывается из `VirtualTableView` при каждом событии скролла.
        Если видимый диапазон уже полностью внутри текущего кэша - ничего
        не делает (это и есть условие "обновлять окно только когда
        пользователь выходит за пределы текущего кэша").
        """
        if len(self._df) == 0:
            return
        first_visible_row = max(0, first_visible_row)
        last_visible_row = max(first_visible_row, last_visible_row)
        if first_visible_row >= self._cache_start and last_visible_row < self._cache_end:
            return  # видимая область полностью внутри кэша - ничего не делаем
        self._rebuild_cache(first_visible_row, last_visible_row)

    # ------------------------------------------------------------------
    # Обязательные методы QAbstractTableModel
    # ------------------------------------------------------------------
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._df)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._columns)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row, col = index.row(), index.column()

        if role in (Qt.DisplayRole, Qt.EditRole, Qt.ToolTipRole):
            if not (self._cache_start <= row < self._cache_end):
                # запасной (ленивый) путь, если проактивный кэш не успел обновиться
                self.ensure_cache(row, row)
            local_row = row - self._cache_start
            if not (0 <= local_row < len(self._cache_data)):
                return None
            value = self._cache_data[local_row][col]
            return self._format_value(value)

        if role == Qt.TextAlignmentRole:
            col_name = self._columns[col]
            if pd.api.types.is_numeric_dtype(self._df[col_name]):
                return Qt.AlignRight | Qt.AlignVCenter

        return None

    @staticmethod
    def _format_value(value: Any) -> str:
        """Человекочитаемое строковое представление значения ячейки."""
        if value is None or (isinstance(value, float) and np.isnan(value)) or value is pd.NaT:
            return ""
        if pd.isna(value):
            return ""
        if isinstance(value, pd.Timestamp):
            return value.strftime("%Y-%m-%d")
        if isinstance(value, float):
            return f"{value:,.2f}"
        if isinstance(value, (int, np.integer)):
            return f"{value:,}"
        return str(value)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self._columns[section]
        return str(section + 1)

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable  # без редактирования

    # ------------------------------------------------------------------
    # Сортировка
    # ------------------------------------------------------------------
    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder) -> None:
        if not (0 <= column < len(self._columns)) or self._df.empty:
            return
        self.layoutAboutToBeChanged.emit()
        col_name = self._columns[column]
        ascending = order == Qt.AscendingOrder
        self._df = self._df.sort_values(
            by=col_name, ascending=ascending, kind="mergesort", na_position="last"
        ).reset_index(drop=True)
        self._cache_start = 0
        self._cache_end = 0
        self._cache_data = []
        self._rebuild_cache(0, min(len(self._df), self._buffer) - 1)
        self.layoutChanged.emit()


# ======================================================================
# 2. Диалог добавления условия фильтра (с автоопределением типа столбца)
# ======================================================================
class FilterDialog(QDialog):
    """Диалог добавления ОДНОГО условия фильтра для столбца.

    Тип столбца определяется автоматически по dtype pandas-Series:
        * datetime64[*]  -> набор операций для дат (QDateEdit)
        * числовой dtype -> набор операций для чисел (QDoubleSpinBox)
        * иначе (object/string) -> набор операций для текста (QLineEdit)

    На столбец может быть добавлено сколько угодно условий - диалог всегда
    открывается "с чистого листа" для нового условия; управлять уже
    добавленными условиями (в т.ч. быстро снимать по одному) можно через
    панель чипов в `VirtualDataFrameTable`.

    Результат доступен через `get_filter_spec()` после `exec_() == QDialog.Accepted`.
    """

    def __init__(self, column_name: str, series: pd.Series, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.column_name = column_name
        self.series = series
        self._kind = detect_column_kind(series)
        self._spec: Optional[Dict[str, Any]] = None

        self.setWindowTitle(f"Добавить фильтр: {column_name}")
        self.setMinimumWidth(340)
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        kind_ru = {"date": "дата", "numeric": "число", "text": "текст"}[self._kind]
        layout.addWidget(QLabel(f"Столбец: <b>{self.column_name}</b> ({kind_ru})"))

        self.ops = _OPS_BY_KIND[self._kind]
        self.op_combo = QComboBox()
        for label, code in self.ops:
            self.op_combo.addItem(label, code)
        layout.addWidget(QLabel("Условие:"))
        layout.addWidget(self.op_combo)

        value_row = QHBoxLayout()
        if self._kind == "text":
            self.text_edit = QLineEdit()
            self.text_edit.setPlaceholderText("значение…")
            value_row.addWidget(self.text_edit)
        elif self._kind == "numeric":
            self.num_edit1 = QDoubleSpinBox()
            self.num_edit1.setRange(-1e15, 1e15)
            self.num_edit1.setDecimals(4)
            self.num_edit2 = QDoubleSpinBox()
            self.num_edit2.setRange(-1e15, 1e15)
            self.num_edit2.setDecimals(4)
            self.and_label = QLabel("и")
            value_row.addWidget(self.num_edit1)
            value_row.addWidget(self.and_label)
            value_row.addWidget(self.num_edit2)
        else:  # date
            self.date_edit1 = QDateEdit()
            self.date_edit1.setCalendarPopup(True)
            self.date_edit1.setDisplayFormat("yyyy-MM-dd")
            self.date_edit1.setDate(QDate.currentDate())
            self.date_edit2 = QDateEdit()
            self.date_edit2.setCalendarPopup(True)
            self.date_edit2.setDisplayFormat("yyyy-MM-dd")
            self.date_edit2.setDate(QDate.currentDate())
            self.and_label = QLabel("и")
            value_row.addWidget(self.date_edit1)
            value_row.addWidget(self.and_label)
            value_row.addWidget(self.date_edit2)
        layout.addLayout(value_row)

        self.op_combo.currentIndexChanged.connect(self._update_value_widgets)
        self._update_value_widgets()

        btn_row = QHBoxLayout()
        self.btn_ok = QPushButton("Добавить фильтр")
        self.btn_cancel = QPushButton("Отмена")
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_ok)
        btn_row.addWidget(self.btn_cancel)
        layout.addLayout(btn_row)

        self.btn_ok.clicked.connect(self._on_accept)
        self.btn_cancel.clicked.connect(self.reject)

    def _update_value_widgets(self) -> None:
        """Показывать второе поле ввода только для операции 'между'."""
        code = self.op_combo.currentData()
        is_between = code == "between"
        if self._kind == "numeric":
            self.and_label.setVisible(is_between)
            self.num_edit2.setVisible(is_between)
        elif self._kind == "date":
            self.and_label.setVisible(is_between)
            self.date_edit2.setVisible(is_between)

    # ------------------------------------------------------------------
    def _on_accept(self) -> None:
        code = self.op_combo.currentData()
        if self._kind == "text":
            self._spec = {"type": "text", "op": code, "value": self.text_edit.text()}
        elif self._kind == "numeric":
            if code == "between":
                v1, v2 = self.num_edit1.value(), self.num_edit2.value()
                self._spec = {"type": "numeric", "op": code, "value": (min(v1, v2), max(v1, v2))}
            else:
                self._spec = {"type": "numeric", "op": code, "value": self.num_edit1.value()}
        else:
            if code == "between":
                d1, d2 = self.date_edit1.date().toPyDate(), self.date_edit2.date().toPyDate()
                lo, hi = (d1, d2) if d1 <= d2 else (d2, d1)
                self._spec = {"type": "date", "op": code, "value": (pd.Timestamp(lo), pd.Timestamp(hi))}
            else:
                d = self.date_edit1.date().toPyDate()
                self._spec = {"type": "date", "op": code, "value": pd.Timestamp(d)}
        self.accept()

    def get_filter_spec(self) -> Optional[Dict[str, Any]]:
        """Вернуть спецификацию нового фильтра ({'type','op','value'})."""
        return self._spec


# ======================================================================
# 3. QTableView с настройками производительности и контекстным меню
# ======================================================================
class VirtualTableView(QTableView):
    """QTableView, настроенный под большие данные + меню фильтра на заголовке.

    Сигналы:
        filterRequested(int col): пользователь выбрал "Фильтр…" для столбца col
            (добавление НОВОГО условия - на столбце их может быть несколько).
        resetColumnFilterRequested(int col): "Сбросить фильтр столбца"
            (снимает ВСЕ условия с этого столбца).
        resetAllFiltersRequested(): "Сбросить все фильтры".
    """

    filterRequested = pyqtSignal(int)
    resetColumnFilterRequested = pyqtSignal(int)
    resetAllFiltersRequested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._configure()

    def _configure(self) -> None:
        # Внешний вид / поведение
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionsMovable(True)
        self.horizontalHeader().setStretchLastSection(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.ExtendedSelection)
        self.setEditTriggers(QTableView.NoEditTriggers)  # запрет редактирования

        # Плавный попиксельный скролл
        self.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.setVerticalScrollMode(QTableView.ScrollPerPixel)

        # Контекстное меню заголовка столбцов
        self.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self._on_header_context_menu)

        # Проактивное обновление кэша модели при скролле
        self.verticalScrollBar().valueChanged.connect(self._on_scrolled)

    # ------------------------------------------------------------------
    def setModel(self, model: Optional[QAbstractTableModel]) -> None:
        super().setModel(model)
        # сразу прогреть кэш под текущий видимый диапазон
        self._on_scrolled(0)

    def _on_scrolled(self, _value: int) -> None:
        """Вычислить первую/последнюю видимую строку и попросить модель обновить кэш."""
        model = self.model()
        if model is None or model.rowCount() == 0:
            return
        first_row = self.rowAt(0)
        if first_row == -1:
            first_row = 0
        last_row = self.rowAt(max(0, self.viewport().height() - 1))
        if last_row == -1:
            last_row = model.rowCount() - 1
        model.ensure_cache(first_row, last_row)

    # ------------------------------------------------------------------
    def _on_header_context_menu(self, pos) -> None:
        col = self.horizontalHeader().logicalIndexAt(pos)
        if col < 0:
            return
        menu = QMenu(self)
        act_filter = menu.addAction("Фильтр…")
        act_reset_col = menu.addAction("Сбросить фильтр столбца")
        menu.addSeparator()
        act_reset_all = menu.addAction("Сбросить все фильтры")

        action = menu.exec_(self.horizontalHeader().mapToGlobal(pos))
        if action == act_filter:
            self.filterRequested.emit(col)
        elif action == act_reset_col:
            self.resetColumnFilterRequested.emit(col)
        elif action == act_reset_all:
            self.resetAllFiltersRequested.emit()


# ======================================================================
# 3b. FlowLayout - лейаут с переносом (для панели чипов активных фильтров)
# ======================================================================
class FlowLayout(QLayout):
    """Простой лейаут с автоматическим переносом дочерних виджетов на новую
    строку, когда не хватает ширины. Используется для панели чипов фильтров,
    т.к. количество активных фильтров заранее не известно.
    """

    def __init__(self, parent: Optional[QWidget] = None, margin: int = 0, spacing: int = 6) -> None:
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self._items: List[QWidgetItem] = []

    def addItem(self, item) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientations:
        return Qt.Orientations(Qt.Horizontal)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        x, y = rect.x(), rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self._items:
            widget = item.widget()
            space_x = spacing
            space_y = spacing
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(x, y, item.sizeHint().width(), item.sizeHint().height()))
            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()


class _FilterChip(QFrame):
    """Небольшой "чип" с описанием одного активного фильтра и кнопкой снятия."""

    removed = pyqtSignal()

    def __init__(self, text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("filterChip")
        self.setStyleSheet(
            """
            #filterChip { background: #eef2ff; border: 1px solid #c7d2fe; border-radius: 11px; }
            QLabel { color: #333; font-size: 12px; }
            QToolButton { border: none; color: #667; font-weight: bold; font-size: 12px; }
            QToolButton:hover { color: #c0392b; }
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(9, 3, 4, 3)
        layout.setSpacing(4)
        label = QLabel(text)
        label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        btn = QToolButton()
        btn.setText("✕")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setAutoRaise(True)
        btn.clicked.connect(self.removed.emit)
        layout.addWidget(label)
        layout.addWidget(btn)


# ======================================================================
# 4. Виджет-контейнер: модель + вид + логика фильтрации + панель чипов
# ======================================================================
class VirtualDataFrameTable(QWidget):
    """Готовый к использованию виджет: принимает DataFrame, отображает его
    в виртуализированной таблице с поддержкой сортировки и множественных
    постолбцовых фильтров.

    На один столбец можно повесить несколько условий одновременно (они
    объединяются через AND, как и условия между разными столбцами).
    Все активные фильтры отображаются в виде чипов над таблицей - каждый
    можно быстро снять отдельным кликом, без открытия диалога.

    Пример:
        table = VirtualDataFrameTable(df)
        layout.addWidget(table)
        table.set_dataframe(new_df)  # позже, при желании
    """

    def __init__(self, df: pd.DataFrame, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._df_original: pd.DataFrame = df.reset_index(drop=True)
        # словарь: имя столбца -> список условий (несколько фильтров на столбец)
        self._filters: Dict[str, List[Dict[str, Any]]] = {}

        self.model = PandasVirtualModel(self._df_original)
        self.view = VirtualTableView(self)
        self.view.setModel(self.model)

        self.view.filterRequested.connect(self._show_filter_dialog)
        self.view.resetColumnFilterRequested.connect(self._reset_column_filter)
        self.view.resetAllFiltersRequested.connect(self._reset_all_filters)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #555; padding: 2px 4px;")

        # панель чипов активных фильтров (быстрое управление)
        self.chips_container = QWidget()
        self.chips_layout = FlowLayout(self.chips_container, margin=2, spacing=6)
        self.chips_container.setVisible(False)  # скрыта, пока нет фильтров

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.status_label)
        layout.addWidget(self.chips_container)
        layout.addWidget(self.view)

        self._update_status()

    # ------------------------------------------------------------------
    # Публичное API
    # ------------------------------------------------------------------
    def set_dataframe(self, df: pd.DataFrame) -> None:
        """Заменить исходные данные виджета и сбросить все фильтры."""
        self._df_original = df.reset_index(drop=True)
        self._filters.clear()
        self.model.set_dataframe(self._df_original)
        self._rebuild_chips()
        self._update_status()

    def active_filters(self) -> Dict[str, List[Dict[str, Any]]]:
        """Текущие активные фильтры (для отладки/сохранения состояния)."""
        return {col: list(specs) for col, specs in self._filters.items()}

    # ------------------------------------------------------------------
    # Обработчики контекстного меню заголовка
    # ------------------------------------------------------------------
    def _show_filter_dialog(self, col_index: int) -> None:
        """Открыть диалог добавления НОВОГО условия для столбца."""
        col_name = self._df_original.columns[col_index]
        series = self._df_original[col_name]
        dlg = FilterDialog(col_name, series, self)
        if dlg.exec_() == QDialog.Accepted:
            spec = dlg.get_filter_spec()
            if spec is not None:
                self._filters.setdefault(col_name, []).append(spec)
                self._apply_filters()

    def _reset_column_filter(self, col_index: int) -> None:
        """Снять ВСЕ условия с указанного столбца."""
        col_name = self._df_original.columns[col_index]
        if col_name in self._filters:
            del self._filters[col_name]
            self._apply_filters()

    def _reset_all_filters(self) -> None:
        if self._filters:
            self._filters.clear()
            self._apply_filters()

    def _remove_single_filter(self, col_name: str, spec_index: int) -> None:
        """Быстро снять ОДНО конкретное условие (клик по чипу)."""
        specs = self._filters.get(col_name)
        if not specs or not (0 <= spec_index < len(specs)):
            return
        specs.pop(spec_index)
        if not specs:
            del self._filters[col_name]
        self._apply_filters()

    # ------------------------------------------------------------------
    # Логика применения фильтров
    # ------------------------------------------------------------------
    def _apply_filters(self) -> None:
        df = self._df_original
        if not self._filters:
            filtered = df
        else:
            mask = pd.Series(True, index=df.index)
            for col_name, specs in self._filters.items():
                for spec in specs:
                    mask &= self._build_mask(df[col_name], spec)
            filtered = df[mask]
        self.model.set_dataframe(filtered)
        self._rebuild_chips()
        self._update_status()

    @staticmethod
    def _build_mask(series: pd.Series, spec: Dict[str, Any]) -> pd.Series:
        """Построить булеву маску для одного условия фильтра."""
        kind = spec["type"]
        op = spec["op"]
        value = spec["value"]

        if kind == "text":
            s = series.astype(str).str.lower()
            val = str(value).lower()
            if op == "contains":
                mask = s.str.contains(val, na=False, regex=False)
            elif op == "eq":
                mask = s == val
            elif op == "startswith":
                mask = s.str.startswith(val, na=False)
            elif op == "endswith":
                mask = s.str.endswith(val, na=False)
            elif op == "not_contains":
                mask = ~s.str.contains(val, na=False, regex=False)
            else:
                mask = pd.Series(True, index=series.index)

        elif kind == "numeric":
            s = pd.to_numeric(series, errors="coerce")
            if op == "eq":
                mask = s == value
            elif op == "ne":
                mask = s != value
            elif op == "gt":
                mask = s > value
            elif op == "lt":
                mask = s < value
            elif op == "ge":
                mask = s >= value
            elif op == "le":
                mask = s <= value
            elif op == "between":
                lo, hi = value
                mask = (s >= lo) & (s <= hi)
            else:
                mask = pd.Series(True, index=series.index)

        elif kind == "date":
            s = pd.to_datetime(series, errors="coerce")
            if op == "after":
                mask = s > value
            elif op == "before":
                mask = s < value
            elif op == "on":
                mask = s.dt.date == value.date()
            elif op == "ne":
                mask = s.dt.date != value.date()
            elif op == "between":
                lo, hi = value
                mask = (s >= lo) & (s < hi + pd.Timedelta(days=1))
            else:
                mask = pd.Series(True, index=series.index)
        else:
            mask = pd.Series(True, index=series.index)

        return mask.fillna(False).astype(bool)

    # ------------------------------------------------------------------
    # Панель чипов активных фильтров
    # ------------------------------------------------------------------
    def _rebuild_chips(self) -> None:
        """Перестроить панель чипов под текущий набор активных фильтров."""
        while self.chips_layout.count():
            item = self.chips_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        has_filters = bool(self._filters)
        self.chips_container.setVisible(has_filters)
        if not has_filters:
            return

        for col_name, specs in self._filters.items():
            for i, spec in enumerate(specs):
                chip = _FilterChip(describe_filter_spec(col_name, spec), self.chips_container)
                chip.removed.connect(lambda c=col_name, idx=i: self._remove_single_filter(c, idx))
                self.chips_layout.addWidget(chip)

        if len(self._filters) > 1 or any(len(v) > 1 for v in self._filters.values()):
            clear_all_chip = _FilterChip("Сбросить все ✕✕", self.chips_container)
            clear_all_chip.removed.connect(self._reset_all_filters)
            self.chips_layout.addWidget(clear_all_chip)

    # ------------------------------------------------------------------
    def _update_status(self) -> None:
        total = len(self._df_original)
        shown = self.model.rowCount()
        n_filters = sum(len(v) for v in self._filters.values())
        self.status_label.setText(
            f"Показано строк: {shown:,} из {total:,}  |  Активных условий фильтра: {n_filters}"
        )


# ======================================================================
# 5. Пример запуска: DataFrame на 50 000 строк
# ======================================================================
def _build_demo_dataframe(n_rows: int = 50_000) -> pd.DataFrame:
    """Сгенерировать демонстрационный DataFrame (id, name, price, created, category)."""
    rng = np.random.default_rng(42)
    categories = ["Electronics", "Books", "Toys", "Clothing", "Groceries", "Sports"]

    ids = np.arange(1, n_rows + 1)
    names = [f"Product-{i:06d}" for i in ids]
    prices = np.round(rng.uniform(1.0, 2500.0, size=n_rows), 2)
    start_date = pd.Timestamp("2020-01-01")
    offsets = rng.integers(0, 365 * 5, size=n_rows)
    created = start_date + pd.to_timedelta(offsets, unit="D")
    category = rng.choice(categories, size=n_rows)

    return pd.DataFrame(
        {
            "id": ids,
            "name": names,
            "price": prices,
            "created": created,
            "category": category,
        }
    )


class DemoMainWindow(QMainWindow):
    """Главное окно демонстрационного приложения."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("VirtualDataFrameTable - демо (50 000 строк)")
        self.resize(1200, 700)

        df = _build_demo_dataframe(50_000)
        self.table_widget = VirtualDataFrameTable(df, self)
        self.setCentralWidget(self.table_widget)


def main() -> None:
    app = QApplication(sys.argv)
    window = DemoMainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()