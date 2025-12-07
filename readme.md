# 📚 Полное руководство по созданию PyQt5 приложений

## 🎯 Оглавление
1. [Базовая структура приложения](#базовая-структура)
2. [Основные виджеты и их методы](#основные-виджеты)
3. [Layouts (Компоновщики)](#layouts)
4. [Events и Signals/Slots](#events-и-signals)
5. [Стилизация (QSS)](#стилизация)
6. [Практические паттерны](#практические-паттерны)

---

## 🏗️ Базовая структура приложения {#базовая-структура}

### Минимальное приложение

```python
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget

# 1. Создаем приложение (обязательно!)
app = QApplication(sys.argv)

# 2. Создаем главное окно
window = QMainWindow()
window.setWindowTitle("Мое приложение")
window.setGeometry(100, 100, 800, 600)  # x, y, width, height

# 3. Показываем окно
window.show()

# 4. Запускаем цикл обработки событий
sys.exit(app.exec_())
```

### Правильная структура с классами

```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()  # ОБЯЗАТЕЛЬНО вызываем конструктор родителя
        self.setup_ui()     # Создаем интерфейс
    
    def setup_ui(self):
        self.setWindowTitle("Мое приложение")
        self.setGeometry(100, 100, 800, 600)
        
        # Центральный виджет (обязательно для QMainWindow)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Дальше добавляем layout и виджеты

# Запуск
app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec_())
```

---

## 🧩 Основные виджеты и их методы {#основные-виджеты}

### 1. QWidget (базовый виджет)

**Основные методы:**

```python
widget = QWidget()

# Размеры и позиция
widget.setGeometry(x, y, width, height)  # Позиция и размер
widget.setFixedSize(width, height)       # Фиксированный размер
widget.setMinimumSize(width, height)     # Минимальный размер
widget.setMaximumSize(width, height)     # Максимальный размер
widget.resize(width, height)             # Изменить размер

# Видимость
widget.show()                            # Показать
widget.hide()                            # Скрыть
widget.setVisible(True/False)            # Установить видимость

# Включение/отключение
widget.setEnabled(True/False)            # Включить/выключить
widget.isEnabled()                       # Проверить состояние

# Стили
widget.setStyleSheet("background-color: red;")  # CSS-подобные стили
```

### 2. QPushButton (кнопка)

```python
from PyQt5.QtWidgets import QPushButton

button = QPushButton("Текст кнопки")

# Основные методы
button.setText("Новый текст")            # Изменить текст
button.text()                            # Получить текст
button.setEnabled(True/False)            # Включить/выключить
button.setCheckable(True)                # Сделать переключаемой
button.setChecked(True)                  # Установить состояние
button.isChecked()                       # Проверить состояние

# СОБЫТИЯ (самое важное!)
button.clicked.connect(self.on_button_click)  # Клик по кнопке
button.pressed.connect(func)             # Нажатие
button.released.connect(func)            # Отпускание

# Пример обработчика
def on_button_click(self):
    print("Кнопка нажата!")
```

### 3. QLineEdit (поле ввода)

```python
from PyQt5.QtWidgets import QLineEdit

input_field = QLineEdit()

# Получение и установка текста
input_field.setText("Начальный текст")   # Установить текст
text = input_field.text()                # Получить текст
input_field.clear()                      # Очистить

# Placeholder
input_field.setPlaceholderText("Введите текст...")

# Настройки
input_field.setReadOnly(True)            # Только чтение
input_field.setMaxLength(50)             # Максимальная длина
input_field.setEchoMode(QLineEdit.Password)  # Режим пароля

# СОБЫТИЯ
input_field.textChanged.connect(self.on_text_changed)      # Текст изменился
input_field.returnPressed.connect(self.on_enter_pressed)   # Нажат Enter
input_field.editingFinished.connect(func)                  # Завершено редактирование

# Пример обработчика
def on_text_changed(self, text):
    print(f"Новый текст: {text}")
```

### 4. QLabel (метка)

```python
from PyQt5.QtWidgets import QLabel

label = QLabel("Текст метки")

# Основные методы
label.setText("Новый текст")
label.text()
label.setWordWrap(True)                  # Перенос слов
label.setAlignment(Qt.AlignCenter)       # Выравнивание

# Можно использовать HTML
label.setText("<h1>Заголовок</h1><p>Текст</p>")
```

### 5. QTableWidget (таблица)

```python
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem

table = QTableWidget(5, 3)  # 5 строк, 3 колонки

# Размеры
table.setRowCount(10)                    # Установить количество строк
table.setColumnCount(5)                  # Установить количество колонок
table.rowCount()                         # Получить количество строк
table.columnCount()                      # Получить количество колонок

# Заголовки
table.setHorizontalHeaderLabels(['Колонка 1', 'Колонка 2', 'Колонка 3'])
table.setVerticalHeaderLabels(['Строка 1', 'Строка 2'])

# Заполнение данными
item = QTableWidgetItem("Значение")
table.setItem(0, 0, item)                # Установить элемент в ячейку

# Получение данных
item = table.item(0, 0)                  # Получить элемент
if item:
    text = item.text()                   # Получить текст

# Выделение
table.setSelectionBehavior(QTableWidget.SelectRows)  # Выделение по строкам
table.setSelectionMode(QTableWidget.SingleSelection) # Режим выделения

# Размеры колонок
from PyQt5.QtWidgets import QHeaderView
table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)  # Растягивать

# СОБЫТИЯ
table.cellClicked.connect(self.on_cell_clicked)        # Клик по ячейке
table.cellDoubleClicked.connect(func)                  # Двойной клик
table.currentCellChanged.connect(func)                 # Изменилась текущая ячейка
table.itemChanged.connect(func)                        # Элемент изменился

# Пример обработчика
def on_cell_clicked(self, row, column):
    print(f"Клик по ячейке [{row}, {column}]")
    item = self.table.item(row, column)
    if item:
        print(f"Содержимое: {item.text()}")
```

### 6. QComboBox (выпадающий список)

```python
from PyQt5.QtWidgets import QComboBox

combo = QComboBox()

# Добавление элементов
combo.addItem("Элемент 1")
combo.addItems(["Элемент 2", "Элемент 3", "Элемент 4"])

# Получение и установка
combo.setCurrentIndex(0)                 # Установить текущий индекс
combo.setCurrentText("Элемент 2")        # Установить по тексту
index = combo.currentIndex()             # Получить индекс
text = combo.currentText()               # Получить текст

# Удаление
combo.removeItem(0)                      # Удалить по индексу
combo.clear()                            # Очистить все

# СОБЫТИЯ
combo.currentIndexChanged.connect(self.on_combo_changed)
combo.currentTextChanged.connect(func)

def on_combo_changed(self, index):
    text = self.combo.currentText()
    print(f"Выбрано: {text}")
```

### 7. QCheckBox и QRadioButton

```python
from PyQt5.QtWidgets import QCheckBox, QRadioButton

# Checkbox
checkbox = QCheckBox("Согласен с условиями")
checkbox.setChecked(True)                # Установить состояние
is_checked = checkbox.isChecked()        # Проверить состояние

checkbox.stateChanged.connect(self.on_checkbox_changed)

def on_checkbox_changed(self, state):
    if state == Qt.Checked:
        print("Отмечено")
    else:
        print("Не отмечено")

# RadioButton
radio1 = QRadioButton("Вариант 1")
radio2 = QRadioButton("Вариант 2")
radio1.setChecked(True)

radio1.toggled.connect(self.on_radio_toggled)

def on_radio_toggled(self, checked):
    if checked:
        print("Выбран вариант 1")
```

---

## 📐 Layouts (Компоновщики) {#layouts}

Layouts управляют расположением виджетов. **Это ключевой момент!**

### 1. QVBoxLayout (вертикальный)

```python
from PyQt5.QtWidgets import QVBoxLayout

layout = QVBoxLayout()

# Добавление виджетов (сверху вниз)
layout.addWidget(widget1)
layout.addWidget(widget2)
layout.addWidget(widget3)

# Добавление растяжки (пустое пространство)
layout.addStretch()

# Добавление другого layout
layout.addLayout(another_layout)

# Настройки отступов и промежутков
layout.setContentsMargins(10, 10, 10, 10)  # left, top, right, bottom
layout.setSpacing(5)                       # Промежуток между виджетами

# Применение к виджету
widget.setLayout(layout)
```

### 2. QHBoxLayout (горизонтальный)

```python
from PyQt5.QtWidgets import QHBoxLayout

layout = QHBoxLayout()

# Добавление виджетов (слева направо)
layout.addWidget(button1)
layout.addWidget(button2)
layout.addWidget(button3)

# Добавление с растяжением
layout.addWidget(widget, stretch=2)  # Этот виджет займет в 2 раза больше места
layout.addStretch()                  # Пустое пространство справа

widget.setLayout(layout)
```

### 3. QGridLayout (сетка)

```python
from PyQt5.QtWidgets import QGridLayout

layout = QGridLayout()

# Добавление виджетов по позициям (row, column)
layout.addWidget(label1, 0, 0)      # Строка 0, Колонка 0
layout.addWidget(input1, 0, 1)      # Строка 0, Колонка 1
layout.addWidget(label2, 1, 0)      # Строка 1, Колонка 0
layout.addWidget(input2, 1, 1)      # Строка 1, Колонка 1

# Виджет на несколько ячеек (row, column, rowSpan, columnSpan)
layout.addWidget(button, 2, 0, 1, 2)  # Занимает 2 колонки

widget.setLayout(layout)
```

### 4. Вложенные Layouts (самое мощное!)

```python
# Главный layout
main_layout = QVBoxLayout()

# Верхняя часть - горизонтальный layout
top_layout = QHBoxLayout()
top_layout.addWidget(QPushButton("Кнопка 1"))
top_layout.addWidget(QPushButton("Кнопка 2"))

# Средняя часть - таблица
table = QTableWidget()

# Нижняя часть - формы в сетке
bottom_layout = QGridLayout()
bottom_layout.addWidget(QLabel("Имя:"), 0, 0)
bottom_layout.addWidget(QLineEdit(), 0, 1)
bottom_layout.addWidget(QLabel("Email:"), 1, 0)
bottom_layout.addWidget(QLineEdit(), 1, 1)

# Собираем все вместе
main_layout.addLayout(top_layout)
main_layout.addWidget(table)
main_layout.addLayout(bottom_layout)

widget.setLayout(main_layout)
```

---

## ⚡ Events и Signals/Slots {#events-и-signals}

**Signals/Slots** - это механизм связи между объектами в Qt.

### Концепция

- **Signal (сигнал)** - событие, которое происходит (например, клик по кнопке)
- **Slot (слот)** - функция, которая вызывается при срабатывании сигнала

### Стандартные сигналы

```python
# Кнопка
button.clicked.connect(self.on_button_click)
button.pressed.connect(func)
button.released.connect(func)

# Поле ввода
input_field.textChanged.connect(self.on_text_changed)
input_field.returnPressed.connect(self.on_enter)
input_field.editingFinished.connect(func)

# Таблица
table.cellClicked.connect(self.on_cell_click)
table.cellDoubleClicked.connect(func)
table.itemChanged.connect(func)

# ComboBox
combo.currentIndexChanged.connect(self.on_combo_changed)
combo.currentTextChanged.connect(func)

# CheckBox
checkbox.stateChanged.connect(self.on_checkbox_changed)

# RadioButton
radio.toggled.connect(self.on_radio_toggled)
```

### Создание собственных сигналов

```python
from PyQt5.QtCore import pyqtSignal

class CustomWidget(QWidget):
    # Объявляем собственный сигнал
    dataChanged = pyqtSignal(str)        # Сигнал с параметром str
    valueUpdated = pyqtSignal(int, int)  # Сигнал с двумя параметрами
    
    def __init__(self):
        super().__init__()
    
    def some_method(self):
        # Генерируем сигнал
        self.dataChanged.emit("Новые данные")
        self.valueUpdated.emit(10, 20)

# Использование
widget = CustomWidget()
widget.dataChanged.connect(self.handle_data_changed)

def handle_data_changed(self, data):
    print(f"Получены данные: {data}")
```

### Передача параметров в слоты

```python
# Метод 1: lambda функция
button.clicked.connect(lambda: self.on_click("параметр"))

def on_click(self, param):
    print(f"Параметр: {param}")

# Метод 2: functools.partial
from functools import partial

button.clicked.connect(partial(self.on_click, "параметр"))

# Метод 3: создание отдельной функции
def create_handler(param):
    def handler():
        self.on_click(param)
    return handler

button.clicked.connect(create_handler("параметр"))
```

### Отключение сигналов

```python
# Отключить конкретный слот
button.clicked.disconnect(self.on_button_click)

# Отключить все слоты
button.clicked.disconnect()

# Временно заблокировать сигналы
button.blockSignals(True)   # Заблокировать
# ... делаем что-то ...
button.blockSignals(False)  # Разблокировать
```

---

## 🎨 Стилизация (QSS - Qt Style Sheets) {#стилизация}

QSS - это CSS-подобный язык для стилизации виджетов.

### Базовый синтаксис

```python
# Применение к одному виджету
button.setStyleSheet("""
    QPushButton {
        background-color: #0e639c;
        color: white;
        border: none;
        padding: 10px;
        border-radius: 5px;
    }
    QPushButton:hover {
        background-color: #1177bb;
    }
    QPushButton:pressed {
        background-color: #007acc;
    }
""")

# Применение ко всему приложению
app.setStyleSheet("...")

# Применение к окну (влияет на все дочерние виджеты)
window.setStyleSheet("...")
```

### Селекторы

```python
"""
/* По типу виджета */
QPushButton { ... }

/* По ID (через setObjectName) */
#myButton { ... }

/* По классу */
.QPushButton { ... }

/* Псевдо-состояния */
QPushButton:hover { ... }
QPushButton:pressed { ... }
QPushButton:checked { ... }
QPushButton:disabled { ... }
QPushButton:focus { ... }

/* Вложенные виджеты */
QMainWindow QPushButton { ... }

/* Части виджетов */
QTableWidget::item { ... }
QTableWidget::item:hover { ... }
QHeaderView::section { ... }
"""
```

### Свойства

```python
"""
/* Цвета */
background-color: #1e1e1e;
color: #cccccc;
border-color: #3c3c3c;

/* Границы */
border: 1px solid #3c3c3c;
border-radius: 5px;
border-top: 2px solid red;

/* Отступы */
padding: 10px;
padding: 10px 20px;  /* vertical horizontal */
padding: 10px 20px 10px 20px;  /* top right bottom left */
margin: 10px;

/* Текст */
font-size: 14px;
font-weight: bold;
font-family: Arial;
text-align: left;

/* Размеры */
min-width: 100px;
max-width: 200px;
min-height: 50px;
"""
```

### Централизованные стили (лучшая практика!)

```python
class Styles:
    # Цвета
    PRIMARY = "#0e639c"
    HOVER = "#1177bb"
    BG_DARK = "#1e1e1e"
    TEXT = "#cccccc"
    
    # Стили
    BUTTON = f"""
        QPushButton {{
            background-color: {PRIMARY};
            color: white;
            padding: 10px;
        }}
        QPushButton:hover {{
            background-color: {HOVER};
        }}
    """
    
    INPUT = f"""
        QLineEdit {{
            background-color: #3c3c3c;
            color: {TEXT};
            border: 1px solid #444;
            padding: 8px;
        }}
    """

# Использование
button.setStyleSheet(Styles.BUTTON)
input_field.setStyleSheet(Styles.INPUT)
```

---

## 💡 Практические паттерны {#практические-паттерны}

### 1. Создание переключаемых страниц

```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        
        # Sidebar с кнопками
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout()
        
        self.btn_page1 = QPushButton("Страница 1")
        self.btn_page2 = QPushButton("Страница 2")
        
        self.btn_page1.clicked.connect(lambda: self.show_page(0))
        self.btn_page2.clicked.connect(lambda: self.show_page(1))
        
        sidebar_layout.addWidget(self.btn_page1)
        sidebar_layout.addWidget(self.btn_page2)
        sidebar_layout.addStretch()
        sidebar.setLayout(sidebar_layout)
        
        # Страницы
        self.page1 = Page1Widget()
        self.page2 = Page2Widget()
        
        # Layout для страниц
        pages_layout = QVBoxLayout()
        pages_layout.addWidget(self.page1)
        pages_layout.addWidget(self.page2)
        self.page2.hide()  # Скрываем вторую страницу
        
        # Собираем
        main_layout.addWidget(sidebar)
        main_layout.addLayout(pages_layout)
        central_widget.setLayout(main_layout)
    
    def show_page(self, index):
        if index == 0:
            self.page1.show()
            self.page2.hide()
        elif index == 1:
            self.page1.hide()
            self.page2.show()
```

### 2. Передача данных между виджетами

```python
class Page1(QWidget):
    # Создаем сигнал для передачи данных
    dataReady = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def on_button_click(self):
        data = {
            'field1': self.input1.text(),
            'field2': self.input2.text()
        }
        # Отправляем данные
        self.dataReady.emit(data)

class Page2(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def receive_data(self, data):
        # Получаем данные от Page1
        print(f"Получены данные: {data}")
        self.label.setText(f"Field1: {data['field1']}")

# В главном окне
page1 = Page1()
page2 = Page2()

# Связываем
page1.dataReady.connect(page2.receive_data)
```

### 3. Работа с диалоговыми окнами

```python
from PyQt5.QtWidgets import QDialog

class CustomDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Диалоговое окно")
        layout = QVBoxLayout()
        
        self.input = QLineEdit()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Отмена")
        
        ok_button.clicked.connect(self.accept)      # Закрывает с кодом 1
        cancel_button.clicked.connect(self.reject)  # Закрывает с кодом 0
        
        layout.addWidget(self.input)
        layout.addWidget(ok_button)
        layout.addWidget(cancel_button)
        self.setLayout(layout)
    
    def get_data(self):
        return self.input.text()

# Использование
dialog = CustomDialog(self)
if dialog.exec_() == QDialog.Accepted:  # Показываем модально
    data = dialog.get_data()
    print(f"Получено: {data}")
else:
    print("Отменено")
```

### 4. Динамическое создание виджетов

```python
def add_row_to_table(self):
    row_count = self.table.rowCount()
    self.table.insertRow(row_count)
    
    # Добавляем ячейки
    self.table.setItem(row_count, 0, QTableWidgetItem("Значение 1"))
    self.table.setItem(row_count, 1, QTableWidgetItem("Значение 2"))
    
    # Добавляем кнопку в ячейку
    button = QPushButton("Удалить")
    button.clicked.connect(lambda: self.delete_row(row_count))
    self.table.setCellWidget(row_count, 2, button)

def delete_row(self, row):
    self.table.removeRow(row)
```

### 5. Сохранение и загрузка данных из таблицы

```python
def save_table_data(self):
    data = []
    for i in range(self.table.rowCount()):
        row = []
        for j in range(self.table.columnCount()):
            item = self.table.item(i, j)
            row.append(item.text() if item else "")
        data.append(row)
    return data

def load_table_data(self, data):
    self.table.setRowCount(len(data))
    self.table.setColumnCount(len(data[0]) if data else 0)
    
    for i, row in enumerate(data):
        for j, value in enumerate(row):
            self.table.setItem(i, j, QTableWidgetItem(str(value)))
```

---

## 🚀 Порядок создания приложения (чек-лист)

1. **Импорты**
   ```python
   from PyQt5.QtWidgets import QApplication, QMainWindow, ...
   from PyQt5.QtCore import Qt, pyqtSignal
   ```

2. **Класс стилей** (опционально, но удобно)
   ```python
   class Styles:
       BUTTON = "..."
       INPUT = "..."
   ```

3. **Создание пользовательских виджетов**
   ```python
   class CustomWidget(QWidget):
       def __init__(self):
           super().__init__()
           self.setup_ui()
       
       def setup_ui(self):
           layout = QVBoxLayout()
           # добавляем виджеты
           self.setLayout(layout)
   ```

4. **Главное окно**
   ```python
   class MainWindow(QMainWindow):
       def __init__(self):
           super().__init__()
           self.setup_ui()
       
       def setup_ui(self):
           central_widget = QWidget()
           self.setCentralWidget(central_widget)
           # настраиваем layout
   ```

5. **Подключение событий**
   ```python
   button.clicked.connect(self.handler)
   ```

6. **Запуск**
   ```python
   app = QApplication(sys.argv)
   window = MainWindow()
   window.show()
   sys.exit(app.exec_())
   ```

---

## 📝 Полезные советы

1. **Всегда вызывайте `super().__init__()`** в конструкторе
2. **Используйте layouts**, не устанавливайте позиции вручную
3. **Создавайте методы `setup_ui()`** для настройки интерфейса
4. **Делите на маленькие виджеты-классы** - так проще управлять
5. **Централизуйте стили** в один класс
6. **Используйте signals для связи** между виджетами
7. **Именуйте переменные понятно**: `self.input_name`, а не `self.le1`
8. **Комментируйте код** - через месяц не вспомните, что делает
9. **Тестируйте по частям** - создайте виджет, убедитесь, что работает, потом добавляйте следующий

---

## 🔗 Полезные ресурсы

- Официальная документация: https://doc.qt.io/qtforpython/
- Qt Examples: примеры кода встроены в Qt
- Stack Overflow: огромное сообщество с ответами

Удачи в создании приложений! 🚀