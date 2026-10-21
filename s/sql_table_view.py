from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QTableView

from sql_table_model import SqlTableModel, load_config


class SqlTableView(QTableView):
    error = pyqtSignal(str)

    def __init__(self, db, config_path, query_name=None,
                 page_size=200, max_pages=5, parent=None):
        super().__init__(parent)
        self._config_path = config_path
        self._model = SqlTableModel(db, page_size, max_pages, self)
        self._model.error.connect(self.error)
        self.setModel(self._model)
        if query_name:
            self.open_query(query_name)

    def queries(self):
        """Список имён запросов из JSON."""
        return list(load_config(self._config_path))

    def open_query(self, name):
        # JSON читается заново - новые запросы подхватываются без перезапуска
        self._model.open(load_config(self._config_path)[name])

    def refresh(self):
        self._model.refresh()

    def set_page_size(self, size):
        self._model.set_page_size(size)

    def set_max_pages(self, n):
        self._model.set_max_pages(n)
