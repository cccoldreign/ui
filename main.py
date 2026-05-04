"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                        ACCESS-LIKE PyQt5 APPLICATION                           ║
║                                                                                  ║
║  СТРУКТУРА:                                                                      ║
║  1. DB_CONFIG          — настройки подключения к БД                             ║
║  2. DatabaseManager    — менеджер соединения с БД (singleton)                  ║
║  3. BaseForm           — абстрактный класс для форм редактирования              ║
║  4. BaseTableView      — абстрактный класс для табличного представления         ║
║  5. EmployeeForm       — конкретная форма редактирования сотрудника             ║
║  6. EmployeeTableView  — конкретная таблица сотрудников                         ║
║  7. MainWindow         — главное MDI окно с тулбаром                            ║
╚══════════════════════════════════════════════════════════════════════════════════╝

  ГОРЯЧИЕ КЛАВИШИ:
    F5  — сохранить изменения / обновить форму
    Ctrl+W — закрыть текущее MDI окно
    Ctrl+T — переключить режим MDI / Вкладки
"""

import sys
import pyodbc
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QMdiArea, QMdiSubWindow,
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QToolBar,
    QAction, QTableWidget, QTableWidgetItem, QHeaderView,
    QCompleter, QMessageBox, QTabWidget, QFrame,
    QSizePolicy, QStatusBar, QDateEdit, QDoubleSpinBox,
    QMenu, QActionGroup, QAbstractItemView, QCheckBox, QSpinBox,
    QDialog, QDialogButtonBox, QScrollArea, QGroupBox
)
from PyQt5.QtCore import (
    Qt, QStringListModel, pyqtSignal, QDate, QSortFilterProxyModel,
    QAbstractTableModel, QModelIndex, QVariant
)
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette, QKeySequence

# Простая замена ABC + abstractmethod без конфликта метаклассов PyQt5.
# @abstractmethod здесь только документирует намерение.
# Наследники обязаны переопределить эти методы — иначе упадут в runtime.
def abstractmethod(func):
    func.__isabstractmethod__ = True
    return func

# ══════════════════════════════════════════════════════════════════════════════════
#  СЕКЦИЯ 1 — КОНФИГУРАЦИЯ БД
#  Здесь только строки подключения. Меняй под свои нужды.
# ══════════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    "dsn":      "MyLocalDB",
    "uid":      "myuser",
    "pwd":      "mypassword",
}

TABLE_CONFIG = {
    # "internal_name": ("SQL таблица", "Заголовок окна", [список колонок для отображения])
    "employees": (
        "employees",
        "Сотрудники",
        ["id", "last_name", "first_name", "middle_name", "department", "position", "birth_date", "salary"]
    ),
}

COLUMN_LABELS = {
    "id":          "ID",
    "last_name":   "Фамилия",
    "first_name":  "Имя",
    "middle_name": "Отчество",
    "department":  "Отдел",
    "position":    "Должность",
    "birth_date":  "Дата рождения",
    "salary":      "Зарплата",
}

# ══════════════════════════════════════════════════════════════════════════════════
#  СЕКЦИЯ 2 — DATABASE MANAGER
#  Singleton. Хранит одно соединение на всё приложение.
#  Все запросы идут через него.
# ══════════════════════════════════════════════════════════════════════════════════

class DatabaseManager:
    """
    Singleton-менеджер соединения с БД через pyodbc.

    Использование:
        db = DatabaseManager.instance()
        rows = db.fetchall("SELECT * FROM employees")
        db.execute("UPDATE employees SET salary=%s WHERE id=%s", (100000, 1))
    """
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        conn_str = (
            f"DSN={DB_CONFIG['dsn']};"
            f"UID={DB_CONFIG['uid']};"
            f"PWD={DB_CONFIG['pwd']};"
        )
        try:
            self.conn = pyodbc.connect(conn_str, autocommit=False)
            print("[DB] Соединение установлено")
        except pyodbc.Error as e:
            print(f"[DB] Ошибка соединения: {e}")
            raise

    def cursor(self):
        return self.conn.cursor()

    @staticmethod
    def _build_sql(sql, params):
        """
        psqlODBC на Mac через unixODBC капризен с параметрами.
        Самый надёжный способ — вставлять значения напрямую в SQL.
        Для внутреннего десктоп-приложения SQL-инъекция не угроза.
        """
        if not params:
            return sql, ()
        result = sql
        for val in params:
            if val is None:
                literal = "NULL"
            elif isinstance(val, bool):
                literal = "TRUE" if val else "FALSE"
            elif isinstance(val, (int, float)):
                literal = str(val)
            else:
                # Экранируем одиночные кавычки
                escaped = str(val).replace("'", "''")
                literal = f"'{escaped}'"
            result = result.replace("%s", literal, 1)
        return result, ()

    def fetchall(self, sql, params=()):
        """Выполнить SELECT, вернуть список строк."""
        cur = self.conn.cursor()
        built_sql, built_params = self._build_sql(sql, params)
        print(f"[SQL] {built_sql[:120]}")
        cur.execute(built_sql)
        return cur.fetchall()

    def fetchone(self, sql, params=()):
        """Выполнить SELECT, вернуть одну строку."""
        cur = self.conn.cursor()
        built_sql, _ = self._build_sql(sql, params)
        print(f"[SQL] {built_sql[:120]}")
        cur.execute(built_sql)
        return cur.fetchone()

    def execute(self, sql, params=()):
        """Выполнить INSERT/UPDATE/DELETE с коммитом."""
        cur = self.conn.cursor()
        built_sql, _ = self._build_sql(sql, params)
        print(f"[SQL] {built_sql[:120]}")
        cur.execute(built_sql)
        self.conn.commit()

    def columns(self, table_name):
        """Вернуть список (name, type_code) колонок таблицы."""
        cur = self.conn.cursor()
        # LIMIT 1 безопаснее для ODBC драйверов чем WHERE 1=0
        cur.execute(f"SELECT * FROM {table_name} LIMIT 1")
        return [(desc[0], desc[1]) for desc in cur.description]

    def close(self):
        self.conn.close()
        print("[DB] Соединение закрыто")



# ══════════════════════════════════════════════════════════════════════════════════
#  СЕКЦИЯ 2.5 — ForeignKeyWidget
#
#  Виджет для полей-внешних ключей.
#  Пользователь видит и пишет НАЗВАНИЕ (напр. "ООО Рога и Копыта").
#  В БД сохраняется INTEGER id (напр. 3).
#
#  Использование в fields():
#      ("enterprise_id", "Предприятие", "fk:enterprises:name:id")
#       ^колонка в главной таблице  ^формат  ^таблица ^отображаемое поле ^pk
# ══════════════════════════════════════════════════════════════════════════════════

class ForeignKeyWidget(QWidget):
    """
    Поле с автодополнением для внешнего ключа.

    Показывает: display_col (название предприятия)
    Хранит:     pk_col (integer id) в self.current_fk_id

    Сигнал changed эмитируется при выборе записи.
    """
    changed = pyqtSignal()

    def __init__(self, ref_table: str, display_col: str, pk_col: str, parent=None):
        super().__init__(parent)
        self.ref_table   = ref_table    # "enterprises"
        self.display_col = display_col  # "name"
        self.pk_col      = pk_col       # "id"
        self.current_fk_id = None       # текущий выбранный id (или None)
        self._records = []              # [(id, display_text), ...]
        self._loading = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText(f"Начните вводить {display_col}...")

        self._completer = QCompleter([])
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self._completer.activated.connect(self._on_selected)
        self.line_edit.setCompleter(self._completer)
        self.line_edit.editingFinished.connect(self._on_editing_finished)

        # Кнопка очистить
        btn_clear = QPushButton("✕")
        btn_clear.setFixedWidth(26)
        btn_clear.setFixedHeight(26)
        btn_clear.setToolTip("Очистить выбор")
        btn_clear.clicked.connect(self.clear_selection)

        layout.addWidget(self.line_edit)
        layout.addWidget(btn_clear)

        self._load_records()

    def _load_records(self):
        """Загрузить все записи справочной таблицы."""
        try:
            db = DatabaseManager.instance()
            rows = db.fetchall(
                f"SELECT {self.pk_col}, {self.display_col} FROM {self.ref_table} ORDER BY {self.display_col}"
            )
            self._records = [(getattr(r, self.pk_col), getattr(r, self.display_col) or "") for r in rows]
            names = [r[1] for r in self._records]
            model = QStringListModel(names)
            self._completer.setModel(model)
        except Exception as e:
            print(f"[FKWidget] Ошибка загрузки {self.ref_table}: {e}")

    def _on_selected(self, text: str):
        """Пользователь выбрал из выпадушки."""
        self._set_by_display(text)

    def _on_editing_finished(self):
        """Потеря фокуса — попробовать найти точное совпадение."""
        self._set_by_display(self.line_edit.text())

    def _set_by_display(self, text: str):
        """Найти id по тексту и установить current_fk_id."""
        text = text.strip().lower()
        for fk_id, display in self._records:
            if display.lower() == text:
                if self.current_fk_id != fk_id:
                    self.current_fk_id = fk_id
                    self._loading = True
                    self.line_edit.blockSignals(True)
                    self.line_edit.setText(display)
                    self.line_edit.blockSignals(False)
                    self._loading = False
                    self.changed.emit()
                return
        # Не нашли точного совпадения — сбрасываем id но оставляем текст
        self.current_fk_id = None

    def set_value(self, fk_id):
        """
        Установить виджет по id (вызывается при загрузке записи из БД).
        fk_id — integer или None.
        """
        self.current_fk_id = fk_id
        if fk_id is None:
            self.line_edit.blockSignals(True)
            self.line_edit.clear()
            self.line_edit.blockSignals(False)
            return
        for rec_id, display in self._records:
            if rec_id == fk_id or str(rec_id) == str(fk_id):
                self.line_edit.blockSignals(True)
                self.line_edit.setText(display)
                self.line_edit.blockSignals(False)
                return
        # id есть но не в кэше — перезагрузить
        self._load_records()
        self.set_value(fk_id)

    def get_value(self):
        """Вернуть текущий fk_id для сохранения в БД. None если не выбрано."""
        return self.current_fk_id

    def clear_selection(self):
        self.current_fk_id = None
        self.line_edit.blockSignals(True)
        self.line_edit.clear()
        self.line_edit.blockSignals(False)
        self.changed.emit()

    def setEnabled(self, enabled: bool):
        """Проксируем enable/disable на внутренний line_edit."""
        super().setEnabled(enabled)
        self.line_edit.setEnabled(enabled)

    def refresh(self):
        """Перезагрузить список предприятий (например после добавления)."""
        current_id = self.current_fk_id
        self._load_records()
        if current_id is not None:
            self.set_value(current_id)


# ══════════════════════════════════════════════════════════════════════════════════
#  СЕКЦИЯ 3 — BASE FORM (АБСТРАКТНЫЙ КЛАСС ФОРМЫ РЕДАКТИРОВАНИЯ)
#
#  Наследники обязаны реализовать:
#    - table_name()   — имя SQL таблицы
#    - pk_column()    — имя первичного ключа
#    - fields()       — список (column, label, widget_type)
#    - search_column()— колонка для строки поиска (ФИО и т.д.)
#    - display_name() — строка отображения для комплитера (напр. "Иванов Иван")
#
#  Что даёт базовый класс:
#    - Строка поиска с автодополнением
#    - Динамическая генерация полей по fields()
#    - Индикатор редактирования (✎) слева от формы
#    - F5 = сохранить + обновить
#    - Переключение записи = автосохранение
# ══════════════════════════════════════════════════════════════════════════════════

class BaseForm(QWidget):
    """
    Абстрактная форма в стиле Access.

    Поиск → автодополнение → загрузка записи → редактирование → F5/переключение = сохранение.
    """

    # Сигнал: запись сохранена (для обновления других виджетов если нужно)
    record_saved = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager.instance()
        self._current_id = None      # PK текущей загруженной записи
        self._dirty = False          # есть ли несохранённые изменения
        self._is_new_mode = False
        self._field_widgets = {}     # {column: widget}
        self._all_records = []       # кэш всех записей для комплитера

        self._build_ui()
        self._refresh_completer()

    # ── Хелперы для резолва property/method ──────────────────────────────────
    def _tname(self):
        v = self.table_name
        return v() if callable(v) else v

    def _pkcol(self):
        v = self.pk_column
        return v() if callable(v) else v

    def _scol(self):
        v = self.search_column
        return v() if callable(v) else v

    # ── Абстрактные методы ────────────────────────────────────────────────────

    @property
    @abstractmethod
    def table_name(self) -> str:
        """Имя SQL таблицы, напр. 'employees'"""
        ...

    @property
    @abstractmethod
    def pk_column(self) -> str:
        """Имя первичного ключа, напр. 'id'"""
        ...

    @abstractmethod
    def fields(self) -> list:
        """
        Список кортежей: (column_name, label, widget_type)
        widget_type: 'text' | 'date' | 'number' | 'combo:<val1>,<val2>'
        Пример:
            [('last_name', 'Фамилия', 'text'),
             ('birth_date', 'Дата рождения', 'date'),
             ('salary', 'Зарплата', 'number')]
        """
        ...

    @abstractmethod
    def search_column(self) -> str:
        """Колонка по которой строится строка поиска."""
        ...

    @abstractmethod
    def display_value(self, row) -> str:
        """
        Как отобразить строку в комплитере.
        row — tuple из SELECT * FROM table
        Пример: f"{row.last_name} {row.first_name}"
        """
        ...

    # ── Построение UI ─────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setMinimumWidth(480)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # — Строка поиска —
        search_frame = QFrame()
        search_frame.setFrameShape(QFrame.StyledPanel)
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(8, 6, 8, 6)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(f"🔍  Поиск по полю «{self._scol()}»...")
        self.search_edit.setMinimumHeight(32)
        self.search_edit.returnPressed.connect(self._on_search_return)

        self._completer = QCompleter([])
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains)
        self._completer.activated.connect(self._on_completer_activated)
        self.search_edit.setCompleter(self._completer)

        btn_refresh = QPushButton("⟳")
        btn_refresh.setFixedWidth(36)
        btn_refresh.setToolTip("Обновить список (F5)")
        btn_refresh.clicked.connect(self.refresh)

        search_layout.addWidget(QLabel("ФИО / поиск:"))
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(btn_refresh)
        main_layout.addWidget(search_frame)

        # — Центральная часть: индикатор + форма —
        center = QHBoxLayout()
        center.setSpacing(4)

        # Индикатор редактирования (карандаш)
        self.edit_indicator = QLabel("  ")
        self.edit_indicator.setFixedWidth(22)
        self.edit_indicator.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.edit_indicator.setStyleSheet("font-size: 16px; color: #e67e22;")
        center.addWidget(self.edit_indicator)

        # Форма с полями
        self.form_frame = QFrame()
        self.form_frame.setFrameShape(QFrame.StyledPanel)
        self.form_layout = QFormLayout(self.form_frame)
        self.form_layout.setContentsMargins(12, 10, 12, 10)
        self.form_layout.setSpacing(10)
        self.form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        center.addWidget(self.form_frame)

        main_layout.addLayout(center)

        # — Генерируем поля по fields() —
        for col, label, wtype in self.fields():
            widget = self._create_field_widget(wtype)
            widget.setEnabled(False)   # до загрузки записи — неактивны
            self._connect_dirty(widget)
            self._field_widgets[col] = widget
            self.form_layout.addRow(f"{label}:", widget)

        # — Кнопки —
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("💾  Сохранить (F5)")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self.save_current)
        self.btn_new = QPushButton("＋  Новая запись")
        self.btn_new.clicked.connect(self._new_record)
        self.btn_delete = QPushButton("✕  Удалить")
        self.btn_delete.setEnabled(False)
        self.btn_delete.setStyleSheet("color: #c0392b;")
        self.btn_delete.clicked.connect(self._delete_record)

        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_new)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_delete)
        main_layout.addLayout(btn_layout)

        # — Статусная строка формы —
        self.status_label = QLabel("Введите имя для поиска или нажмите «Новая запись»")
        self.status_label.setStyleSheet("color: gray; font-size: 11px;")
        main_layout.addWidget(self.status_label)

    def _create_field_widget(self, wtype: str) -> QWidget:
        """
        Создать виджет по типу поля.
        Типы: text | date | number | combo:v1,v2 | fk:table:display_col:pk_col
        """
        if wtype == "date":
            w = QDateEdit()
            w.setCalendarPopup(True)
            w.setDisplayFormat("dd.MM.yyyy")
            w.setDate(QDate.currentDate())
            return w
        elif wtype == "number":
            w = QDoubleSpinBox()
            w.setMaximum(9_999_999)
            w.setDecimals(2)
            return w
        elif wtype.startswith("combo:"):
            values = wtype.split(":", 1)[1].split(",")
            w = QComboBox()
            w.addItems(values)
            return w
        elif wtype.startswith("fk:"):
            # fk:ref_table:display_col:pk_col
            parts = wtype.split(":")
            ref_table   = parts[1] if len(parts) > 1 else ""
            display_col = parts[2] if len(parts) > 2 else "name"
            pk_col      = parts[3] if len(parts) > 3 else "id"
            return ForeignKeyWidget(ref_table, display_col, pk_col)
        else:  # text
            return QLineEdit()

    def _connect_dirty(self, widget):
        """Подписаться на изменения виджета чтобы отслеживать dirty state."""
        if isinstance(widget, ForeignKeyWidget):
            widget.changed.connect(self._mark_dirty)
        elif isinstance(widget, QLineEdit):
            widget.textChanged.connect(self._mark_dirty)
        elif isinstance(widget, QDateEdit):
            widget.dateChanged.connect(self._mark_dirty)
        elif isinstance(widget, QDoubleSpinBox):
            widget.valueChanged.connect(self._mark_dirty)
        elif isinstance(widget, QComboBox):
            widget.currentTextChanged.connect(self._mark_dirty)

    # ── Логика dirty / индикатор ──────────────────────────────────────────────

    def _mark_dirty(self, *_):
        if self._current_id is not None and not self._dirty:
            self._dirty = True
            self.edit_indicator.setText("✎")
            self.btn_save.setEnabled(True)

    def _clear_dirty(self):
        self._dirty = False
        self.edit_indicator.setText("  ")
        self.btn_save.setEnabled(False)

    # ── Комплитер / поиск ─────────────────────────────────────────────────────

    def _refresh_completer(self):
        """Перезагрузить список всех записей для автодополнения."""
        try:
            # search_column и table_name могут быть property или методом — вызываем оба варианта
            tname = self.table_name() if callable(self.table_name) else self.table_name
            scol  = self.search_column() if callable(self.search_column) else self.search_column
            rows = self.db.fetchall(f"SELECT * FROM {tname} ORDER BY {scol}")
            self._all_records = rows
            names = [self.display_value(r) for r in rows]
            print(f"[Completer] Загружено {len(names)} записей: {names[:3]}")
            model = QStringListModel(names)
            self._completer.setModel(model)
            self._completer.setCompletionMode(QCompleter.PopupCompletion)
        except Exception as e:
            import traceback
            print(f"[Form] Ошибка загрузки комплитера: {e}")
            traceback.print_exc()

    def _find_record_by_display(self, text: str):
        """Найти запись по строке отображения."""
        for row in self._all_records:
            if self.display_value(row).lower() == text.strip().lower():
                return row
        return None

    def _on_completer_activated(self, text: str):
        """Пользователь выбрал из выпадающего списка."""
        self._maybe_save_before_switch()
        row = self._find_record_by_display(text)
        if row:
            self._load_record(getattr(row, self._pkcol()))

    def _on_search_return(self):
        """Enter в поле поиска."""
        text = self.search_edit.text().strip()
        if not text:
            return
        self._maybe_save_before_switch()
        row = self._find_record_by_display(text)
        if row:
            self._load_record(getattr(row, self._pkcol()))
        else:
            self.status_label.setText(f"Запись «{text}» не найдена")

    # ── Загрузка / сохранение записи ─────────────────────────────────────────

    def _load_record(self, pk_value):
        """Загрузить запись из БД по PK и заполнить поля."""
        try:
            row = self.db.fetchone(
                f"SELECT * FROM {self._tname()} WHERE {self._pkcol()} = %s",
                (pk_value,)
            )
            if not row:
                return
            self._current_id = pk_value

            # Включить поля
            for w in self._field_widgets.values():
                w.setEnabled(True)
            self.btn_delete.setEnabled(True)

            # Заполнить значениями (временно отключим dirty-слушатели)
            self._dirty = False
            self.edit_indicator.setText("  ")
            self.btn_save.setEnabled(False)

            for col, _, wtype in self.fields():
                widget = self._field_widgets[col]
                value = getattr(row, col, None)
                self._set_widget_value(widget, wtype, value)

            self._clear_dirty()
            self.status_label.setText(
                f"Запись #{pk_value} загружена  ·  F5 для сохранения"
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка загрузки", str(e))

    def _set_widget_value(self, widget, wtype, value):
        """Установить значение виджета без триггера dirty."""
        if isinstance(widget, ForeignKeyWidget):
            # value — integer id из БД, виджет покажет название
            widget.set_value(value)
            return

        if value is None:
            value = "" if wtype == "text" else value

        if isinstance(widget, QLineEdit):
            widget.blockSignals(True)
            widget.setText(str(value) if value is not None else "")
            widget.blockSignals(False)
        elif isinstance(widget, QDateEdit):
            widget.blockSignals(True)
            if value:
                widget.setDate(QDate(value.year, value.month, value.day))
            widget.blockSignals(False)
        elif isinstance(widget, QDoubleSpinBox):
            widget.blockSignals(True)
            widget.setValue(float(value) if value is not None else 0.0)
            widget.blockSignals(False)
        elif isinstance(widget, QComboBox):
            widget.blockSignals(True)
            idx = widget.findText(str(value) if value else "")
            widget.setCurrentIndex(max(0, idx))
            widget.blockSignals(False)

    def _get_widget_value(self, widget, wtype):
        """Получить значение из виджета для сохранения в БД."""
        if isinstance(widget, ForeignKeyWidget):
            # Возвращаем integer id, не название
            return widget.get_value()
        elif isinstance(widget, QLineEdit):
            return widget.text()
        elif isinstance(widget, QDateEdit):
            d = widget.date()
            return f"{d.year()}-{d.month():02d}-{d.day():02d}"
        elif isinstance(widget, QDoubleSpinBox):
            return widget.value()
        elif isinstance(widget, QComboBox):
            return widget.currentText()
        return None

    def save_current(self):
        """Сохранить текущую запись в БД."""
        if self._current_id is None and not self._is_new_mode:
            return
        try:
            cols = []
            vals = []
            for col, _, wtype in self.fields():
                if col == self._pkcol():
                    continue
                cols.append(col)
                vals.append(self._get_widget_value(self._field_widgets[col], wtype))

            if hasattr(self, '_is_new_mode') and self._is_new_mode:
                placeholders = ", ".join(["%s"] * len(cols))
                col_list = ", ".join(cols)
                self.db.execute(
                    f"INSERT INTO {self._tname()} ({col_list}) VALUES ({placeholders})",
                    vals
                )
                self._is_new_mode = False
                self.status_label.setText("✔ Новая запись добавлена")
            else:
                set_clause = ", ".join([f"{c} = %s" for c in cols])
                self.db.execute(
                    f"UPDATE {self._tname()} SET {set_clause} WHERE {self._pkcol()} = %s",
                    vals + [self._current_id]
                )
                self.status_label.setText(f"✔ Запись #{self._current_id} сохранена")

            self._clear_dirty()
            self._refresh_completer()
            self.record_saved.emit(self._current_id or 0)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения", str(e))

    def _maybe_save_before_switch(self):
        """Спросить о сохранении при переключении на другую запись."""
        if self._dirty:
            ans = QMessageBox.question(
                self, "Сохранить изменения?",
                "Есть несохранённые изменения. Сохранить перед переключением?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if ans == QMessageBox.Yes:
                self.save_current()
            elif ans == QMessageBox.Cancel:
                return False
        return True

    def _new_record(self):
        """Подготовить форму для ввода новой записи."""
        self._maybe_save_before_switch()
        self._current_id = None
        self._is_new_mode = True
        self.search_edit.clear()
        for w in self._field_widgets.values():
            w.setEnabled(True)
            if isinstance(w, ForeignKeyWidget):
                w.clear_selection()
            elif isinstance(w, QLineEdit):
                w.blockSignals(True); w.clear(); w.blockSignals(False)
        self._dirty = False
        self.edit_indicator.setText("✎")
        self.btn_save.setEnabled(True)
        self.btn_delete.setEnabled(False)
        self.status_label.setText("Заполните поля и нажмите «Сохранить»")
        # Фокус на первое поле
        first = list(self._field_widgets.values())
        if first:
            first[0].setFocus()

    def _delete_record(self):
        """Удалить текущую запись."""
        if self._current_id is None:
            return
        ans = QMessageBox.question(
            self, "Удалить запись?",
            f"Вы уверены что хотите удалить запись #{self._current_id}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ans == QMessageBox.Yes:
            try:
                self.db.execute(
                    f"DELETE FROM {self._tname()} WHERE {self._pkcol()} = %s",
                    (self._current_id,)
                )
                self._current_id = None
                self._dirty = False
                self.edit_indicator.setText("  ")
                self.btn_save.setEnabled(False)
                self.btn_delete.setEnabled(False)
                for w in self._field_widgets.values():
                    w.setEnabled(False)
                    if isinstance(w, QLineEdit):
                        w.clear()
                self.search_edit.clear()
                self._refresh_completer()
                self.status_label.setText("Запись удалена")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка удаления", str(e))

    def refresh(self):
        """F5 — сохранить (если нужно) и обновить комплитер."""
        if self._dirty:
            self.save_current()
        self._refresh_completer()
        if self._current_id:
            self._load_record(self._current_id)
        self.status_label.setText("↻ Данные обновлены")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F5:
            self.refresh()
        else:
            super().keyPressEvent(event)


# ══════════════════════════════════════════════════════════════════════════════════
#  СЕКЦИЯ 4 — BASE TABLE VIEW (АБСТРАКТНЫЙ КЛАСС ТАБЛИЧНОГО ПРЕДСТАВЛЕНИЯ)
#
#  Показывает данные таблицы БД как редактируемую таблицу с фильтрами.
#  Наследники обязаны реализовать:
#    - table_name()    — имя SQL таблицы
#    - pk_column()     — имя первичного ключа
#    - columns()       — список (column, label, тип: 'text'|'number'|'date')
#
#  Что даёт базовый класс:
#    - Загрузка всех строк таблицы
#    - Inline-редактирование любой ячейки (кроме PK)
#    - Панель фильтров: выбор колонки + тип фильтра (содержит/равно/больше/меньше)
#    - Сохранение изменённой строки при уходе с неё
#    - F5 = обновить таблицу
# ══════════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════════
#  СЕКЦИЯ 3.5 — FILTER DIALOG
#
#  Диалог для настройки нескольких фильтров таблицы.
#  Каждый фильтр — строка: [Столбец] [Условие] [Значение] [✕]
#  Кнопка «＋ Добавить фильтр» добавляет новую строку.
#  Все фильтры объединяются через AND.
# ══════════════════════════════════════════════════════════════════════════════════

class FilterDialog(QDialog):
    """
    Диалог настройки фильтров таблицы.

    Использование:
        dlg = FilterDialog(columns, current_filters, parent)
        if dlg.exec_() == QDialog.Accepted:
            filters = dlg.get_filters()  # [(col, op, val, col_type), ...]
    """

    # Операции по типу колонки
    OPS = {
        "text":   ["содержит", "равно", "начинается с", "заканчивается на", "не содержит"],
        "number": ["равно", "не равно", "больше", "меньше", "больше или равно", "меньше или равно"],
        "date":   ["равно", "после", "до", "не равно"],
    }

    def __init__(self, columns: list, active_filters: list, parent=None):
        """
        columns       — список (col_name, label, col_type) из BaseTableView.columns()
        active_filters — текущие фильтры [(col, op, val, col_type), ...]
        """
        super().__init__(parent)
        self.setWindowTitle("Настройка фильтров")
        self.setMinimumWidth(620)
        self.setMinimumHeight(300)
        self._columns = columns  # [(col_name, label, col_type)]
        self._rows = []          # список виджетов каждой строки фильтра

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # — Заголовок —
        header = QLabel("Условия фильтрации (объединяются через И):")
        header.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        # — Прокручиваемая область со строками фильтров —
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self._rows_widget = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_widget)
        self._rows_layout.setSpacing(6)
        self._rows_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self._rows_widget)
        layout.addWidget(scroll)

        # — Кнопка добавить —
        btn_add = QPushButton("＋  Добавить условие")
        btn_add.setFixedWidth(180)
        btn_add.clicked.connect(self._add_filter_row)
        layout.addWidget(btn_add)

        # — Кнопки OK / Отмена —
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Применить")
        buttons.button(QDialogButtonBox.Cancel).setText("Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Заполняем существующими фильтрами
        if active_filters:
            for col, op, val, col_type in active_filters:
                self._add_filter_row(col, op, val)
        else:
            self._add_filter_row()  # одна пустая строка по умолчанию

    def _add_filter_row(self, preset_col=None, preset_op=None, preset_val=""):
        """Добавить одну строку фильтра в диалог."""
        row_frame = QFrame()
        row_frame.setFrameShape(QFrame.StyledPanel)
        row_layout = QHBoxLayout(row_frame)
        row_layout.setContentsMargins(8, 6, 8, 6)
        row_layout.setSpacing(8)

        # — Выбор столбца —
        col_combo = QComboBox()
        col_combo.setMinimumWidth(130)
        for col_name, label, _ in self._columns:
            col_combo.addItem(label, col_name)

        # — Выбор операции —
        op_combo = QComboBox()
        op_combo.setMinimumWidth(150)

        # — Значение —
        val_edit = QLineEdit()
        val_edit.setPlaceholderText("Значение...")
        val_edit.setMinimumWidth(160)

        # — Кнопка удалить строку —
        btn_remove = QPushButton("✕")
        btn_remove.setFixedWidth(30)
        btn_remove.setStyleSheet("color: #c0392b; font-weight: bold;")

        row_layout.addWidget(QLabel("Столбец:"))
        row_layout.addWidget(col_combo)
        row_layout.addWidget(QLabel("Условие:"))
        row_layout.addWidget(op_combo)
        row_layout.addWidget(QLabel("Значение:"))
        row_layout.addWidget(val_edit)
        row_layout.addWidget(btn_remove)

        # Обновить операции при смене столбца
        def update_ops(idx):
            col_name = col_combo.currentData()
            col_type = next((t for c, _, t in self._columns if c == col_name), "text")
            op_combo.clear()
            op_combo.addItems(self.OPS.get(col_type, self.OPS["text"]))

        col_combo.currentIndexChanged.connect(update_ops)
        update_ops(0)  # инициализация

        # Удалить строку
        row_data = {"frame": row_frame, "col": col_combo, "op": op_combo, "val": val_edit}

        def remove_row():
            row_frame.deleteLater()
            if row_data in self._rows:
                self._rows.remove(row_data)

        btn_remove.clicked.connect(remove_row)

        self._rows_layout.addWidget(row_frame)
        self._rows.append(row_data)

        # Установить preset значения
        if preset_col:
            idx = col_combo.findData(preset_col)
            if idx >= 0:
                col_combo.setCurrentIndex(idx)
                update_ops(idx)
        if preset_op:
            idx = op_combo.findText(preset_op)
            if idx >= 0:
                op_combo.setCurrentIndex(idx)
        if preset_val:
            val_edit.setText(preset_val)

    def get_filters(self) -> list:
        """
        Вернуть список активных фильтров.
        Returns: [(col_name, op, val, col_type), ...]
        Пропускает строки с пустым значением.
        """
        result = []
        for row in self._rows:
            col_name = row["col"].currentData()
            op       = row["op"].currentText()
            val      = row["val"].text().strip()
            if not val:
                continue
            col_type = next((t for c, _, t in self._columns if c == col_name), "text")
            result.append((col_name, op, val, col_type))
        return result


class BaseTableView(QWidget):
    """
    Абстрактное табличное представление в стиле Access Datasheet View.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager.instance()
        self._data = []
        self._dirty_rows = {}
        self._current_row = -1

        self._build_ui()
        self.load_data()

    def _tname(self):
        v = self.table_name
        return v() if callable(v) else v

    def _pkcol(self):
        v = self.pk_column
        return v() if callable(v) else v

    # ── Абстрактные методы ────────────────────────────────────────────────────

    @property
    @abstractmethod
    def table_name(self) -> str: ...

    @property
    @abstractmethod
    def pk_column(self) -> str: ...

    @abstractmethod
    def columns(self) -> list:
        """
        Список кортежей: (column_name, label, col_type)
        col_type: 'text' | 'number' | 'date'
        """
        ...

    # ── Построение UI ─────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # — Панель действий —
        action_frame = QFrame()
        action_frame.setFrameShape(QFrame.StyledPanel)
        action_layout = QHBoxLayout(action_frame)
        action_layout.setContentsMargins(8, 6, 8, 6)

        btn_filter = QPushButton("🔍 Фильтры...")
        btn_filter.clicked.connect(self._open_filter_dialog)

        self.btn_clear_filter = QPushButton("✕ Сбросить фильтры")
        self.btn_clear_filter.clicked.connect(self._clear_filter)
        self.btn_clear_filter.setEnabled(False)

        self.filter_info = QLabel("Фильтры не применены")
        self.filter_info.setStyleSheet("color: #666; font-style: italic;")

        btn_save_all = QPushButton("💾 Сохранить изменения")
        btn_save_all.clicked.connect(self._save_all_dirty)

        btn_del = QPushButton("✕ Удалить строку")
        btn_del.setStyleSheet("color: #c0392b;")
        btn_del.clicked.connect(self._delete_row)

        action_layout.addWidget(btn_filter)
        action_layout.addWidget(self.btn_clear_filter)
        action_layout.addWidget(self.filter_info)
        action_layout.addStretch()
        action_layout.addWidget(btn_save_all)
        action_layout.addWidget(btn_del)

        layout.addWidget(action_frame)

        # Храним текущие активные фильтры
        self._active_filters = []  # список (col_name, op, val, col_type)

        # — Таблица —
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed
        )
        self.table.setSortingEnabled(True)
        self.table.cellChanged.connect(self._on_cell_changed)
        self.table.currentCellChanged.connect(self._on_row_changed)

        layout.addWidget(self.table)

        # — Статус —
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.status_label)

    # ── Загрузка данных ───────────────────────────────────────────────────────

    def load_data(self, where_clause=""):
        """Загрузить строки из БД в таблицу. where_clause — готовая строка без WHERE."""
        try:
            sql = f"SELECT * FROM {self._tname()}"
            if where_clause:
                sql += f" WHERE {where_clause}"
            sql += f" ORDER BY {self._pkcol()}"
            print(f"[SQL load_data] {sql}")
            self._data = self.db.fetchall(sql)
            self._dirty_rows.clear()
            self._populate_table()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка загрузки", str(e))

    def _populate_table(self):
        """Заполнить QTableWidget данными из self._data."""
        cols = self.columns()
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels([label for _, label, _ in cols])

        for row_idx, row in enumerate(self._data):
            self.table.insertRow(row_idx)
            for col_idx, (col_name, _, _) in enumerate(cols):
                value = getattr(row, col_name, "")
                item = QTableWidgetItem(str(value) if value is not None else "")
                # PK — только для чтения
                if col_name == self._pkcol():
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    item.setForeground(QColor("#999"))
                self.table.setItem(row_idx, col_idx, item)

        self.table.blockSignals(False)
        self.status_label.setText(f"Строк: {len(self._data)}")

    # ── Фильтрация ────────────────────────────────────────────────────────────

    @staticmethod
    def _build_condition(col_name, op, val, col_type):
        """
        Собрать одно SQL-условие как строку (без параметров — всё инлайн).
        ILIKE заменён на LOWER() LIKE LOWER() для совместимости с psqlODBC.
        """
        v_esc = val.replace("'", "''")  # экранируем кавычки

        if col_type == "text":
            v_low = v_esc.lower()
            if op == "содержит":
                return f"LOWER({col_name}) LIKE LOWER('%{v_low}%')"
            elif op == "начинается с":
                return f"LOWER({col_name}) LIKE LOWER('{v_low}%')"
            elif op == "заканчивается на":
                return f"LOWER({col_name}) LIKE LOWER('%{v_low}')"
            else:  # равно
                return f"LOWER({col_name}) = LOWER('{v_low}')"
        elif col_type == "number":
            op_map = {"равно": "=", "больше": ">", "меньше": "<",
                      "больше или равно": ">=", "меньше или равно": "<="}
            return f"{col_name} {op_map.get(op, '=')} {v_esc}"
        elif col_type == "date":
            op_map = {"равно": "=", "после": ">", "до": "<"}
            return f"{col_name} {op_map.get(op, '=')} '{v_esc}'"
        return ""

    def _open_filter_dialog(self):
        """Открыть диалог с несколькими фильтрами."""
        dlg = FilterDialog(self.columns(), self._active_filters.copy(), self)
        if dlg.exec_() == FilterDialog.Accepted:
            self._active_filters = dlg.get_filters()
            self._apply_active_filters()

    def _apply_active_filters(self):
        """Применить self._active_filters к таблице."""
        if not self._active_filters:
            self.load_data()
            self.filter_info.setText("Фильтры не применены")
            self.btn_clear_filter.setEnabled(False)
            return

        conditions = []
        for col_name, op, val, col_type in self._active_filters:
            cond = self._build_condition(col_name, op, val, col_type)
            if cond:
                conditions.append(cond)

        where = " AND ".join(conditions)
        self.load_data(where)

        # Обновить инфо-строку
        parts = []
        for col_name, op, val, _ in self._active_filters:
            label = next((lbl for c, lbl, _ in self.columns() if c == col_name), col_name)
            parts.append(f"{label} {op} «{val}»")
        self.filter_info.setText("Фильтр: " + "  И  ".join(parts))
        self.btn_clear_filter.setEnabled(True)

    def _clear_filter(self):
        self._active_filters = []
        self.filter_info.setText("Фильтры не применены")
        self.btn_clear_filter.setEnabled(False)
        self.load_data()

    # ── Редактирование ────────────────────────────────────────────────────────

    def _on_cell_changed(self, row_idx, col_idx):
        """Ячейка изменена — отметить строку как dirty."""
        col_name = self.columns()[col_idx][0]
        if col_name == self._pkcol():
            return
        item = self.table.item(row_idx, col_idx)
        if item is None:
            return
        if row_idx not in self._dirty_rows:
            self._dirty_rows[row_idx] = {}
        self._dirty_rows[row_idx][col_name] = item.text()

        # Покрасить строку чтобы было видно что изменена
        for c in range(self.table.columnCount()):
            it = self.table.item(row_idx, c)
            if it:
                it.setBackground(QColor("#fff3cd"))

    def _on_row_changed(self, curr_row, _c, prev_row, _pc):
        """При смене строки — автосохранение предыдущей если она dirty."""
        if prev_row >= 0 and prev_row in self._dirty_rows:
            self._save_row(prev_row)

    def _save_row(self, row_idx):
        """Сохранить одну изменённую строку в БД."""
        if row_idx not in self._dirty_rows:
            return
        changes = self._dirty_rows[row_idx]
        if not changes:
            return
        try:
            # Найти PK этой строки
            pk_col_idx = next(
                i for i, (c, _, _) in enumerate(self.columns()) if c == self._pkcol()
            )
            pk_item = self.table.item(row_idx, pk_col_idx)
            if pk_item is None:
                return
            pk_val = pk_item.text()

            set_clause = ", ".join([f"{c} = %s" for c in changes.keys()])
            vals = list(changes.values()) + [pk_val]
            self.db.execute(
                f"UPDATE {self._tname()} SET {set_clause} WHERE {self._pkcol()} = %s",
                vals
            )
            del self._dirty_rows[row_idx]

            # Убрать жёлтую подсветку
            for c in range(self.table.columnCount()):
                it = self.table.item(row_idx, c)
                if it:
                    it.setBackground(QColor("#d4edda"))
            self.status_label.setText(f"✔ Строка #{pk_val} сохранена")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения строки", str(e))

    def _save_all_dirty(self):
        """Сохранить все изменённые строки."""
        for row_idx in list(self._dirty_rows.keys()):
            self._save_row(row_idx)
        self.status_label.setText("✔ Все изменения сохранены")

    def _delete_row(self):
        """Удалить выбранную строку."""
        selected = self.table.currentRow()
        if selected < 0:
            return
        pk_col_idx = next(
            i for i, (c, _, _) in enumerate(self.columns()) if c == self._pkcol()
        )
        pk_item = self.table.item(selected, pk_col_idx)
        if pk_item is None:
            return
        pk_val = pk_item.text()

        ans = QMessageBox.question(
            self, "Удалить строку?",
            f"Удалить запись с ID = {pk_val}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ans == QMessageBox.Yes:
            try:
                self.db.execute(
                    f"DELETE FROM {self._tname()} WHERE {self._pkcol()} = %s",
                    (pk_val,)
                )
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка удаления", str(e))

    def refresh(self):
        """F5 — сохранить dirty и перезагрузить."""
        self._save_all_dirty()
        self.load_data()
        self.status_label.setText("↻ Таблица обновлена")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F5:
            self.refresh()
        else:
            super().keyPressEvent(event)


# ══════════════════════════════════════════════════════════════════════════════════
#  СЕКЦИЯ 5 — КОНКРЕТНЫЕ КЛАССЫ: EmployeeForm и EmployeeTableView
#
#  Это единственное место куда ты лезешь когда добавляешь новую таблицу.
#  Скопировал → переименовал → поменял table_name, fields, columns → готово.
# ══════════════════════════════════════════════════════════════════════════════════

class EmployeeForm(BaseForm):
    """
    Форма редактирования сотрудника.
    Поиск по фамилии с автодополнением полного ФИО.
    Поле "Предприятие" — ForeignKeyWidget: пользователь видит название,
    в БД пишется enterprise_id (integer).
    """

    @property
    def table_name(self):
        return "employees"

    @property
    def pk_column(self):
        return "id"

    def fields(self):
        return [
            ("last_name",      "Фамилия",      "text"),
            ("first_name",     "Имя",          "text"),
            ("middle_name",    "Отчество",     "text"),
            ("department",     "Отдел",        "combo:IT,Бухгалтерия,HR,Юридический,Маркетинг"),
            ("position",       "Должность",    "text"),
            ("birth_date",     "Дата рождения","date"),
            ("salary",         "Зарплата",     "number"),
            # fk:справочная_таблица:отображаемая_колонка:pk_колонка
            ("enterprise_id",  "Предприятие",  "fk:enterprises:name:id"),
        ]

    def search_column(self):
        return "last_name"

    def display_value(self, row):
        parts = [row.last_name, row.first_name]
        if hasattr(row, 'middle_name') and row.middle_name:
            parts.append(row.middle_name)
        return " ".join(p for p in parts if p)


# ─────────────────────────────────────────────────────────────────────────────────

class EnterpriseForm(BaseForm):
    """
    Форма редактирования предприятия.
    Поиск по названию предприятия.
    """

    @property
    def table_name(self):
        return "enterprises"

    @property
    def pk_column(self):
        return "id"

    def fields(self):
        return [
            ("name", "Название",  "text"),
            ("inn",  "ИНН",       "text"),
            ("city", "Город",     "text"),
        ]

    def search_column(self):
        return "name"

    def display_value(self, row):
        return row.name or ""


# ─────────────────────────────────────────────────────────────────────────────────

class EmployeeTableView(BaseTableView):
    """
    Табличное представление сотрудников.
    Колонка enterprise_id показывает числовой id —
    для красивого отображения названия используй форму.
    """

    @property
    def table_name(self):
        return "employees"

    @property
    def pk_column(self):
        return "id"

    def columns(self):
        return [
            ("id",            "ID",            "number"),
            ("last_name",     "Фамилия",       "text"),
            ("first_name",    "Имя",           "text"),
            ("middle_name",   "Отчество",      "text"),
            ("department",    "Отдел",         "text"),
            ("position",      "Должность",     "text"),
            ("birth_date",    "Дата рождения", "date"),
            ("salary",        "Зарплата",      "number"),
            ("enterprise_id", "Предприятие ID","number"),
        ]


# ─────────────────────────────────────────────────────────────────────────────────

class EnterpriseTableView(BaseTableView):
    """Табличное представление предприятий."""

    @property
    def table_name(self):
        return "enterprises"

    @property
    def pk_column(self):
        return "id"

    def columns(self):
        return [
            ("id",   "ID",       "number"),
            ("name", "Название", "text"),
            ("inn",  "ИНН",      "text"),
            ("city", "Город",    "text"),
        ]


# ══════════════════════════════════════════════════════════════════════════════════
#  СЕКЦИЯ 6 — MAIN WINDOW
#
#  QMainWindow с QMdiArea внутри.
#  Тулбар — QToolBar (можно перетащить к любой стороне окна).
#  Ctrl+T — переключение MDI / Вкладки (Tab mode).
#
#  Как добавить новую форму в тулбар:
#    1. Создай класс наследник BaseForm или BaseTableView (секция 5)
#    2. В _build_toolbar() добавь QAction и подключи к _open_XXX
#    3. Напиши метод _open_XXX аналогично _open_employee_form
# ══════════════════════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    """
    Главное окно приложения.

    MDI-режим: дочерние окна плавают внутри QMdiArea.
    Tab-режим:  дочерние окна отображаются как вкладки (Ctrl+T).
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AccessPy — Менеджер данных")
        self.resize(1280, 800)

        # ── MDI Area ──────────────────────────────────────────────────────────
        # Центральный виджет. Все формы и таблицы открываются как subwindow.
        self.mdi = QMdiArea()
        self.mdi.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.mdi.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setCentralWidget(self.mdi)

        self._tab_mode = False  # текущий режим отображения

        # ── Тулбар ────────────────────────────────────────────────────────────
        # QToolBar — перетаскивается к любой стороне окна (top/bottom/left/right)
        self._build_toolbar()

        # ── Статус-бар ────────────────────────────────────────────────────────
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Готов  ·  Ctrl+T — переключить режим MDI/Вкладки  ·  F5 — обновить активное окно")

        # ── Горячие клавиши ───────────────────────────────────────────────────
        # Ctrl+W — закрыть активное MDI окно
        close_action = QAction(self)
        close_action.setShortcut(QKeySequence("Ctrl+W"))
        close_action.triggered.connect(self._close_active)
        self.addAction(close_action)

        # Ctrl+T — переключить режим
        toggle_action = QAction(self)
        toggle_action.setShortcut(QKeySequence("Ctrl+T"))
        toggle_action.triggered.connect(self._toggle_tab_mode)
        self.addAction(toggle_action)

    # ── Построение тулбара ────────────────────────────────────────────────────

    def _build_toolbar(self):
        """
        Создать QToolBar с кнопками.
        Тулбар можно перетащить мышью к любой стороне окна.
        Чтобы добавить кнопку — скопируй блок QAction + addAction.
        """
        toolbar = QToolBar("Инструменты")
        toolbar.setMovable(True)          # ← перетаскивается
        toolbar.setFloatable(True)        # ← можно оторвать как окно
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # — Раздел: Сотрудники —
        act_emp_form = QAction("👤\nФорма\nсотрудника", self)
        act_emp_form.setToolTip("Открыть форму редактирования сотрудника")
        act_emp_form.triggered.connect(self._open_employee_form)
        toolbar.addAction(act_emp_form)

        act_emp_table = QAction("📋\nТаблица\nсотрудников", self)
        act_emp_table.setToolTip("Открыть таблицу всех сотрудников")
        act_emp_table.triggered.connect(self._open_employee_table)
        toolbar.addAction(act_emp_table)

        toolbar.addSeparator()

        # — Раздел: Управление окнами —
        act_tile = QAction("⊞\nМозаика", self)
        act_tile.setToolTip("Расположить окна мозаикой")
        act_tile.triggered.connect(self.mdi.tileSubWindows)
        toolbar.addAction(act_tile)

        act_cascade = QAction("❐\nКаскад", self)
        act_cascade.setToolTip("Расположить окна каскадом")
        act_cascade.triggered.connect(self.mdi.cascadeSubWindows)
        toolbar.addAction(act_cascade)

        act_close_all = QAction("✕\nЗакрыть\nвсе", self)
        act_close_all.setToolTip("Закрыть все дочерние окна")
        act_close_all.triggered.connect(self.mdi.closeAllSubWindows)
        toolbar.addAction(act_close_all)

        toolbar.addSeparator()

        # — Переключение режима —
        self.act_toggle = QAction("⧉\nВкладки", self)
        self.act_toggle.setToolTip("Переключить режим MDI / Вкладки (Ctrl+T)")
        self.act_toggle.triggered.connect(self._toggle_tab_mode)
        toolbar.addAction(self.act_toggle)

    # ── Фабрика MDI-окон ─────────────────────────────────────────────────────

    def _create_subwindow(self, widget: QWidget, title: str) -> QMdiSubWindow:
        """
        Обернуть виджет в QMdiSubWindow и добавить в MDI Area.

        В tab-режиме окно автоматически разворачивается на весь экран.
        В MDI-режиме показывается как плавающее окно.
        """
        sub = QMdiSubWindow()
        sub.setWidget(widget)
        sub.setWindowTitle(title)
        sub.setAttribute(Qt.WA_DeleteOnClose)
        self.mdi.addSubWindow(sub)

        if self._tab_mode:
            sub.showMaximized()
        else:
            sub.resize(620, 480)
            sub.show()

        return sub

    # ── Открыть конкретные окна ───────────────────────────────────────────────

    def _open_employee_form(self):
        """Открыть форму редактирования сотрудника."""
        form = EmployeeForm()
        self._create_subwindow(form, "👤 Форма сотрудника")
        self.status.showMessage("Форма сотрудника открыта")

    def _open_employee_table(self):
        """Открыть таблицу сотрудников."""
        table_view = EmployeeTableView()
        self._create_subwindow(table_view, "📋 Таблица сотрудников")
        self.status.showMessage("Таблица сотрудников открыта")

    # ── Управление окнами ─────────────────────────────────────────────────────

    def _close_active(self):
        """Закрыть активное MDI окно (Ctrl+W)."""
        active = self.mdi.activeSubWindow()
        if active:
            active.close()

    def _toggle_tab_mode(self):
        """
        Ctrl+T — переключить режим отображения.

        MDI-режим: окна плавают, их можно двигать и ресайзить.
        Tab-режим: каждое окно занимает весь экран, переключение через вкладки.
        """
        self._tab_mode = not self._tab_mode

        if self._tab_mode:
            self.mdi.setViewMode(QMdiArea.TabbedView)
            self.mdi.setTabsClosable(True)
            self.mdi.setTabsMovable(True)
            self.act_toggle.setText("⧉\nMDI")
            self.act_toggle.setToolTip("Переключить в режим плавающих окон (Ctrl+T)")
            self.status.showMessage("Режим: Вкладки  ·  Ctrl+T — вернуть MDI")
        else:
            self.mdi.setViewMode(QMdiArea.SubWindowView)
            self.act_toggle.setText("⧉\nВкладки")
            self.act_toggle.setToolTip("Переключить в режим вкладок (Ctrl+T)")
            self.status.showMessage("Режим: MDI  ·  Ctrl+T — переключить на вкладки")

    def closeEvent(self, event):
        """При закрытии главного окна — закрыть соединение с БД."""
        try:
            DatabaseManager.instance().close()
        except Exception:
            pass
        event.accept()


# ══════════════════════════════════════════════════════════════════════════════════
#  СЕКЦИЯ 7 — ТОЧКА ВХОДА
# ══════════════════════════════════════════════════════════════════════════════════

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Явный stylesheet — гарантирует чёрный текст везде: в таблицах, формах, комбобоксах
    app.setStyleSheet("""
        * {
            color: #1a1a1a;
            font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
            font-size: 13px;
        }
        QMainWindow, QMdiArea, QMdiSubWindow {
            background-color: #e8edf2;
        }
        QWidget {
            background-color: #f5f5f5;
            color: #1a1a1a;
        }
        QLineEdit, QDateEdit, QDoubleSpinBox, QSpinBox, QComboBox {
            background-color: #ffffff;
            color: #1a1a1a;
            border: 1px solid #c0c8d4;
            border-radius: 4px;
            padding: 4px 8px;
            min-height: 24px;
        }
        QLineEdit:focus, QDateEdit:focus, QDoubleSpinBox:focus {
            border: 1px solid #3478db;
        }
        QLineEdit:disabled, QDateEdit:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {
            background-color: #efefef;
            color: #888888;
        }
        QTableWidget {
            background-color: #ffffff;
            color: #1a1a1a;
            gridline-color: #d0d8e4;
            alternate-background-color: #eef2f8;
            selection-background-color: #3478db;
            selection-color: #ffffff;
        }
        QTableWidget::item {
            color: #1a1a1a;
            padding: 4px;
        }
        QHeaderView::section {
            background-color: #dde4ed;
            color: #1a1a1a;
            padding: 6px;
            border: none;
            border-right: 1px solid #c0c8d4;
            border-bottom: 1px solid #c0c8d4;
            font-weight: bold;
        }
        QPushButton {
            background-color: #3478db;
            color: #ffffff;
            border: none;
            border-radius: 4px;
            padding: 6px 14px;
            min-height: 26px;
        }
        QPushButton:hover {
            background-color: #2560c0;
        }
        QPushButton:pressed {
            background-color: #1a4fa0;
        }
        QPushButton:disabled {
            background-color: #b0b8c8;
            color: #ffffff;
        }
        QToolBar {
            background-color: #f0f4f8;
            border-bottom: 1px solid #c8d0dc;
            spacing: 4px;
            padding: 4px;
        }
        QToolButton {
            color: #1a1a1a;
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: 4px;
            padding: 4px 8px;
        }
        QToolButton:hover {
            background-color: #dde6f0;
            border-color: #b0bcd0;
        }
        QStatusBar {
            background-color: #e0e8f0;
            color: #444444;
        }
        QFrame[frameShape="1"] {
            border: 1px solid #c8d4e0;
            border-radius: 4px;
            background-color: #ffffff;
        }
        QLabel {
            color: #1a1a1a;
            background-color: transparent;
        }
        QMdiSubWindow {
            background-color: #f5f5f5;
        }
        QMdiSubWindow::title {
            color: #1a1a1a;
        }
        QCompleter QAbstractItemView {
            color: #1a1a1a;
            background-color: #ffffff;
            selection-background-color: #3478db;
            selection-color: #ffffff;
        }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()