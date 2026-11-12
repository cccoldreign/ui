import csv
from datetime import datetime

from PyQt5.QtCore import QObject, QRunnable, QThreadPool, Qt, pyqtSignal
from PyQt5.QtWidgets import QInputDialog, QMenu, QTableView

from sql_query import FILTER_MENU
from sql_table_model import SqlTableModel, load_config


class _ExportSignals(QObject):
    progress = pyqtSignal(int)        # сколько строк записано
    finished = pyqtSignal(int, str)   # всего строк, текст ошибки ("" если успешно)


class _ExportTask(QRunnable):
    def __init__(self, db, sql, params, path, signals):
        super().__init__()
        self.db, self.sql, self.params, self.path, self.signals = db, sql, params, path, signals

    def run(self):
        n = 0
        try:
            # utf-8-sig и ";" - чтобы файл корректно открывался в Excel
            with open(self.path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                chunks = self.db.stream(self.sql, self.params)
                writer.writerow(next(chunks))          # заголовки
                for rows in chunks:                    # порции по fetchmany
                    writer.writerows(rows)
                    n += len(rows)
                    self.signals.progress.emit(n)
            self.signals.finished.emit(n, "")
        except Exception as e:
            self.signals.finished.emit(n, str(e))


def _parse_value(text, ctype):
    text = text.strip()
    if ctype == "number":
        try:
            return int(text)
        except ValueError:
            return float(text.replace(",", "."))
    if ctype == "date":
        for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                pass
        raise ValueError(text)
    return text


class SqlTableView(QTableView):
    error = pyqtSignal(str)
    export_progress = pyqtSignal(int)
    export_finished = pyqtSignal(int, str)

    def __init__(self, db, config_path, query_name=None,
                 page_size=200, max_pages=5, parent=None):
        super().__init__(parent)
        self._db = db
        self._config_path = config_path
        self._model = SqlTableModel(db, page_size, max_pages, self)
        self._model.error.connect(self.error)
        self.setModel(self._model)

        header = self.horizontalHeader()
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self._header_menu)

        if query_name:
            self.open_query(query_name)

    # --- запросы ---

    def queries(self):
        """Список имён запросов из JSON."""
        return list(load_config(self._config_path))

    def open_query(self, name):
        # JSON читается заново - новые запросы подхватываются без перезапуска
        self.horizontalHeader().setSortIndicatorShown(False)
        self._model.open(load_config(self._config_path)[name])

    def refresh(self):
        self._model.refresh()

    def set_page_size(self, size):
        self._model.set_page_size(size)

    def set_max_pages(self, n):
        self._model.set_max_pages(n)

    # --- фильтры и сортировка (после первой загрузки данных) ---

    def add_filter(self, column, op, value=None):
        """op: contains, starts, eq, ne, gt, ge, lt, le, null, notnull."""
        self._model.add_filter(column, op, value)

    def add_where(self, sql, params=()):
        """Дописать своё условие в where: add_where("salary > ?", (50000,))."""
        self._model.add_where(sql, params)

    def set_sort(self, column, direction="ASC"):
        self._model.set_sort(column, direction)
        header = self.horizontalHeader()
        header.setSortIndicator(self._model._cols.index(column),
                                Qt.AscendingOrder if direction.upper() == "ASC" else Qt.DescendingOrder)
        header.setSortIndicatorShown(True)

    def clear_filters(self):
        """Сбросить фильтры, добавленные условия и сортировку к значениям из JSON."""
        self.horizontalHeader().setSortIndicatorShown(False)
        self._model.clear_filters()

    # --- меню по правому клику на заголовок ---

    def _header_menu(self, pos):
        header = self.horizontalHeader()
        col = header.logicalIndexAt(pos)
        if col < 0:
            return
        name = self._model.column_name(col)
        ctype = self._model.column_type(col)

        menu = QMenu(self)
        menu.addAction("Сортировать по возрастанию").triggered.connect(
            lambda checked=False: self._safe(self.set_sort, name, "ASC"))
        menu.addAction("Сортировать по убыванию").triggered.connect(
            lambda checked=False: self._safe(self.set_sort, name, "DESC"))
        menu.addSeparator()
        filters = menu.addMenu("Фильтр")
        for code, label in FILTER_MENU.get(ctype, FILTER_MENU["string"]):
            filters.addAction(label).triggered.connect(
                lambda checked=False, c=code: self._ask_filter(name, ctype, c))
        menu.addSeparator()
        menu.addAction("Сбросить фильтры и сортировку").triggered.connect(
            lambda checked=False: self.clear_filters())
        menu.exec_(header.mapToGlobal(pos))

    def _ask_filter(self, name, ctype, code):
        if code in ("null", "notnull"):
            self._safe(self.add_filter, name, code)
            return
        text, ok = QInputDialog.getText(self, name, "Значение:")
        if not ok:
            return
        try:
            value = _parse_value(text, ctype)
        except ValueError:
            self.error.emit(f"Неверное значение: {text}")
            return
        self._safe(self.add_filter, name, code, value)

    def _safe(self, func, *args):
        try:
            func(*args)
        except Exception as e:
            self.error.emit(str(e))

    # --- экспорт ---

    def export_csv(self, path):
        """Выгружает весь результат текущего запроса (с фильтрами и сортировкой) в CSV."""
        query = self._model.query
        if query is None:
            return
        sql, params = query.export_sql()
        signals = _ExportSignals(self)
        signals.progress.connect(self.export_progress)
        signals.finished.connect(self.export_finished)
        QThreadPool.globalInstance().start(_ExportTask(self._db, sql, params, path, signals))
