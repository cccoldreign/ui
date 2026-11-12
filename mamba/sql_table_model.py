import json
from collections import OrderedDict

from PyQt5.QtCore import (QAbstractTableModel, QModelIndex, QObject, QRunnable,
                          QThreadPool, Qt, pyqtSignal)

from sql_query import SqlQuery


def load_config(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------- фоновая загрузка ----------

class _Signals(QObject):
    done = pyqtSignal(int, int, object, object)   # gen, page, names, rows
    failed = pyqtSignal(int, int, str)            # gen, page, message


class _Task(QRunnable):
    def __init__(self, db, sql, params, size, gen, page, signals):
        super().__init__()
        self.db, self.sql, self.params, self.size = db, sql, params, size
        self.gen, self.page, self.signals = gen, page, signals

    def run(self):
        try:
            names, rows = self.db.fetch_page(self.sql, self.params, self.size)
            self.signals.done.emit(self.gen, self.page, names, rows)
        except Exception as e:
            self.signals.failed.emit(self.gen, self.page, str(e))


# ---------- модель ----------

class SqlTableModel(QAbstractTableModel):
    error = pyqtSignal(str)

    def __init__(self, db, page_size=200, max_pages=5, parent=None):
        super().__init__(parent)
        self._db = db
        self._size = page_size
        self._max_pages = max(3, max_pages)   # минимум 3 страницы, чтобы не было "дребезга"
        self._query = None
        self._gen = 0
        self._reset_state()

        self._signals = _Signals()
        self._signals.done.connect(self._on_done)
        self._signals.failed.connect(self._on_failed)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)       # запросы идут строго по очереди

    def _reset_state(self, keep_cols=False):
        if not keep_cols:
            self._cols = []
        self._cache = OrderedDict()   # номер страницы -> список строк (LRU)
        self._pending = set()
        self._known = 0               # сколько строк известно на данный момент
        self._finished = False        # достигнут конец данных

    # --- управление ---

    @property
    def query(self):
        return self._query

    def open(self, cfg):
        self._query = SqlQuery(cfg)
        self._reload(keep_cols=False)

    def _reload(self, keep_cols=True):
        if self._query is None:
            return
        self.beginResetModel()
        self._gen += 1
        self._reset_state(keep_cols)
        self.endResetModel()
        self._request(0)

    def refresh(self):
        self._reload()

    def set_page_size(self, size):
        self._size = max(1, int(size))
        self._reload()

    def set_max_pages(self, n):
        self._max_pages = max(3, int(n))

    # --- фильтры и сортировка: меняют структуру запроса и перезапускают его ---

    def add_filter(self, column, op, value=None):
        self._query.add_filter(column, op, value)
        self._reload()

    def add_where(self, sql, params=()):
        self._query.add_where(sql, params)
        self._reload()

    def set_sort(self, column, direction="ASC"):
        self._query.set_sort(column, direction)
        self._reload()

    def clear_filters(self):
        self._query.reset()
        self._reload()

    def column_name(self, i):
        return self._cols[i]

    def column_type(self, i):
        types = self._query.types if self._query else []
        return types[i] if i < len(types) else "string"

    # --- загрузка страниц ---

    def _request(self, page):
        if self._query is None or page < 0 or page in self._cache or page in self._pending:
            return
        self._pending.add(page)
        try:
            sql, params = self._query.page_sql(page * self._size, self._size)
        except Exception as e:
            self._pending.discard(page)
            self.error.emit(str(e))
            return
        self._pool.start(_Task(self._db, sql, params, self._size, self._gen, page, self._signals))

    def _on_failed(self, gen, page, msg):
        if gen == self._gen:
            self._pending.discard(page)
            self.error.emit(msg)

    def _on_done(self, gen, page, names, rows):
        if gen != self._gen:
            return                                  # устаревший результат
        self._pending.discard(page)
        size = self._size
        first = not self._cols

        count = page * size + len(rows)
        if len(rows) < size:
            self._finished = True
            new_known = count
        else:
            new_known = max(self._known, count)

        if first:
            self.beginResetModel()
            self._cols = list(names)
        self._query.columns = list(self._cols)
        if rows:
            self._cache[page] = rows
            self._cache.move_to_end(page)
            while len(self._cache) > self._max_pages:
                self._cache.popitem(last=False)     # выбрасываем самую старую страницу

        if first:
            self._known = new_known
            self.endResetModel()
            return

        if new_known > self._known:
            self.beginInsertRows(QModelIndex(), self._known, new_known - 1)
            self._known = new_known
            self.endInsertRows()
        elif new_known < self._known:
            self.beginRemoveRows(QModelIndex(), new_known, self._known - 1)
            self._known = new_known
            self.endRemoveRows()

        top = page * size
        bottom = min(top + len(rows) - 1, self._known - 1)
        if bottom >= top and self._cols:
            self.dataChanged.emit(self.index(top, 0), self.index(bottom, len(self._cols) - 1))

    # --- интерфейс QAbstractTableModel ---

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else self._known

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._cols)

    def data(self, index, role=Qt.DisplayRole):
        if role != Qt.DisplayRole or not index.isValid():
            return None
        row = index.row()
        page = row // self._size
        rows = self._cache.get(page)
        if rows is None:
            self._request(page)                     # страницы нет в кэше - грузим
            return "…"
        self._cache.move_to_end(page)
        if not self._finished and row >= self._known - 1:
            self._request(page + 1)                 # дошли до конца - грузим следующую
        i = row - page * self._size
        if i >= len(rows):
            return None
        value = rows[i][index.column()]
        return "" if value is None else str(value)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self._cols[section] if section < len(self._cols) else None
        return section + 1
