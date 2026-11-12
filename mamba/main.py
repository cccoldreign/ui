import sys

from PyQt5.QtWidgets import QApplication

from database_manager import DatabaseManager
from sql_table_view import SqlTableView

app = QApplication(sys.argv)

db = DatabaseManager.instance()
table = SqlTableView(db=db, config_path="sql_tables.json", query_name="employees")
table.error.connect(lambda msg: print("SQL error:", msg))
table.resize(800, 500)
table.show()

# Правый клик по заголовку колонки - сортировка и фильтры.
# То же из кода (add_filter/set_sort - после первой загрузки данных):
#   table.add_where("department = ?", ("IT",))   # допишет условие в where и перезапустит
#   table.add_filter("salary", "gt", 50000)
#   table.set_sort("name", "DESC")
#   table.clear_filters()

sys.exit(app.exec_())
