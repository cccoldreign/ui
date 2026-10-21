import json
import sqlite3
import sys
from collections import OrderedDict
from contextlib import closing
from pathlib import Path

from PyQt5.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QRunnable,
    QThreadPool,
    Qt,
    pyqtSignal,
)
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QTableView,
    QVBoxLayout,
    QWidget,
)


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "struct.json"
DATABASE_PATH = BASE_DIR / "demo.sqlite3"
PAGE_SIZE = 200
CACHE_PAGES = 3
DEMO_ROWS = 250_000


class SqlTableConfig:
    """Простая конфигурация: SELECT/FROM — доверенные SQL-фрагменты."""

    def __init__(self, select, from_clause, where="", order_by=""):
        if not isinstance(select, str) or not select.strip():
            raise ValueError('"SELECT" в конфигурации должен быть непустой строкой')
        if not isinstance(from_clause, str) or not from_clause.strip():
            raise ValueError('"FROM" в конфигурации должен быть непустой строкой')
        for name, value in (("WHERE", where), ("ORDER BY", order_by)):
            if not isinstance(value, str):
                raise ValueError(f'"{name}" в конфигурации должен быть строкой')

        self.select = select.strip().rstrip(";")
        self.from_clause = from_clause.strip().rstrip(";")
        self.where = where.strip().removeprefix("WHERE").strip().rstrip(";")
        self.order_by = order_by.strip().removeprefix("ORDER BY").strip().rstrip(";")

    @classmethod
    def from_json(cls, path):
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise ValueError("Корень struct.json должен быть JSON-объектом")
        return cls(
            select=data.get("SELECT"),
            from_clause=data.get("FROM"),
            where=data.get("WHERE", ""),
            order_by=data.get("ORDER BY", ""),
        )

    def select_sql(self):
        sql = f"SELECT {self.select} FROM {self.from_clause}"
        if self.where:
            sql += f" WHERE {self.where}"
        if self.order_by:
            sql += f" ORDER BY {self.order_by}"
        return sql

    def count_sql(self):
        sql = f"SELECT COUNT(*) FROM {self.from_clause}"
        if self.where:
            sql += f" WHERE {self.where}"
        return sql


class SQLiteAdapter:
    """Драйверный слой. Для другой БД замените этот адаптер."""

    def connect(self, connection_string):
        return sqlite3.connect(connection_string, timeout=30)

    def fetch_page(self, connection, select_sql, limit, offset):
        sql = select_sql.rstrip().rstrip(";") + " LIMIT ? OFFSET ?"
        cursor = connection.cursor()
        try:
            cursor.execute(sql, (limit, offset))
            headers = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            return headers, [tuple("" if value is None else value for value in row) for row in rows]
        finally:
            cursor.close()

    def fetch_count(self, connection, count_sql):
        cursor = connection.cursor()
        try:
            cursor.execute(count_sql)
            return cursor.fetchone()[0]
        finally:
            cursor.close()


class DatabaseManager:
    """Открывает отдельное соединение на каждый запрос, в том числе из фонового потока."""

    def __init__(self, connection_string, adapter=None):
        self.connection_string = str(connection_string)
        self.adapter = adapter or SQLiteAdapter()

    def fetch_page(self, config, page_size, offset):
        with closing(self.adapter.connect(self.connection_string)) as connection:
            return self.adapter.fetch_page(
                connection, config.select_sql(), page_size, offset
            )

    def fetch_count(self, config):
        with closing(self.adapter.connect(self.connection_string)) as connection:
            return self.adapter.fetch_count(connection, config.count_sql())


class _WorkerSignals(QObject):
    succeeded = pyqtSignal(int, int, object, object)
    failed = pyqtSignal(int, int, str)


class _LoadPageTask(QRunnable):
    def __init__(self, manager, config, generation, page, page_size, initial=False):
        super().__init__()
        self.manager = manager
        self.config = config
        self.generation = generation
        self.page = page
        self.page_size = page_size
        self.initial = initial
        self.signals = _WorkerSignals()

    def run(self):
        try:
            total = self.manager.fetch_count(self.config) if self.initial else None
            headers, rows = self.manager.fetch_page(
                self.config, self.page_size, self.page * self.page_size
            )
            self.signals.succeeded.emit(
                self.generation, self.page, (headers, rows), total
            )
        except Exception as error:
            self.signals.failed.emit(self.generation, self.page, str(error))


class SqlTableModel(QAbstractTableModel):
    """Виртуальная таблица: число строк известно, данные подгружаются страницами."""

    error_occurred = pyqtSignal(str)
    loading_finished = pyqtSignal()

    def __init__(self, manager, config, page_size=PAGE_SIZE, cache_pages=CACHE_PAGES):
        super().__init__()
        if page_size < 1 or cache_pages < 1:
            raise ValueError("page_size и cache_pages должны быть больше нуля")
        self.manager = manager
        self.config = config
        self.page_size = page_size
        self.cache_pages = cache_pages
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(2)
        self.generation = 0
        self.total_rows = 0
        self.headers = []
        self.pages = OrderedDict()
        self.pending = set()
        self.load_initial()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else self.total_rows

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.headers)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal and 0 <= section < len(self.headers):
            return self.headers[section]
        if orientation == Qt.Vertical and 0 <= section < self.total_rows:
            return section + 1
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        page_number, row_in_page = divmod(index.row(), self.page_size)
        rows = self.pages.get(page_number)
        if rows is None:
            self.request_page(page_number)
            if row_in_page >= self.page_size - 30:
                self.request_page(page_number + 1)
            return ""
        self.pages.move_to_end(page_number)
        if row_in_page >= len(rows) or index.column() >= len(rows[row_in_page]):
            return ""
        value = rows[row_in_page][index.column()]
        return "" if value is None else value

    def load_initial(self):
        self.generation += 1
        generation = self.generation
        self.pages.clear()
        self.pending.clear()
        self.beginResetModel()
        self.total_rows = 0
        self.headers = []
        self.endResetModel()
        self._start_task(0, generation, initial=True)

    def refresh(self):
        self.load_initial()

    def request_page(self, page_number):
        if page_number < 0 or page_number * self.page_size >= self.total_rows:
            return
        key = (self.generation, page_number)
        if page_number in self.pages or key in self.pending:
            return
        self._start_task(page_number, self.generation)

    def _start_task(self, page_number, generation, initial=False):
        key = (generation, page_number)
        if key in self.pending:
            return
        self.pending.add(key)
        task = _LoadPageTask(
            self.manager,
            self.config,
            generation,
            page_number,
            self.page_size,
            initial,
        )
        task.signals.succeeded.connect(self._on_page_loaded)
        task.signals.failed.connect(self._on_load_failed)
        self.pool.start(task)

    def _on_page_loaded(self, generation, page_number, result, total):
        self.pending.discard((generation, page_number))
        if generation != self.generation:
            return
        headers, rows = result
        if total is not None:
            self.beginResetModel()
            self.total_rows = total
            self.headers = headers
            self.pages.clear()
            self._cache_page(page_number, rows)
            self.endResetModel()
        else:
            self._cache_page(page_number, rows)
            if rows and self.columnCount():
                first_row = page_number * self.page_size
                last_row = min(self.total_rows - 1, first_row + len(rows) - 1)
                if first_row <= last_row:
                    self.dataChanged.emit(
                        self.index(first_row, 0),
                        self.index(last_row, self.columnCount() - 1),
                        [Qt.DisplayRole, Qt.EditRole],
                    )
        self.loading_finished.emit()

    def _on_load_failed(self, generation, page_number, message):
        self.pending.discard((generation, page_number))
        if generation == self.generation:
            self.error_occurred.emit(message)

    def _cache_page(self, page_number, rows):
        self.pages[page_number] = rows
        self.pages.move_to_end(page_number)
        while len(self.pages) > self.cache_pages:
            self.pages.popitem(last=False)

    def goto_row(self, row):
        if not 0 <= row < self.total_rows:
            raise IndexError(f"Строка должна быть в диапазоне 0..{self.total_rows - 1}")
        self.request_page(row // self.page_size)


class SqlTableView(QWidget):
    """Готовый виджет: table = SqlTableView(connection, config)."""

    row_selected = pyqtSignal(int)
    error_occurred = pyqtSignal(str)
    loading_finished = pyqtSignal()

    def __init__(self, connection, config, adapter=None):
        super().__init__()
        self.manager = DatabaseManager(connection, adapter=adapter)
        self.config = (
            SqlTableConfig.from_json(config)
            if isinstance(config, (str, Path))
            else SqlTableConfig.from_dict(config)
            if isinstance(config, dict)
            else config
        )
        if not isinstance(self.config, SqlTableConfig):
            raise TypeError("config должен быть путём к JSON или SqlTableConfig")

        self.table = QTableView(self)
        self.model = SqlTableModel(self.manager, self.config)
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSortingEnabled(False)
        self.table.verticalHeader().setDefaultSectionSize(24)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.status = QLabel("Загрузка…", self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addWidget(self.status)

        self.table.selectionModel().currentRowChanged.connect(self._on_row_selected)
        self.model.error_occurred.connect(self._on_error)
        self.model.loading_finished.connect(self.loading_finished)
        self.model.loading_finished.connect(self._update_status)

    def _on_row_selected(self, current, _previous):
        if current.isValid():
            self.row_selected.emit(current.row())

    def _on_error(self, message):
        self.status.setText(f"Ошибка загрузки: {message}")
        self.error_occurred.emit(message)

    def _update_status(self):
        self.status.setText(
            f"Всего строк: {self.model.total_rows:,} | "
            f"В кэше: {len(self.model.pages)} страниц"
        )

    def refresh(self):
        self.status.setText("Загрузка…")
        self.model.refresh()

    def goto_row(self, row):
        self.model.goto_row(row)
        if self.model.columnCount():
            self.table.scrollTo(
                self.model.index(row, 0), QTableView.PositionAtTop
            )


def ensure_demo_database(path=DATABASE_PATH, row_count=DEMO_ROWS):
    """Создаёт демонстрационную таблицу порциями, не удерживая её в памяти."""
    with closing(sqlite3.connect(path)) as connection:
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS demo_records (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    amount REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    note TEXT
                )
                """
            )
            cursor.execute("SELECT COUNT(*) FROM demo_records")
            count = cursor.fetchone()[0]
        if count == 0:
            insert_sql = """
                INSERT INTO demo_records (id, name, category, amount, created_at, note)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            categories = ("Книги", "Одежда", "Техника", "Дом")
            batch_size = 5_000
            with closing(connection.cursor()) as cursor:
                for start in range(1, row_count + 1, batch_size):
                    stop = min(start + batch_size, row_count + 1)
                    rows = (
                        (
                            row_id,
                            f"Запись {row_id:06d}",
                            categories[row_id % len(categories)],
                            round((row_id * 13 % 100_000) / 100, 2),
                            f"2026-{(row_id % 12) + 1:02d}-{(row_id % 28) + 1:02d}",
                            None if row_id % 17 == 0 else f"Примечание {row_id}",
                        )
                        for row_id in range(start, stop)
                    )
                    cursor.executemany(insert_sql, rows)
                    connection.commit()


def main():
    ensure_demo_database()
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("SQL Table Viewer")
    window.resize(1000, 650)
    table = SqlTableView(DATABASE_PATH, CONFIG_PATH)
    window.setCentralWidget(table)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()