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

sys.exit(app.exec_())
