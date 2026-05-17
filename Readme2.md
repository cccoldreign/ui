# Полное руководство: Создание SubDB на PyQt5 и pyodbc

## 📋 Оглавление
1. [Архитектура и основные концепции](#архитектура)
2. [Расширение DatabaseManager](#расширение-databasemanager)
3. [Система типов данных](#система-типов-данных)
4. [Автоматическое создание форм](#автоматическое-создание-форм)
5. [Обработка иностранных ключей](#обработка-иностранных-ключей)
6. [Отслеживание изменений](#отслеживание-изменений)
7. [Полные примеры](#полные-примеры)

---

## Архитектура

### Общий принцип работы

```
┌─────────────────┐
│   База данных   │
│   (PostgreSQL)  │
└────────┬────────┘
         │
         ↓
┌──────────────────────────┐
│   DatabaseManager        │ ← Управление соединением
│   + Schema Detection     │ ← Анализ структуры таблиц
└────────┬─────────────────┘
         │
         ↓
┌──────────────────────────┐
│   TableSchema            │ ← Метаданные о таблице
│   (типы, FK, индексы)    │
└────────┬─────────────────┘
         │
         ↓
┌──────────────────────────┐
│   AutoFormBuilder        │ ← Генерация форм по схеме
│   + Field Types          │
└────────┬─────────────────┘
         │
         ↓
┌──────────────────────────┐
│   PyQt5 Widgets          │ ← Визуальные компоненты
│   (QLineEdit, QComboBox) │
└────────┬─────────────────┘
         │
         ↓
┌──────────────────────────┐
│   ChangeTracker          │ ← Отслеживание изменений
│   + UpdateBuilder        │
└──────────────────────────┘
```

---

## Расширение DatabaseManager

### 1. Добавляем методы для анализа схемы

```python
# database_manager.py

import pyodbc
from typing import List, Dict, Tuple, Optional

class DatabaseManager:
    """Singleton-менеджер с поддержкой анализа схемы"""
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
        """Вставляем параметры прямо в SQL"""
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
                escaped = str(val).replace("'", "''")
                literal = f"'{escaped}'"
            result = result.replace("%s", literal, 1)
        return result, ()

    def fetchall(self, sql, params=()):
        """Выполнить SELECT, вернуть список строк"""
        cur = self.conn.cursor()
        built_sql, _ = self._build_sql(sql, params)
        print(f"[SQL] {built_sql[:120]}")
        cur.execute(built_sql)
        return cur.fetchall()

    def fetchone(self, sql, params=()):
        """Выполнить SELECT, вернуть одну строку"""
        cur = self.conn.cursor()
        built_sql, _ = self._build_sql(sql, params)
        print(f"[SQL] {built_sql[:120]}")
        cur.execute(built_sql)
        return cur.fetchone()

    def execute(self, sql, params=()):
        """Выполнить INSERT/UPDATE/DELETE с коммитом"""
        cur = self.conn.cursor()
        built_sql, _ = self._build_sql(sql, params)
        print(f"[SQL] {built_sql[:120]}")
        cur.execute(built_sql)
        self.conn.commit()

    def columns(self, table_name):
        """Вернуть список (name, type_code) колонок таблицы"""
        cur = self.conn.cursor()
        cur.execute(f"SELECT * FROM {table_name} LIMIT 1")
        return [(desc[0], desc[1]) for desc in cur.description]

    # ========== НОВЫЕ МЕТОДЫ ДЛЯ АНАЛИЗА СХЕМЫ ==========

    def get_table_schema(self, table_name: str) -> Dict:
        """
        Получить полную информацию о структуре таблицы.
        
        Возвращает:
            {
                'columns': [
                    {
                        'name': 'id',
                        'type': 'INTEGER',
                        'nullable': False,
                        'primary_key': True,
                        'foreign_key': None
                    },
                    {
                        'name': 'department_id',
                        'type': 'INTEGER',
                        'nullable': True,
                        'primary_key': False,
                        'foreign_key': ('departments', 'id')
                    },
                    ...
                ]
            }
        """
        cur = self.conn.cursor()
        schema = {'columns': []}

        # Получаем информацию о колонках
        cur.execute(f"SELECT * FROM {table_name} LIMIT 1")
        
        primary_keys = self._get_primary_keys(table_name)
        foreign_keys = self._get_foreign_keys(table_name)

        for desc in cur.description:
            col_name = desc[0]
            col_type = desc[1]  # type_code из pyodbc
            type_name = self._normalize_type_code(col_type, col_name, table_name)

            column_info = {
                'name': col_name,
                'type': type_name,
                'type_code': col_type,
                'nullable': True,  # pyodbc не предоставляет, может быть переопределено
                'primary_key': col_name in primary_keys,
                'foreign_key': foreign_keys.get(col_name, None)
            }
            schema['columns'].append(column_info)

        return schema

    def _get_primary_keys(self, table_name: str) -> set:
        """Получить набор имён первичных ключей таблицы"""
        cur = self.conn.cursor()
        try:
            # Для PostgreSQL
            sql = """
                SELECT column_name 
                FROM information_schema.key_column_usage
                WHERE table_name = %s AND constraint_type = 'PRIMARY KEY'
            """
            cur.execute(sql.replace('%s', f"'{table_name}'"))
            return {row[0] for row in cur.fetchall()}
        except:
            return set()

    def _get_foreign_keys(self, table_name: str) -> Dict[str, Tuple]:
        """
        Получить словарь иностранных ключей.
        
        Возвращает:
            {
                'department_id': ('departments', 'id'),
                'manager_id': ('employees', 'id')
            }
        """
        cur = self.conn.cursor()
        fk_dict = {}
        try:
            # Для PostgreSQL (через information_schema)
            sql = f"""
                SELECT 
                    kcu.column_name,
                    ccu.table_name as foreign_table_name,
                    ccu.column_name as foreign_column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu 
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.table_name = '{table_name}' 
                    AND tc.constraint_type = 'FOREIGN KEY'
            """
            cur.execute(sql)
            for row in cur.fetchall():
                col_name, fk_table, fk_col = row[0], row[1], row[2]
                fk_dict[col_name] = (fk_table, fk_col)
        except:
            pass
        
        return fk_dict

    def _normalize_type_code(self, type_code, col_name: str, table_name: str) -> str:
        """
        Преобразовать type_code в читаемое имя типа.
        pyodbc возвращает type_code, но нужно получить строковое имя.
        """
        cur = self.conn.cursor()
        try:
            sql = f"""
                SELECT data_type 
                FROM information_schema.columns
                WHERE table_name = '{table_name}' AND column_name = '{col_name}'
            """
            cur.execute(sql)
            result = cur.fetchone()
            return result[0] if result else str(type_code)
        except:
            return str(type_code)

    def get_referenced_data(self, table_name: str, id_column: str, 
                           display_column: str, filters: Dict = None) -> List[Tuple]:
        """
        Получить данные из связанной таблицы для автозаполнения.
        
        Пример:
            # Получить список подразделений (id, name)
            deps = db.get_referenced_data('departments', 'id', 'name')
            # → [('1', 'IT'), ('2', 'HR'), ...]
            
            # С фильтром
            deps = db.get_referenced_data(
                'departments', 'id', 'name', 
                filters={'active': True}
            )
        """
        where_clause = ""
        if filters:
            conditions = [f"{k} = {self._format_value(v)}" for k, v in filters.items()]
            where_clause = f"WHERE {' AND '.join(conditions)}"

        sql = f"SELECT {id_column}, {display_column} FROM {table_name} {where_clause}"
        return self.fetchall(sql)

    @staticmethod
    def _format_value(val):
        """Форматировать значение для вставки в SQL"""
        if val is None:
            return "NULL"
        elif isinstance(val, bool):
            return "TRUE" if val else "FALSE"
        elif isinstance(val, (int, float)):
            return str(val)
        else:
            escaped = str(val).replace("'", "''")
            return f"'{escaped}'"

    def close(self):
        self.conn.close()
        print("[DB] Соединение закрыто")
```

---

## Система типов данных

### 1. Класс для описания типов полей

```python
# field_types.py

from enum import Enum
from typing import Any, Optional, Callable

class FieldType(Enum):
    """Типы полей в БД"""
    TEXT = "TEXT"
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    DATETIME = "DATETIME"
    FOREIGN_KEY = "FOREIGN_KEY"

class FieldDefinition:
    """Описание поля таблицы"""
    
    def __init__(
        self,
        name: str,
        field_type: FieldType,
        display_name: str = None,
        nullable: bool = True,
        primary_key: bool = False,
        foreign_key: tuple = None,  # (table_name, id_column, display_column)
        validators: list = None,
        read_only: bool = False,
        default_value: Any = None
    ):
        self.name = name
        self.field_type = field_type
        self.display_name = display_name or name
        self.nullable = nullable
        self.primary_key = primary_key
        self.foreign_key = foreign_key  # (table_name, id_col, display_col)
        self.validators = validators or []
        self.read_only = read_only
        self.default_value = default_value
        self.current_value = None
        self.original_value = None

    def __repr__(self):
        return f"<Field {self.name}: {self.field_type.value}>"

class TableSchema:
    """Метаданные таблицы"""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.fields: Dict[str, FieldDefinition] = {}
        self.primary_keys = []

    def add_field(self, field: FieldDefinition):
        """Добавить поле"""
        self.fields[field.name] = field
        if field.primary_key:
            self.primary_keys.append(field.name)

    def get_field(self, name: str) -> Optional[FieldDefinition]:
        """Получить поле по имени"""
        return self.fields.get(name)

    def get_fields_by_type(self, field_type: FieldType) -> List[FieldDefinition]:
        """Получить поля определённого типа"""
        return [f for f in self.fields.values() if f.field_type == field_type]

    def to_dict(self) -> Dict:
        """Преобразовать схему в словарь"""
        return {
            'table_name': self.table_name,
            'fields': {
                name: {
                    'name': field.name,
                    'type': field.field_type.value,
                    'display_name': field.display_name,
                    'nullable': field.nullable,
                    'primary_key': field.primary_key,
                    'read_only': field.read_only,
                    'foreign_key': field.foreign_key
                }
                for name, field in self.fields.items()
            }
        }
```

### 2. Функция для автоматического создания схемы из БД

```python
# schema_builder.py

from database_manager import DatabaseManager
from field_types import FieldType, FieldDefinition, TableSchema

def build_schema_from_database(table_name: str) -> TableSchema:
    """
    Автоматически создать схему таблицы из БД.
    
    Пример:
        schema = build_schema_from_database('employees')
        # Теперь schema содержит все поля с правильными типами
    """
    db = DatabaseManager.instance()
    schema_info = db.get_table_schema(table_name)
    schema = TableSchema(table_name)

    for col_info in schema_info['columns']:
        col_name = col_info['name']
        col_type_str = col_info['type'].upper()
        is_fk = col_info['foreign_key'] is not None
        is_pk = col_info['primary_key']

        # Определяем тип поля
        if is_fk:
            fk_table, fk_id_col = col_info['foreign_key']
            # Предполагаем display column = 'name'
            fk_display_col = _find_display_column(fk_table)
            field_type = FieldType.FOREIGN_KEY
            foreign_key_info = (fk_table, fk_id_col, fk_display_col)
        elif 'INT' in col_type_str:
            field_type = FieldType.INTEGER
            foreign_key_info = None
        elif 'DECIMAL' in col_type_str or 'NUMERIC' in col_type_str:
            field_type = FieldType.DECIMAL
            foreign_key_info = None
        elif 'BOOL' in col_type_str:
            field_type = FieldType.BOOLEAN
            foreign_key_info = None
        elif 'DATE' in col_type_str:
            if 'TIME' in col_type_str:
                field_type = FieldType.DATETIME
            else:
                field_type = FieldType.DATE
            foreign_key_info = None
        else:  # TEXT, VARCHAR, etc.
            field_type = FieldType.TEXT
            foreign_key_info = None

        field = FieldDefinition(
            name=col_name,
            field_type=field_type,
            display_name=_humanize_name(col_name),
            nullable=col_info['nullable'],
            primary_key=is_pk,
            foreign_key=foreign_key_info,
            read_only=is_pk  # Первичные ключи обычно read-only
        )

        schema.add_field(field)

    return schema

def _find_display_column(table_name: str) -> str:
    """
    Найти подходящую колонку для отображения в иностранном ключе.
    Порядок приоритета: 'name', 'title', 'description', первая текстовая колонка
    """
    db = DatabaseManager.instance()
    schema = build_schema_from_database(table_name)
    
    candidates = ['name', 'title', 'description']
    for candidate in candidates:
        if candidate in schema.fields:
            return candidate
    
    # Найти первую текстовую колонку
    for field in schema.fields.values():
        if field.field_type == FieldType.TEXT and not field.primary_key:
            return field.name
    
    # Fallback: вернуть первую колонку (не PK)
    for field in schema.fields.values():
        if not field.primary_key:
            return field.name
    
    return 'id'

def _humanize_name(snake_case: str) -> str:
    """Преобразовать snake_case в 'Human Readable'"""
    return ' '.join(word.capitalize() for word in snake_case.split('_'))
```

---

## Автоматическое создание форм

### 1. Базовые виджеты с поддержкой автозаполнения

```python
# form_widgets.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QCompleter, QSizePolicy
)
from PyQt5.QtCore import Qt, QStringListModel, QDate
from typing import Optional, Callable, List

class AutoCompleteLineEdit(QLineEdit):
    """QLineEdit с автозаполнением и кешированием данных"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.completer = QCompleter()
        self.setCompleter(self.completer)
        self._data_cache = []  # [(id, display), ...]
        self._id_to_display = {}  # id → display
        self._display_to_id = {}  # display → id

    def set_autocomplete_data(self, data: List[tuple], 
                             id_column_idx: int = 0, 
                             display_column_idx: int = 1):
        """
        Установить данные для автозаполнения.
        
        Пример:
            deps = [('1', 'IT'), ('2', 'HR'), ('3', 'Finance')]
            edit.set_autocomplete_data(deps, id_column_idx=0, display_column_idx=1)
        """
        self._data_cache = list(data)
        self._id_to_display = {
            row[id_column_idx]: row[display_column_idx] 
            for row in data
        }
        self._display_to_id = {
            row[display_column_idx]: row[id_column_idx] 
            for row in data
        }
        
        # Обновляем completer
        display_values = [row[display_column_idx] for row in data]
        model = QStringListModel(display_values)
        self.completer.setModel(model)

    def get_selected_id(self) -> Optional[str]:
        """Получить ID выбранного значения"""
        display_text = self.text()
        return self._display_to_id.get(display_text)

    def set_value_by_id(self, value_id):
        """Установить значение по ID"""
        if value_id in self._id_to_display:
            self.setText(self._id_to_display[value_id])
        else:
            self.clear()

    def get_data_cache(self) -> List[tuple]:
        """Получить кеш данных"""
        return self._data_cache


class ForeignKeyComboBox(QComboBox):
    """QComboBox для иностранных ключей с автоматической загрузкой"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._id_list = []  # [id1, id2, ...]
        self._selected_id = None

    def populate_from_table(self, table_name: str, id_column: str, 
                           display_column: str, filters: dict = None):
        """Загрузить значения из таблицы БД"""
        from database_manager import DatabaseManager
        db = DatabaseManager.instance()
        data = db.get_referenced_data(table_name, id_column, display_column, filters)
        
        self._id_list = []
        self.clear()
        
        for id_val, display_val in data:
            self._id_list.append(id_val)
            self.addItem(str(display_val))

    def get_selected_id(self):
        """Получить ID выбранного элемента"""
        idx = self.currentIndex()
        return self._id_list[idx] if 0 <= idx < len(self._id_list) else None

    def set_value_by_id(self, value_id):
        """Установить значение по ID"""
        try:
            idx = self._id_list.index(value_id)
            self.setCurrentIndex(idx)
        except ValueError:
            self.setCurrentIndex(-1)
```

### 2. Класс для автоматического построения формы

```python
# form_builder.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QSpinBox, QDoubleSpinBox, QCheckBox, QDateEdit, QScrollArea,
    QFrame
)
from PyQt5.QtCore import QDate, pyqtSignal
from field_types import FieldType, FieldDefinition, TableSchema
from form_widgets import AutoCompleteLineEdit, ForeignKeyComboBox
from typing import Dict, Optional, List

class FormRow:
    """Описание одной строки в форме"""
    
    def __init__(self, *fields, spacing: int = 10, sizes: List[int] = None):
        """
        Создать строку из полей.
        
        Пример:
            row = FormRow(
                ('name', FieldType.TEXT),
                ('surname', FieldType.TEXT),
                spacing=20,
                sizes=[150, 150]  # Ширина каждого поля
            )
        """
        self.fields = fields
        self.spacing = spacing
        self.sizes = sizes or []

class AutoFormBuilder:
    """Автоматическое построение PyQt5 форм из схемы таблицы"""
    
    def __init__(self, schema: TableSchema):
        self.schema = schema
        self.widgets: Dict[str, QWidget] = {}
        self.original_values: Dict[str, any] = {}
        self.form_widget = None

    def build_form(self) -> QWidget:
        """
        Создать основной виджет формы.
        
        Возвращает:
            QWidget с всеми полями
        """
        self.form_widget = QWidget()
        layout = QVBoxLayout()
        
        for field_name, field in self.schema.fields.items():
            row_layout = QHBoxLayout()
            
            # Создаём label
            label = QLabel(f"{field.display_name}:")
            label.setMinimumWidth(150)
            row_layout.addWidget(label)
            
            # Создаём widget поля
            widget = self._create_field_widget(field)
            self.widgets[field_name] = widget
            
            row_layout.addWidget(widget)
            row_layout.addStretch()
            
            layout.addLayout(row_layout)
        
        self.form_widget.setLayout(layout)
        return self.form_widget

    def _create_field_widget(self, field: FieldDefinition) -> QWidget:
        """Создать виджет для поля в зависимости от типа"""
        
        if field.field_type == FieldType.TEXT:
            widget = QLineEdit()
            widget.setReadOnly(field.read_only)
            
        elif field.field_type == FieldType.INTEGER:
            widget = QSpinBox()
            widget.setRange(-999999, 999999)
            widget.setReadOnly(field.read_only)
            
        elif field.field_type == FieldType.DECIMAL:
            widget = QDoubleSpinBox()
            widget.setRange(-999999.99, 999999.99)
            widget.setDecimals(2)
            widget.setReadOnly(field.read_only)
            
        elif field.field_type == FieldType.BOOLEAN:
            widget = QCheckBox()
            widget.setEnabled(not field.read_only)
            
        elif field.field_type == FieldType.DATE:
            widget = QDateEdit()
            widget.setDate(QDate.currentDate())
            widget.setReadOnly(field.read_only)
            
        elif field.field_type == FieldType.DATETIME:
            widget = QDateEdit()
            widget.setDateTime(QDateTime.currentDateTime())
            widget.setReadOnly(field.read_only)
            
        elif field.field_type == FieldType.FOREIGN_KEY:
            widget = ForeignKeyComboBox()
            # Загружаем данные из связанной таблицы
            fk_table, fk_id_col, fk_display_col = field.foreign_key
            widget.populate_from_table(fk_table, fk_id_col, fk_display_col)
            widget.setEnabled(not field.read_only)
            
        else:
            widget = QLineEdit()
            widget.setReadOnly(field.read_only)
        
        return widget

    def build_custom_form(self, *rows: FormRow) -> QWidget:
        """
        Создать форму с кастомным расположением полей.
        
        Пример:
            form = builder.build_custom_form(
                FormRow('name', 'surname', spacing=20, sizes=[150, 150]),
                FormRow('email', spacing=10, sizes=[300])
            )
        """
        self.form_widget = QWidget()
        main_layout = QVBoxLayout()
        
        for row in rows:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(row.spacing)
            
            for i, field_name in enumerate(row.fields):
                field = self.schema.get_field(field_name)
                if not field:
                    continue
                
                # Label
                label = QLabel(f"{field.display_name}:")
                if row.sizes and i < len(row.sizes):
                    label.setMaximumWidth(100)
                row_layout.addWidget(label)
                
                # Widget
                widget = self._create_field_widget(field)
                self.widgets[field_name] = widget
                
                if row.sizes and i < len(row.sizes):
                    widget.setMaximumWidth(row.sizes[i])
                
                row_layout.addWidget(widget)
            
            row_layout.addStretch()
            main_layout.addLayout(row_layout)
        
        main_layout.addStretch()
        self.form_widget.setLayout(main_layout)
        return self.form_widget

    def set_values(self, data: Dict):
        """Установить значения полей из словаря"""
        for field_name, value in data.items():
            self.set_field_value(field_name, value)
            self.original_values[field_name] = value

    def set_field_value(self, field_name: str, value):
        """Установить значение одного поля"""
        if field_name not in self.widgets:
            return
        
        widget = self.widgets[field_name]
        field = self.schema.get_field(field_name)
        
        if isinstance(widget, QLineEdit):
            widget.setText(str(value) if value else "")
        elif isinstance(widget, QSpinBox):
            widget.setValue(int(value) if value else 0)
        elif isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(value) if value else 0.0)
        elif isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QDateEdit):
            if value:
                widget.setDate(QDate.fromString(str(value), "yyyy-MM-dd"))
        elif isinstance(widget, ForeignKeyComboBox):
            widget.set_value_by_id(value)

    def get_values(self) -> Dict:
        """Получить текущие значения всех полей"""
        values = {}
        for field_name, widget in self.widgets.items():
            if isinstance(widget, QLineEdit):
                values[field_name] = widget.text()
            elif isinstance(widget, QSpinBox):
                values[field_name] = widget.value()
            elif isinstance(widget, QDoubleSpinBox):
                values[field_name] = widget.value()
            elif isinstance(widget, QCheckBox):
                values[field_name] = widget.isChecked()
            elif isinstance(widget, QDateEdit):
                values[field_name] = widget.date().toString("yyyy-MM-dd")
            elif isinstance(widget, ForeignKeyComboBox):
                values[field_name] = widget.get_selected_id()
        
        return values
```

---

## Обработка иностранных ключей

### 1. Система загрузки и кеширования данных FK

```python
# foreign_key_manager.py

from typing import Dict, List, Tuple, Optional
from database_manager import DatabaseManager

class ForeignKeyManager:
    """Управление загрузкой и кешированием данных иностранных ключей"""
    
    def __init__(self):
        self._cache: Dict[str, List[Tuple]] = {}  # table_name → data
        self.db = DatabaseManager.instance()

    def load_reference_data(self, table_name: str, id_column: str, 
                           display_column: str, filters: Dict = None) -> List[Tuple]:
        """
        Загрузить данные для иностранного ключа с кешированием.
        
        Пример:
            fk_mgr = ForeignKeyManager()
            # Первый вызов — запрос к БД
            deps = fk_mgr.load_reference_data('departments', 'id', 'name')
            # Второй вызов — из кеша
            deps = fk_mgr.load_reference_data('departments', 'id', 'name')
        """
        cache_key = f"{table_name}_{id_column}_{display_column}"
        
        if cache_key not in self._cache:
            data = self.db.get_referenced_data(
                table_name, id_column, display_column, filters
            )
            self._cache[cache_key] = list(data)
        
        return self._cache[cache_key]

    def get_display_value(self, table_name: str, id_column: str,
                         display_column: str, id_value) -> Optional[str]:
        """
        Получить display value по ID.
        
        Пример:
            dept_name = fk_mgr.get_display_value(
                'departments', 'id', 'name', '1'
            )
            # → 'IT'
        """
        data = self.load_reference_data(table_name, id_column, display_column)
        
        for id_val, display_val in data:
            if id_val == id_value:
                return display_val
        
        return None

    def get_id_value(self, table_name: str, id_column: str,
                    display_column: str, display_value: str) -> Optional:
        """
        Получить ID по display value.
        
        Пример:
            dept_id = fk_mgr.get_id_value(
                'departments', 'id', 'name', 'IT'
            )
            # → '1'
        """
        data = self.load_reference_data(table_name, id_column, display_column)
        
        for id_val, disp_val in data:
            if disp_val == display_value:
                return id_val
        
        return None

    def clear_cache(self, table_name: Optional[str] = None):
        """
        Очистить кеш.
        Если table_name не указан, очищается весь кеш.
        """
        if table_name is None:
            self._cache.clear()
        else:
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(table_name)]
            for k in keys_to_remove:
                del self._cache[k]
```

### 2. Интеграция с формой

```python
# В form_builder.py добавляем поддержку ForeignKeyManager

class AutoFormBuilder:
    # ... существующий код ...
    
    def __init__(self, schema: TableSchema, fk_manager: Optional['ForeignKeyManager'] = None):
        self.schema = schema
        self.widgets: Dict[str, QWidget] = {}
        self.original_values: Dict[str, any] = {}
        self.form_widget = None
        self.fk_manager = fk_manager or ForeignKeyManager()
    
    def _create_field_widget(self, field: FieldDefinition) -> QWidget:
        """Создать виджет для поля"""
        
        # ... предыдущий код для других типов ...
        
        elif field.field_type == FieldType.FOREIGN_KEY:
            widget = ForeignKeyComboBox()
            fk_table, fk_id_col, fk_display_col = field.foreign_key
            
            # Используем ForeignKeyManager для загрузки данных
            data = self.fk_manager.load_reference_data(
                fk_table, fk_id_col, fk_display_col
            )
            
            # Заполняем комбобокс
            widget._id_list = []
            widget.clear()
            for id_val, display_val in data:
                widget._id_list.append(id_val)
                widget.addItem(str(display_val))
            
            widget.setEnabled(not field.read_only)
        
        return widget
```

---

## Отслеживание изменений

### 1. Система отслеживания изменений

```python
# change_tracker.py

from typing import Dict, Any, Set, List
from dataclasses import dataclass
from enum import Enum

class ChangeType(Enum):
    """Тип изменения"""
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    DELETED = "DELETED"
    UNCHANGED = "UNCHANGED"

@dataclass
class FieldChange:
    """Информация об изменении поля"""
    field_name: str
    original_value: Any
    new_value: Any
    changed: bool

class ChangeTracker:
    """Отслеживание изменений в форме"""
    
    def __init__(self, original_data: Dict[str, Any]):
        """
        Инициализировать трекер.
        
        Пример:
            tracker = ChangeTracker({'id': 1, 'name': 'John', 'salary': 5000})
        """
        self.original_data = dict(original_data)
        self.current_data = dict(original_data)
        self.change_history: List[Dict] = []

    def update_current_data(self, new_data: Dict[str, Any]):
        """Обновить текущие значения (из формы)"""
        self.current_data = dict(new_data)

    def get_changed_fields(self) -> Dict[str, FieldChange]:
        """
        Получить только изменённые поля.
        
        Возвращает:
            {
                'name': FieldChange('name', 'John', 'Jane', True),
                'salary': FieldChange('salary', 5000, 6000, True)
            }
        """
        changes = {}
        
        all_keys = set(self.original_data.keys()) | set(self.current_data.keys())
        
        for key in all_keys:
            original = self.original_data.get(key)
            current = self.current_data.get(key)
            
            # Преобразуем для сравнения (строки из QLineEdit и т.д.)
            is_changed = self._compare_values(original, current)
            
            if is_changed:
                changes[key] = FieldChange(
                    field_name=key,
                    original_value=original,
                    new_value=current,
                    changed=True
                )
        
        return changes

    def get_changed_fields_dict(self) -> Dict[str, Any]:
        """
        Получить словарь только изменённых полей для UPDATE.
        
        Возвращает:
            {'name': 'Jane', 'salary': 6000}
        """
        changes = self.get_changed_fields()
        return {field: change.new_value for field, change in changes.items()}

    def has_changes(self) -> bool:
        """Были ли изменения?"""
        return len(self.get_changed_fields()) > 0

    def get_change_summary(self) -> str:
        """Получить текстовое описание изменений"""
        changes = self.get_changed_fields()
        
        if not changes:
            return "Нет изменений"
        
        lines = ["Изменения:"]
        for field_name, change in changes.items():
            lines.append(
                f"  • {field_name}: {change.original_value} → {change.new_value}"
            )
        
        return "\n".join(lines)

    def reset(self):
        """Сбросить на исходные значения"""
        self.current_data = dict(self.original_data)

    def commit(self):
        """Принять изменения как новое исходное состояние"""
        self.original_data = dict(self.current_data)
        self.change_history.append({
            'timestamp': __import__('datetime').datetime.now(),
            'data': dict(self.current_data)
        })

    @staticmethod
    def _compare_values(val1: Any, val2: Any) -> bool:
        """Безопасное сравнение значений разных типов"""
        # Преобразуем оба значения в строки для сравнения
        str1 = str(val1).strip() if val1 is not None else ""
        str2 = str(val2).strip() if val2 is not None else ""
        return str1 != str2
```

### 2. Класс для автоматического создания UPDATE запроса

```python
# update_builder.py

from typing import Dict, Any, List
from database_manager import DatabaseManager
from field_types import TableSchema

class UpdateBuilder:
    """Построение UPDATE запроса только для изменённых полей"""
    
    def __init__(self, schema: TableSchema, table_name: str):
        self.schema = schema
        self.table_name = table_name
        self.db = DatabaseManager.instance()

    def build_update_sql(self, changed_fields: Dict[str, Any], 
                        primary_key_values: Dict[str, Any]) -> str:
        """
        Построить UPDATE запрос только для изменённых полей.
        
        Пример:
            builder = UpdateBuilder(schema, 'employees')
            sql = builder.build_update_sql(
                {'name': 'Jane', 'salary': 6000},
                {'id': 1}
            )
            # → UPDATE employees SET name='Jane', salary=6000 WHERE id=1
        """
        if not changed_fields:
            raise ValueError("Нет изменённых полей")

        set_clauses = []
        for field_name, value in changed_fields.items():
            formatted_value = self._format_value(value)
            set_clauses.append(f"{field_name} = {formatted_value}")

        where_clauses = []
        for pk_name, pk_value in primary_key_values.items():
            formatted_pk = self._format_value(pk_value)
            where_clauses.append(f"{pk_name} = {formatted_pk}")

        set_part = ", ".join(set_clauses)
        where_part = " AND ".join(where_clauses)

        return f"UPDATE {self.table_name} SET {set_part} WHERE {where_part}"

    def execute_update(self, changed_fields: Dict[str, Any], 
                      primary_key_values: Dict[str, Any]) -> bool:
        """
        Выполнить UPDATE с изменённымиполями.
        
        Возвращает:
            True если обновление успешно, False иначе
        """
        if not changed_fields:
            print("[UPDATE] Нет изменённых полей, пропускаем")
            return False

        sql = self.build_update_sql(changed_fields, primary_key_values)
        
        try:
            self.db.execute(sql)
            print(f"[UPDATE] Успешно обновлено {len(changed_fields)} полей")
            return True
        except Exception as e:
            print(f"[UPDATE] Ошибка: {e}")
            return False

    @staticmethod
    def _format_value(value: Any) -> str:
        """Форматировать значение для SQL"""
        if value is None:
            return "NULL"
        elif isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            escaped = str(value).replace("'", "''")
            return f"'{escaped}'"

    def build_insert_sql(self, field_values: Dict[str, Any]) -> str:
        """
        Построить INSERT запрос.
        
        Пример:
            sql = builder.build_insert_sql({
                'name': 'John',
                'salary': 5000,
                'department_id': '1'
            })
        """
        fields = list(field_values.keys())
        values = [self._format_value(field_values[f]) for f in fields]

        fields_str = ", ".join(fields)
        values_str = ", ".join(values)

        return f"INSERT INTO {self.table_name} ({fields_str}) VALUES ({values_str})"

    def execute_insert(self, field_values: Dict[str, Any]) -> bool:
        """Выполнить INSERT"""
        sql = self.build_insert_sql(field_values)
        
        try:
            self.db.execute(sql)
            print(f"[INSERT] Успешно вставлено")
            return True
        except Exception as e:
            print(f"[INSERT] Ошибка: {e}")
            return False
```

---

## Полные примеры

### Пример 1: Простое приложение для управления сотрудниками

```python
# main_app.py

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, 
    QWidget, QMessageBox, QScrollArea
)
from PyQt5.QtCore import Qt

from database_manager import DatabaseManager
from schema_builder import build_schema_from_database
from form_builder import AutoFormBuilder
from change_tracker import ChangeTracker
from update_builder import UpdateBuilder
from foreign_key_manager import ForeignKeyManager

class EmployeeWindow(QMainWindow):
    """Главное окно приложения для управления сотрудниками"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Управление сотрудниками")
        self.setGeometry(100, 100, 800, 600)
        
        # Инициализация БД
        self.db = DatabaseManager.instance()
        self.fk_manager = ForeignKeyManager()
        
        # Построение схемы
        self.schema = build_schema_from_database('employees')
        
        # Построение формы
        self.form_builder = AutoFormBuilder(self.schema, self.fk_manager)
        
        # Создаём UI
        self._setup_ui()
        
        # Загружаем данные сотрудника (пример с ID 1)
        self._load_employee(1)
    
    def _setup_ui(self):
        """Создать пользовательский интерфейс"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        
        # Создаём форму
        form_widget = self.form_builder.build_form()
        
        scroll = QScrollArea()
        scroll.setWidget(form_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        # Кнопки
        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self._on_save)
        layout.addWidget(btn_save)
        
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self._on_cancel)
        layout.addWidget(btn_cancel)
        
        central_widget.setLayout(layout)
    
    def _load_employee(self, employee_id: int):
        """Загрузить данные сотрудника"""
        result = self.db.fetchone(
            f"SELECT * FROM employees WHERE id = {employee_id}"
        )
        
        if result:
            # Преобразуем Row в словарь
            data = dict(zip(
                [desc[0] for desc in self.db.cursor().description],
                result
            ))
            
            # Заполняем форму
            self.form_builder.set_values(data)
            
            # Инициализируем трекер изменений
            self.change_tracker = ChangeTracker(data)
    
    def _on_save(self):
        """Обработчик кнопки 'Сохранить'"""
        # Получаем текущие значения из формы
        current_values = self.form_builder.get_values()
        
        # Обновляем трекер
        self.change_tracker.update_current_data(current_values)
        
        # Проверяем, есть ли изменения
        if not self.change_tracker.has_changes():
            QMessageBox.information(self, "Информация", "Нет изменений для сохранения")
            return
        
        # Получаем только изменённые поля
        changed_fields = self.change_tracker.get_changed_fields_dict()
        
        # Строим и выполняем UPDATE
        update_builder = UpdateBuilder(self.schema, 'employees')
        
        # Получаем PK для WHERE условия
        pk_values = {
            pk_name: self.form_builder.original_values[pk_name]
            for pk_name in self.schema.primary_keys
        }
        
        if update_builder.execute_update(changed_fields, pk_values):
            QMessageBox.information(self, "Успех", "Данные сохранены")
            self.change_tracker.commit()
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось сохранить данные")
    
    def _on_cancel(self):
        """Обработчик кнопки 'Отмена'"""
        self.change_tracker.reset()
        # Переустанавливаем значения в форму
        self.form_builder.set_values(self.change_tracker.original_data)
        QMessageBox.information(self, "Информация", "Изменения отменены")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = EmployeeWindow()
    window.show()
    sys.exit(app.exec_())
```

### Пример 2: Форма с кастомным расположением

```python
# custom_form_example.py

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton
from form_builder import AutoFormBuilder, FormRow
from schema_builder import build_schema_from_database
from foreign_key_manager import ForeignKeyManager

class CustomFormWindow(QMainWindow):
    """Окно с кастомным расположением полей"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Форма с кастомным расположением")
        self.setGeometry(100, 100, 800, 400)
        
        # Построение схемы
        schema = build_schema_from_database('employees')
        fk_manager = ForeignKeyManager()
        
        # Построение формы с кастомным расположением
        form_builder = AutoFormBuilder(schema, fk_manager)
        
        # Две колонки в одной строке
        form_widget = form_builder.build_custom_form(
            FormRow('name', 'surname', spacing=20, sizes=[150, 150]),
            FormRow('email', spacing=10, sizes=[300]),
            FormRow('department_id', spacing=10, sizes=[200]),
            FormRow('salary', spacing=10, sizes=[150])
        )
        
        layout = QVBoxLayout()
        layout.addWidget(form_widget)
        
        btn_save = QPushButton("Сохранить")
        layout.addWidget(btn_save)
        
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = CustomFormWindow()
    window.show()
    sys.exit(app.exec_())
```

### Пример 3: Использование ChangeTracker

```python
# change_tracking_example.py

from change_tracker import ChangeTracker

# Исходные данные
original = {
    'id': 1,
    'name': 'John Doe',
    'salary': 5000,
    'department_id': 1
}

# Создаём трекер
tracker = ChangeTracker(original)

# Пользователь изменил некоторые значения
updated = {
    'id': 1,
    'name': 'Jane Doe',  # Изменено
    'salary': 6000,       # Изменено
    'department_id': 1    # Не изменено
}

tracker.update_current_data(updated)

# Проверяем изменения
print(f"Есть ли изменения? {tracker.has_changes()}")
# → True

print(f"Изменённые поля: {tracker.get_changed_fields_dict()}")
# → {'name': 'Jane Doe', 'salary': 6000}

print(tracker.get_change_summary())
# → Изменения:
#   • name: John Doe → Jane Doe
#   • salary: 5000 → 6000
```

---

## Практический рецепт: Полный CRUD интерфейс

```python
# full_crud_app.py

class FullCRUDWindow(QMainWindow):
    """Полный CRUD интерфейс с поиском, редактированием и удалением"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CRUD Приложение")
        self.setGeometry(100, 100, 1000, 700)
        
        self.db = DatabaseManager.instance()
        self.schema = build_schema_from_database('employees')
        self.fk_manager = ForeignKeyManager()
        self.current_record_id = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Создать UI с поиском и формой"""
        main_layout = QVBoxLayout()
        
        # Панель поиска
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Поиск по имени:"))
        self.search_input = QLineEdit()
        self.search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_input)
        
        btn_new = QPushButton("Новый запись")
        btn_new.clicked.connect(self._on_new)
        search_layout.addWidget(btn_new)
        
        main_layout.addLayout(search_layout)
        
        # Список результатов поиска
        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self._on_select_record)
        main_layout.addWidget(self.results_list)
        
        # Форма редактирования
        self.form_builder = AutoFormBuilder(self.schema, self.fk_manager)
        form_widget = self.form_builder.build_form()
        main_layout.addWidget(form_widget)
        
        # Кнопки действий
        button_layout = QHBoxLayout()
        
        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self._on_save)
        button_layout.addWidget(btn_save)
        
        btn_delete = QPushButton("Удалить")
        btn_delete.clicked.connect(self._on_delete)
        button_layout.addWidget(btn_delete)
        
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self._on_cancel)
        button_layout.addWidget(btn_cancel)
        
        main_layout.addLayout(button_layout)
        
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
    
    def _on_search(self, query: str):
        """Поиск по имени"""
        self.results_list.clear()
        
        if not query:
            return
        
        sql = f"SELECT id, name FROM employees WHERE name ILIKE '%{query}%' LIMIT 10"
        results = self.db.fetchall(sql)
        
        for emp_id, emp_name in results:
            item = QListWidgetItem(f"{emp_id} - {emp_name}")
            item.setData(Qt.UserRole, emp_id)
            self.results_list.addItem(item)
    
    def _on_select_record(self, item: QListWidgetItem):
        """Выбор записи из списка"""
        emp_id = item.data(Qt.UserRole)
        self._load_employee(emp_id)
    
    def _load_employee(self, emp_id: int):
        """Загрузить сотрудника в форму"""
        result = self.db.fetchone(f"SELECT * FROM employees WHERE id = {emp_id}")
        
        if result:
            cur = self.db.cursor()
            cur.execute("SELECT * FROM employees LIMIT 1")
            data = dict(zip([desc[0] for desc in cur.description], result))
            
            self.form_builder.set_values(data)
            self.change_tracker = ChangeTracker(data)
            self.current_record_id = emp_id
    
    def _on_save(self):
        """Сохранить изменения"""
        if not self.current_record_id:
            QMessageBox.warning(self, "Ошибка", "Выберите запись")
            return
        
        current_values = self.form_builder.get_values()
        self.change_tracker.update_current_data(current_values)
        
        changed_fields = self.change_tracker.get_changed_fields_dict()
        
        if changed_fields:
            update_builder = UpdateBuilder(self.schema, 'employees')
            update_builder.execute_update(
                changed_fields, 
                {'id': self.current_record_id}
            )
            self.change_tracker.commit()
            QMessageBox.information(self, "Успех", "Данные сохранены")
        else:
            QMessageBox.information(self, "Информация", "Нет изменений")
    
    def _on_delete(self):
        """Удалить запись"""
        if not self.current_record_id:
            return
        
        reply = QMessageBox.question(
            self, "Подтверждение", 
            "Вы уверены?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.db.execute(f"DELETE FROM employees WHERE id = {self.current_record_id}")
            QMessageBox.information(self, "Успех", "Запись удалена")
            self._on_new()
    
    def _on_new(self):
        """Новая запись"""
        self.current_record_id = None
        self.form_builder.set_values({
            field_name: None 
            for field_name in self.schema.fields.keys()
        })
        self.search_input.clear()
        self.results_list.clear()
    
    def _on_cancel(self):
        """Отмена"""
        self._on_new()
```

---

## Резюме: Ключевые концепции

| Компонент | Назначение | Ключевые методы |
|-----------|-----------|-----------------|
| **DatabaseManager** | Работа с БД | `get_table_schema()`, `get_referenced_data()` |
| **TableSchema** | Метаданные таблицы | `add_field()`, `get_fields_by_type()` |
| **FieldDefinition** | Описание поля | Хранит тип, связи, валидацию |
| **AutoFormBuilder** | Генерация формы | `build_form()`, `build_custom_form()` |
| **ChangeTracker** | Отслеживание изменений | `get_changed_fields()`, `has_changes()` |
| **UpdateBuilder** | Генерация SQL | `build_update_sql()`, `execute_update()` |
| **ForeignKeyManager** | Управление FK данными | `load_reference_data()`, кеширование |

---

## Типичные задачи

### Создание формы для таблицы
```python
schema = build_schema_from_database('employees')
form_builder = AutoFormBuilder(schema)
form = form_builder.build_form()
```

### Получение только изменённых полей
```python
tracker = ChangeTracker(original_data)
tracker.update_current_data(form_values)
changed = tracker.get_changed_fields_dict()  # Только изменённые
```

### Обновление только изменённых полей
```python
update_builder = UpdateBuilder(schema, 'employees')
update_builder.execute_update(changed_fields, {'id': 1})
```

### Работа с иностранными ключами
```python
fk_mgr = ForeignKeyManager()
data = fk_mgr.load_reference_data('departments', 'id', 'name')
# Используется кеширование автоматически
```