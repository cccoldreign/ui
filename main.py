import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLineEdit, QTableWidget,
                             QTableWidgetItem, QLabel, QSplitter, QDialog, QHeaderView)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon


# ==================== СТИЛИ ====================
class Styles:
    """Централизованное хранилище всех стилей приложения"""
    
    # Основные цвета
    DARK_BG = "#1e1e1e"
    SIDEBAR_BG = "#252526"
    CONTENT_BG = "#1e1e1e"
    BUTTON_BG = "#0e639c"
    BUTTON_HOVER = "#1177bb"
    BUTTON_ACTIVE = "#007acc"
    INPUT_BG = "#3c3c3c"
    TEXT_COLOR = "#cccccc"
    BORDER_COLOR = "#3c3c3c"
    TABLE_HEADER_BG = "#2d2d30"
    TABLE_ROW_HOVER = "#2a2d2e"
    
    MAIN_WINDOW = f"""
        QMainWindow {{
            background-color: {DARK_BG};
        }}
    """
    
    SIDEBAR_BUTTON = f"""
        QPushButton {{
            background-color: {SIDEBAR_BG};
            color: {TEXT_COLOR};
            border: none;
            padding: 15px;
            text-align: left;
            font-size: 14px;
        }}
        QPushButton:hover {{
            background-color: {INPUT_BG};
        }}
        QPushButton:checked {{
            background-color: {BUTTON_ACTIVE};
            border-left: 3px solid #007acc;
        }}
    """
    
    INPUT_FIELD = f"""
        QLineEdit {{
            background-color: {INPUT_BG};
            color: {TEXT_COLOR};
            border: 1px solid {BORDER_COLOR};
            padding: 8px;
            border-radius: 3px;
            font-size: 13px;
        }}
        QLineEdit:focus {{
            border: 1px solid {BUTTON_ACTIVE};
        }}
    """
    
    ACTION_BUTTON = f"""
        QPushButton {{
            background-color: {BUTTON_BG};
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 3px;
            font-size: 13px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {BUTTON_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {BUTTON_ACTIVE};
        }}
    """
    
    TABLE_WIDGET = f"""
        QTableWidget {{
            background-color: {CONTENT_BG};
            color: {TEXT_COLOR};
            gridline-color: {BORDER_COLOR};
            border: 1px solid {BORDER_COLOR};
            font-size: 13px;
        }}
        QTableWidget::item {{
            padding: 5px;
        }}
        QTableWidget::item:hover {{
            background-color: {TABLE_ROW_HOVER};
        }}
        QTableWidget::item:selected {{
            background-color: {BUTTON_ACTIVE};
        }}
        QHeaderView::section {{
            background-color: {TABLE_HEADER_BG};
            color: {TEXT_COLOR};
            padding: 8px;
            border: 1px solid {BORDER_COLOR};
            font-weight: bold;
        }}
    """
    
    LABEL = f"""
        QLabel {{
            color: {TEXT_COLOR};
            font-size: 13px;
            padding: 5px;
        }}
    """


# ==================== ВИДЖЕТЫ ====================

class CustomTable(QTableWidget):
    """Кастомная таблица с возможностью установки данных"""
    
    cellClickedSignal = pyqtSignal(int, int)
    
    def __init__(self, rows=5, cols=5, parent=None):
        super().__init__(rows, cols, parent)
        self.setStyleSheet(Styles.TABLE_WIDGET)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cellClicked.connect(self.cellClickedSignal.emit)
        self.fill_sample_data()
    
    def fill_sample_data(self):
        """Заполнение примерными данными"""
        for i in range(self.rowCount()):
            for j in range(self.columnCount()):
                item = QTableWidgetItem(f"Ячейка {i+1}-{j+1}")
                self.setItem(i, j, item)
    
    def set_custom_data(self, data):
        """Установка пользовательских данных"""
        if not data:
            return
        self.setRowCount(len(data))
        self.setColumnCount(len(data[0]) if data else 0)
        for i, row in enumerate(data):
            for j, value in enumerate(row):
                self.setItem(i, j, QTableWidgetItem(str(value)))
    
    def get_table_data(self):
        """Получение данных из таблицы"""
        data = []
        for i in range(self.rowCount()):
            row = []
            for j in range(self.columnCount()):
                item = self.item(i, j)
                row.append(item.text() if item else "")
            data.append(row)
        return data


class FormInputWidget(QWidget):
    """Виджет с формой ввода"""
    
    def __init__(self, label_text, parent=None):
        super().__init__(parent)
        self.setup_ui(label_text)
    
    def setup_ui(self, label_text):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 10)
        
        label = QLabel(label_text)
        label.setStyleSheet(Styles.LABEL)
        
        self.input_field = QLineEdit()
        self.input_field.setStyleSheet(Styles.INPUT_FIELD)
        self.input_field.setPlaceholderText(f"Введите {label_text.lower()}")
        
        layout.addWidget(label)
        layout.addWidget(self.input_field)
        self.setLayout(layout)
    
    def get_value(self):
        return self.input_field.text()
    
    def set_value(self, value):
        self.input_field.setText(value)


class Page1Widget(QWidget):
    """Первая страница: 2 формы ввода + таблица"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Заголовок
        title = QLabel("Страница 1: Формы и Таблица")
        title.setStyleSheet(Styles.LABEL + "font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # Формы ввода
        self.form1 = FormInputWidget("Поле 1")
        self.form2 = FormInputWidget("Поле 2")
        
        layout.addWidget(self.form1)
        layout.addWidget(self.form2)
        
        # Таблица
        self.table = CustomTable(5, 4)
        layout.addWidget(self.table)
        
        self.setLayout(layout)


class DetailTableDialog(QDialog):
    """Диалоговое окно с детальной таблицей"""
    
    def __init__(self, row, col, parent=None):
        super().__init__(parent)
        self.row = row
        self.col = col
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle(f"Детальная таблица для ячейки ({self.row}, {self.col})")
        self.setMinimumSize(600, 400)
        self.setStyleSheet(f"QDialog {{ background-color: {Styles.CONTENT_BG}; }}")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок
        title = QLabel(f"Детали для ячейки [{self.row}, {self.col}]")
        title.setStyleSheet(Styles.LABEL + "font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Таблица
        self.detail_table = CustomTable(4, 3)
        layout.addWidget(self.detail_table)
        
        # Кнопка копирования
        self.copy_button = QPushButton("Копировать данные таблицы")
        self.copy_button.setStyleSheet(Styles.ACTION_BUTTON)
        self.copy_button.clicked.connect(self.copy_table_data)
        layout.addWidget(self.copy_button)
        
        self.setLayout(layout)
        
        self.copied_data = None
    
    def copy_table_data(self):
        """Копирование данных таблицы"""
        self.copied_data = self.detail_table.get_table_data()
        self.accept()
    
    def get_copied_data(self):
        return self.copied_data


class Page2Widget(QWidget):
    """Вторая страница: 3 формы ввода + 2 кнопки + таблица с открытием деталей"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Заголовок
        title = QLabel("Страница 2: Формы, Кнопки и Интерактивная Таблица")
        title.setStyleSheet(Styles.LABEL + "font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # Формы ввода
        self.form1 = FormInputWidget("Параметр 1")
        self.form2 = FormInputWidget("Параметр 2")
        self.form3 = FormInputWidget("Параметр 3")
        
        layout.addWidget(self.form1)
        layout.addWidget(self.form2)
        layout.addWidget(self.form3)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        
        self.button1 = QPushButton("Действие 1")
        self.button1.setStyleSheet(Styles.ACTION_BUTTON)
        self.button1.clicked.connect(self.action1)
        
        self.button2 = QPushButton("Действие 2")
        self.button2.setStyleSheet(Styles.ACTION_BUTTON)
        self.button2.clicked.connect(self.action2)
        
        buttons_layout.addWidget(self.button1)
        buttons_layout.addWidget(self.button2)
        buttons_layout.addStretch()
        
        layout.addLayout(buttons_layout)
        
        # Таблица с обработчиком клика
        self.table = CustomTable(6, 5)
        self.table.cellClickedSignal.connect(self.handle_cell_click)
        layout.addWidget(self.table)
        
        self.setLayout(layout)
    
    def action1(self):
        """Обработчик первой кнопки"""
        v1 = self.form1.get_value()
        v2 = self.form2.get_value()
        v3 = self.form3.get_value()
        print(f"Действие 1: {v1}, {v2}, {v3}")
    
    def action2(self):
        """Обработчик второй кнопки"""
        print("Действие 2 выполнено")
    
    def handle_cell_click(self, row, col):
        """Обработчик клика по ячейке (открывает детальную таблицу для ячейки [2,2])"""
        if row == 1 and col == 1:  # Индексация с 0, поэтому [1,1] = вторая строка, второй столбец
            dialog = DetailTableDialog(row + 1, col + 1, self)
            if dialog.exec_() == QDialog.Accepted:
                copied_data = dialog.get_copied_data()
                if copied_data:
                    # Можно вставить данные в текущую таблицу или в другую
                    self.table.set_custom_data(copied_data)
                    print("Данные скопированы и вставлены в текущую таблицу")


# ==================== ГЛАВНОЕ ОКНО ====================

class MainWindow(QMainWindow):
    """Главное окно приложения в стиле VS Code"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("VS Code Style Application")
        self.setGeometry(100, 100, 1200, 700)
        self.setStyleSheet(Styles.MAIN_WINDOW)
        
        # Центральный виджет
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Боковая панель (sidebar)
        sidebar = self.create_sidebar()
        
        # Область контента
        self.content_area = QWidget()
        self.content_area.setStyleSheet(f"background-color: {Styles.CONTENT_BG};")
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_area.setLayout(self.content_layout)
        
        # Создание страниц
        self.page1 = Page1Widget()
        self.page2 = Page2Widget()
        
        # Добавление первой страницы по умолчанию
        self.content_layout.addWidget(self.page1)
        self.page2.hide()
        self.content_layout.addWidget(self.page2)
        
        # Добавление в главный layout
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.content_area, stretch=1)
        
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
    
    def create_sidebar(self):
        """Создание боковой панели с кнопками"""
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet(f"background-color: {Styles.SIDEBAR_BG};")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Кнопки навигации
        self.btn_page1 = QPushButton("📄 Страница 1")
        self.btn_page1.setCheckable(True)
        self.btn_page1.setChecked(True)
        self.btn_page1.setStyleSheet(Styles.SIDEBAR_BUTTON)
        self.btn_page1.clicked.connect(lambda: self.switch_page(0))
        
        self.btn_page2 = QPushButton("📊 Страница 2")
        self.btn_page2.setCheckable(True)
        self.btn_page2.setStyleSheet(Styles.SIDEBAR_BUTTON)
        self.btn_page2.clicked.connect(lambda: self.switch_page(1))
        
        layout.addWidget(self.btn_page1)
        layout.addWidget(self.btn_page2)
        layout.addStretch()
        
        sidebar.setLayout(layout)
        return sidebar
    
    def switch_page(self, page_index):
        """Переключение между страницами"""
        if page_index == 0:
            self.page1.show()
            self.page2.hide()
            self.btn_page1.setChecked(True)
            self.btn_page2.setChecked(False)
        elif page_index == 1:
            self.page1.hide()
            self.page2.show()
            self.btn_page1.setChecked(False)
            self.btn_page2.setChecked(True)


# ==================== ЗАПУСК ====================

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()