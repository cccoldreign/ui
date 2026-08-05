# -*- coding: utf-8 -*-
"""
dataframe_table_widget.py
==========================

Производительный виджет таблицы для PyQt5, построенный на архитектуре
Qt Model/View (QTableView + QAbstractTableModel) и pandas.DataFrame.

Ключевые идеи:
    * данные хранятся ТОЛЬКО в виде pandas.DataFrame (никаких списков
      Python-объектов, никаких QTableWidgetItem);
    * модель никогда не работает со всем DataFrame сразу — она держит
      в памяти только "окно" (VirtualViewport) из ~100-150 строк и
      обновляет его по мере прокрутки;
    * фильтрация и сортировка реализованы через pandas, без
      QSortFilterProxyModel;
    * исходный DataFrame никогда не мутируется — все операции
      (фильтрация/сортировка) строят новое представление (view).

Структура классов:
    FilterCondition   -- одно условие фильтра (dataclass)
    FilterEngine      -- хранение и применение набора условий фильтра
    VirtualViewport    -- расчёт "окна" видимых строк для виртуализации
    DataFrameModel     -- QAbstractTableModel поверх DataFrame + viewport
    DataFrameTableWidget -- публичный виджет, объединяющий всё вместе
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, QVariant
from PyQt5.QtWidgets import QAbstractItemView, QHeaderView, QTableView, QVBoxLayout, QWidget


# ---------------------------------------------------------------------------
# 1. Условие фильтра
# ---------------------------------------------------------------------------

# Разрешённые операторы (сгруппированы по типу данных, но физически
# это просто строки — конкретную реализацию выбирает FilterEngine).
NUMERIC_OPERATORS = (">", ">=", "<", "<=", "==", "!=", "between")
STRING_OPERATORS = ("contains", "startswith", "endswith", "equals", "not_equals", "regex")
DATETIME_OPERATORS = ("before", "after", "on", "between")


@dataclass(frozen=True)
class FilterCondition:
    """Одно условие фильтрации по одной колонке.

    Хранится как неизменяемый объект (frozen dataclass), что упрощает
    сравнение/удаление и исключает случайные мутации "на лету".
    """

    column: str
    operator: str
    value: Any
    value2: Optional[Any] = None  # используется для between/BETWEEN-подобных операторов
    case_sensitive: bool = True   # актуально только для строковых операторов


# ---------------------------------------------------------------------------
# 2. Движок фильтрации (чистый pandas, без Qt)
# ---------------------------------------------------------------------------

class FilterEngine:
    """Хранит список условий фильтрации и умеет строить булеву маску.

    Все условия объединяются оператором AND (логическое "И").
    Архитектура намеренно линейная (список условий + reduce по AND),
    чтобы в будущем было легко добавить группировку с OR: для этого
    достаточно заменить плоский список на дерево (AND/OR-узлы) и
    изменить только build_mask(), не трогая остальной код виджета.
    """

    def __init__(self) -> None:
        self._conditions: List[FilterCondition] = []

    # -- управление условиями -------------------------------------------------

    def add_filter(
        self,
        column: str,
        operator: str,
        value: Any,
        value2: Optional[Any] = None,
        case_sensitive: bool = True,
    ) -> None:
        """Добавить новое условие фильтрации."""
        condition = FilterCondition(
            column=column,
            operator=operator,
            value=value,
            value2=value2,
            case_sensitive=case_sensitive,
        )
        self._conditions.append(condition)

    def remove_filter(
        self,
        column: Optional[str] = None,
        operator: Optional[str] = None,
        index: Optional[int] = None,
    ) -> None:
        """Удалить условие(я) фильтрации.

        Поведение:
            * если задан index -- удаляется конкретное условие по позиции;
            * иначе удаляются все условия, подходящие под column/operator
              (любой из параметров можно опустить -- он не участвует в фильтре).
        """
        if index is not None:
            if 0 <= index < len(self._conditions):
                del self._conditions[index]
            return

        def _matches(cond: FilterCondition) -> bool:
            if column is not None and cond.column != column:
                return False
            if operator is not None and cond.operator != operator:
                return False
            return True

        self._conditions = [c for c in self._conditions if not _matches(c)]

    def clear_filters(self) -> None:
        """Удалить все условия фильтрации."""
        self._conditions.clear()

    @property
    def conditions(self) -> Tuple[FilterCondition, ...]:
        return tuple(self._conditions)

    def has_filters(self) -> bool:
        return len(self._conditions) > 0

    # -- построение маски -------------------------------------------------

    def build_mask(self, df: pd.DataFrame) -> pd.Series:
        """Построить булеву маску для df на основе всех условий (AND).

        Возвращает pd.Series[bool] той же длины, что и df.
        Не изменяет df.
        """
        if not self._conditions:
            # Быстрый путь: все строки проходят фильтр.
            return pd.Series(True, index=df.index)

        mask = pd.Series(True, index=df.index)
        for condition in self._conditions:
            mask &= self._evaluate_condition(df, condition)
        return mask

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """Вернуть НОВОЕ представление df с учётом фильтров (df.loc[mask]).

        df.loc[mask] создаёт view/копию только выбранных строк -- это
        ожидаемо и необходимо для отображения отфильтрованных данных,
        при этом исходный df не модифицируется.
        """
        mask = self.build_mask(df)
        return df.loc[mask]

    # -- реализация конкретных операторов -------------------------------------------------

    def _evaluate_condition(self, df: pd.DataFrame, condition: FilterCondition) -> pd.Series:
        series = df[condition.column]
        dtype = series.dtype

        if pd.api.types.is_datetime64_any_dtype(dtype):
            return self._evaluate_datetime(series, condition)
        if pd.api.types.is_numeric_dtype(dtype):
            return self._evaluate_numeric(series, condition)
        # По умолчанию считаем колонку строковой (object/string/category).
        return self._evaluate_string(series, condition)

    @staticmethod
    def _evaluate_numeric(series: pd.Series, condition: FilterCondition) -> pd.Series:
        op = condition.operator
        value = condition.value
        if op == ">":
            return series > value
        if op == ">=":
            return series >= value
        if op == "<":
            return series < value
        if op == "<=":
            return series <= value
        if op == "==":
            return series == value
        if op == "!=":
            return series != value
        if op == "between":
            lo, hi = value, condition.value2
            return series.between(lo, hi)
        raise ValueError(f"Неизвестный числовой оператор: {op!r}")

    @staticmethod
    def _evaluate_string(series: pd.Series, condition: FilterCondition) -> pd.Series:
        op = condition.operator
        value = condition.value
        case = condition.case_sensitive
        # na=False -- чтобы NaN не ломал маску и не считался совпадением.
        str_series = series.astype("string")

        if op == "contains":
            return str_series.str.contains(str(value), case=case, na=False, regex=False)
        if op == "startswith":
            s = str_series if case else str_series.str.lower()
            v = value if case else str(value).lower()
            return s.str.startswith(v).fillna(False)
        if op == "endswith":
            s = str_series if case else str_series.str.lower()
            v = value if case else str(value).lower()
            return s.str.endswith(v).fillna(False)
        if op == "equals":
            s = str_series if case else str_series.str.lower()
            v = value if case else str(value).lower()
            return s == v
        if op == "not_equals":
            s = str_series if case else str_series.str.lower()
            v = value if case else str(value).lower()
            return s != v
        if op == "regex":
            return str_series.str.contains(str(value), case=case, na=False, regex=True)
        raise ValueError(f"Неизвестный строковый оператор: {op!r}")

    @staticmethod
    def _evaluate_datetime(series: pd.Series, condition: FilterCondition) -> pd.Series:
        op = condition.operator
        value = pd.to_datetime(condition.value)

        if op == "before":
            return series < value
        if op == "after":
            return series > value
        if op == "on":
            # Совпадение по календарной дате (без учёта времени суток).
            return series.dt.date == value.date()
        if op == "between":
            value2 = pd.to_datetime(condition.value2)
            return series.between(value, value2)
        raise ValueError(f"Неизвестный оператор даты/времени: {op!r}")


# ---------------------------------------------------------------------------
# 3. Виртуальный вьюпорт: расчёт видимого окна строк
# ---------------------------------------------------------------------------

class VirtualViewport:
    """Отвечает только за арифметику виртуализации: какое окно строк
    должно быть закешировано в памяти модели в данный момент.

    Не хранит данные -- только числа (границы окна) и параметры.
    """

    def __init__(self, window_size: int = 150, prefetch_margin: int = 30) -> None:
        """
        window_size      -- сколько строк держим в кеше одновременно.
        prefetch_margin  -- насколько близко к краю окна должен
                             подойти запрошенный индекс, чтобы
                             инициировать пересчёт окна.
        """
        self.window_size = window_size
        self.prefetch_margin = prefetch_margin
        self.total_rows: int = 0
        self.start: int = 0
        self.end: int = 0  # исключительная граница, т.е. окно = [start, end)

    def reset(self, total_rows: int) -> None:
        """Сбросить вьюпорт под новый набор данных."""
        self.total_rows = max(total_rows, 0)
        self.start = 0
        self.end = min(self.window_size, self.total_rows)

    def needs_refresh(self, row: int) -> bool:
        """Нужно ли пересчитать окно, чтобы обслужить запрос строки row."""
        if self.total_rows == 0:
            return False
        if row < self.start or row >= self.end:
            return True
        # Приближаемся к верхней границе окна -- подгружаем следующую порцию.
        if row >= self.end - self.prefetch_margin and self.end < self.total_rows:
            return True
        # Приближаемся к нижней границе окна -- подгружаем предыдущую порцию.
        if row <= self.start + self.prefetch_margin and self.start > 0:
            return True
        return False

    def compute_window(self, row: int) -> Tuple[int, int]:
        """Посчитать новое окно [start, end) с центром вокруг row.

        Окно всегда клэмпится в границы [0, total_rows).
        """
        if self.total_rows == 0:
            return 0, 0

        half = self.window_size // 2
        start = max(0, row - half)
        end = min(self.total_rows, start + self.window_size)
        # Если уткнулись в правый край -- сдвигаем окно влево, чтобы
        # сохранить полный размер window_size (если данных достаточно).
        start = max(0, end - self.window_size)

        self.start, self.end = start, end
        return start, end


# ---------------------------------------------------------------------------
# 4. Модель данных (Qt Model/View)
# ---------------------------------------------------------------------------

class DataFrameModel(QAbstractTableModel):
    """QAbstractTableModel поверх pandas.DataFrame с виртуализацией строк.

    rowCount() всегда возвращает ПОЛНОЕ число строк отображаемого
    DataFrame -- это нужно, чтобы скроллбар QTableView вёл себя
    корректно (показывал реальный масштаб данных).

    Однако data() никогда не трогает весь DataFrame: она обращается
    только к закешированному окну (self._window_df), которое
    подгружается через .iloc по мере необходимости (см. VirtualViewport).
    """

    def __init__(self, viewport: Optional[VirtualViewport] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        # Пустой DataFrame по умолчанию -- у виджета нет данных, пока
        # не вызван set_dataset()/set_dataframe().
        self._df: pd.DataFrame = pd.DataFrame()
        self._viewport = viewport or VirtualViewport()

        # Кеш текущего окна строк -- ИМЕННО он лежит "в памяти модели".
        self._window_df: pd.DataFrame = pd.DataFrame()

    # -- работа с исходными данными -------------------------------------------------

    def set_dataframe(self, df: pd.DataFrame) -> None:
        """Заменить отображаемый DataFrame и полностью сбросить модель.

        df передаётся по ссылке (без копирования) -- вызывающий код
        (DataFrameTableWidget) отвечает за то, чтобы это было
        независимое представление (после фильтрации/сортировки).
        """
        self.beginResetModel()
        self._df = df
        self._viewport.reset(len(df))
        self._refresh_window(0, force=True)
        self.endResetModel()

    def dataframe(self) -> pd.DataFrame:
        """Текущий (отфильтрованный/отсортированный) DataFrame, только для чтения."""
        return self._df

    # -- обязательные методы QAbstractTableModel -------------------------------------------------

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802 (сигнатура Qt)
        if parent.isValid():
            return 0
        return len(self._df)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._df.columns)

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole
    ) -> Union[QVariant, str]:
        if role != Qt.DisplayRole:
            return QVariant()
        if orientation == Qt.Horizontal:
            if 0 <= section < len(self._df.columns):
                return str(self._df.columns[section])
            return QVariant()
        # Вертикальный заголовок -- номер строки (1-based, как в Excel).
        return str(section + 1)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Union[QVariant, str]:
        if not index.isValid():
            return QVariant()
        if role not in (Qt.DisplayRole, Qt.EditRole):
            return QVariant()

        row, col = index.row(), index.column()
        if row < 0 or row >= len(self._df) or col < 0 or col >= len(self._df.columns):
            return QVariant()

        # Ключевой момент виртуализации: если запрошенная строка
        # выходит за пределы (или близко к краю) закешированного окна,
        # пересчитываем окно и подгружаем новый срез через iloc.
        if self._viewport.needs_refresh(row):
            self._refresh_window(row)

        local_row = row - self._viewport.start
        # Защита от гонок при пересчёте окна (например, конкурентная
        # сортировка) -- если что-то не сошлось, просто выходим.
        if local_row < 0 or local_row >= len(self._window_df):
            return QVariant()

        value = self._window_df.iat[local_row, col]
        return self._format_value(value)

    # -- внутренняя механика окна -------------------------------------------------

    def _refresh_window(self, row: int, force: bool = False) -> None:
        """Пересчитать и закешировать окно строк вокруг row."""
        if len(self._df) == 0:
            self._window_df = self._df
            return
        start, end = self._viewport.compute_window(row)
        # .iloc[start:end] -- индексированный доступ без сканирования
        # всего DataFrame и без построения списков Python-объектов.
        self._window_df = self._df.iloc[start:end]

    @staticmethod
    def _format_value(value: Any) -> str:
        """Преобразовать значение ячейки DataFrame в строку для отображения."""
        if value is None:
            return ""
        # NaN/NaT из pandas/numpy отображаем пустой строкой.
        if isinstance(value, float) and np.isnan(value):
            return ""
        if pd.isna(value):
            return ""
        if isinstance(value, pd.Timestamp):
            return value.isoformat(sep=" ")
        return str(value)


# ---------------------------------------------------------------------------
# 5. Публичный виджет
# ---------------------------------------------------------------------------

class DataFrameTableWidget(QWidget):
    """Готовый к использованию виджет таблицы поверх pandas.DataFrame.

    Инкапсулирует:
        * QTableView + DataFrameModel (Qt Model/View, без QTableWidget);
        * FilterEngine (фильтрация средствами pandas);
        * сортировку по клику на заголовок (pandas.sort_values);
        * виртуализацию строк (через DataFrameModel/VirtualViewport).

    Внешний код работает только с публичным API этого класса и никогда
    не обращается к DataFrame/модели напрямую.
    """

    def __init__(
        self,
        window_size: int = 150,
        prefetch_margin: int = 30,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        # Исходные (немодифицированные) данные -- "источник истины".
        self._source_df: pd.DataFrame = pd.DataFrame()

        # Текущее отфильтрованное+отсортированное представление,
        # которое видит пользователь. Строится заново при каждом
        # apply_filters()/сортировке, исходный _source_df не трогается.
        self._view_df: pd.DataFrame = pd.DataFrame()

        self._filter_engine = FilterEngine()
        self._sort_column: Optional[str] = None
        self._sort_ascending: bool = True

        self._viewport = VirtualViewport(window_size=window_size, prefetch_margin=prefetch_margin)
        self._model = DataFrameModel(viewport=self._viewport, parent=self)

        self._view = QTableView(self)
        self._view.setModel(self._model)
        self._view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._view.setSortingEnabled(False)  # сортировку делаем сами через pandas
        self._view.setAlternatingRowColors(True)
        self._view.verticalHeader().setDefaultSectionSize(24)
        self._view.horizontalHeader().setSectionsClickable(True)
        self._view.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self._view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)
        self.setLayout(layout)

    # -- доступ к внутреннему QTableView (для тонкой настройки извне) -------------------------------------------------

    @property
    def view(self) -> QTableView:
        return self._view

    # -- загрузка данных -------------------------------------------------

    def set_dataset(self, data: Sequence[Tuple[Any, ...]], columns: Optional[Sequence[str]] = None) -> None:
        """Загрузить новый набор данных.

        data -- список (или иная последовательность) кортежей-строк.
        columns -- имена колонок; если не заданы, pandas сгенерирует
                   их автоматически (0, 1, 2, ...).

        Данные один раз преобразуются в DataFrame, дальше вся работа
        идёт только через него.
        """
        self._source_df = pd.DataFrame(data, columns=columns)
        self._filter_engine.clear_filters()
        self._sort_column = None
        self._rebuild_view()

    def replace_dataset(self, data: Sequence[Tuple[Any, ...]], columns: Optional[Sequence[str]] = None) -> None:
        """Полностью заменить набор данных (алиас над set_dataset)."""
        self.set_dataset(data, columns)

    def append_rows(self, data: Sequence[Tuple[Any, ...]]) -> None:
        """Добавить строки к уже загруженному набору данных.

        Новые строки должны соответствовать текущим колонкам по составу
        и порядку значений в кортежах.
        """
        if self._source_df.empty:
            self.set_dataset(data)
            return

        new_rows = pd.DataFrame(data, columns=self._source_df.columns)
        # pd.concat с ignore_index -- избегаем ручных Python-циклов,
        # индекс пересобирается один раз, без копирования построчно.
        self._source_df = pd.concat([self._source_df, new_rows], ignore_index=True)
        self._rebuild_view()

    def clear(self) -> None:
        """Полностью очистить виджет (данные, фильтры, сортировку)."""
        self._source_df = pd.DataFrame()
        self._view_df = pd.DataFrame()
        self._filter_engine.clear_filters()
        self._sort_column = None
        self._model.set_dataframe(self._view_df)

    # -- фильтрация -------------------------------------------------

    def add_filter(
        self,
        column: str,
        operator: str,
        value: Any,
        value2: Optional[Any] = None,
        case_sensitive: bool = True,
    ) -> None:
        """Добавить условие фильтра. Не применяется автоматически --
        вызовите apply_filters() (либо используйте add_filter(...) +
        apply_filters() пачкой, чтобы не пересчитывать view на каждый
        add_filter при массовом добавлении условий)."""
        self._filter_engine.add_filter(column, operator, value, value2, case_sensitive)

    def remove_filter(
        self,
        column: Optional[str] = None,
        operator: Optional[str] = None,
        index: Optional[int] = None,
    ) -> None:
        """Удалить условие(я) фильтра. Требует apply_filters() для применения."""
        self._filter_engine.remove_filter(column, operator, index)

    def clear_filters(self) -> None:
        """Удалить все условия фильтра. Требует apply_filters() для применения."""
        self._filter_engine.clear_filters()

    def apply_filters(self) -> None:
        """Пересчитать отображаемое представление с учётом всех фильтров
        (и текущей сортировки, если она задана)."""
        self._rebuild_view()

    # -- сортировка -------------------------------------------------

    def sort_by(self, column: str, ascending: bool = True) -> None:
        """Отсортировать таблицу по колонке программно."""
        self._sort_column = column
        self._sort_ascending = ascending
        self._rebuild_view()

    def _on_header_clicked(self, section: int) -> None:
        """Обработчик клика по заголовку -- переключает сортировку
        по колонке (по возрастанию / по убыванию)."""
        if section < 0 or section >= len(self._view_df.columns):
            return
        column = str(self._view_df.columns[section])

        if self._sort_column == column:
            self._sort_ascending = not self._sort_ascending
        else:
            self._sort_column = column
            self._sort_ascending = True

        self._rebuild_view()

    # -- внутренняя пересборка представления -------------------------------------------------

    def _rebuild_view(self) -> None:
        """Построить self._view_df заново: фильтрация -> сортировка,
        затем передать результат в модель.

        Исходный self._source_df никогда не изменяется. filter_engine.apply()
        и sort_values() сами по себе создают новое представление
        (обычно view, а не полную глубокую копию, пока не потребуется
        запись), поэтому лишних дублирований больших данных не происходит.
        """
        if self._source_df.empty:
            self._view_df = self._source_df
        else:
            filtered = self._filter_engine.apply(self._source_df)
            if self._sort_column is not None and self._sort_column in filtered.columns:
                filtered = filtered.sort_values(
                    by=self._sort_column,
                    ascending=self._sort_ascending,
                    kind="mergesort",  # стабильная сортировка
                )
            self._view_df = filtered

        self._model.set_dataframe(self._view_df)

    # -- вспомогательные геттеры -------------------------------------------------

    def row_count(self) -> int:
        """Количество строк в текущем (отфильтрованном) представлении."""
        return len(self._view_df)

    def source_row_count(self) -> int:
        """Количество строк в исходном (неотфильтрованном) наборе данных."""
        return len(self._source_df)

    def columns(self) -> List[str]:
        return list(self._view_df.columns) if not self._view_df.empty else list(self._source_df.columns)