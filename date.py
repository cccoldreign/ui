"""
╔════════════════════════════════════════════════════════════════════════════════╗
║                     CustomDateEdit — ПРОСТОЙ ВИДЖЕТ ДЛЯ ДАТ                  ║
╠════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  КОМПОНЕНТЫ:                                                                   ║
║    • QLineEdit        — отображает дату в формате YYYY-MM-DD                  ║
║    • Кнопка 📅       — открывает календарь для выбора                        ║
║    • Кнопка ✕        — очищает поле (делает его пусто)                       ║
║                                                                                ║
║  МЕТОДЫ:                                                                       ║
║    set_date(value)  — установить дату (None, "", или "2026-05-06")           ║
║    get_date()       — получить дату ("2026-05-06" или "" если пусто)          ║
║                                                                                ║
║  СИГНАЛЫ:                                                                      ║
║    dateChanged      — сигнал при изменении даты                               ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLineEdit, QPushButton, QDialog, QVBoxLayout, QCalendarWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QDate


class CustomDateEdit(QFrame):
    """
    Виджет для работы с датами в формате YYYY-MM-DD.
    
    Особенности:
    - Простой QLineEdit для ввода даты
    - Календарь для удобного выбора даты
    - Кнопка очистки (делает поле пусто = NULL в БД)
    - Никогда не возвращает None или "none" — только "" или "YYYY-MM-DD"
    
    Пример использования:
    ─────────────────────────────────────────────────────────────
    from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton
    from date import CustomDateEdit
    
    class MyForm(QWidget):
        def __init__(self):
            super().__init__()
            layout = QVBoxLayout(self)
            
            # Добавить в форму
            self.date_field = CustomDateEdit()
            layout.addWidget(self.date_field)
            
            # Кнопка сохранения
            btn_save = QPushButton("Сохранить")
            btn_save.clicked.connect(self.save_to_db)
            layout.addWidget(btn_save)
        
        def save_to_db(self):
            # Получить дату
            date_str = self.date_field.get_date()
            
            if date_str:
                # Дата заполнена
                sql = f"UPDATE table SET birth_date = '{date_str}' WHERE id = 1"
            else:
                # Дата пусто → NULL в БД
                sql = "UPDATE table SET birth_date = NULL WHERE id = 1"
            
            # Выполнить sql
            db.execute(sql)
        
        def load_from_db(self):
            # Из БД получили дату (может быть None)
            row = db.fetchone("SELECT birth_date FROM table WHERE id = 1")
            
            # Установить в виджет
            if row.birth_date:
                self.date_field.set_date(row.birth_date)  # "2000-05-15"
            else:
                self.date_field.set_date("")  # Пусто
    ─────────────────────────────────────────────────────────────
    """
    
    dateChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """Построить интерфейс"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # QLineEdit для ввода даты
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("YYYY-MM-DD или оставить пусто")
        self.edit.setMaxLength(10)
        
        # Кнопка открытия календаря
        btn_calendar = QPushButton("📅")
        btn_calendar.setMaximumWidth(40)
        btn_calendar.clicked.connect(self._open_calendar)
        
        # Кнопка очистки
        btn_clear = QPushButton("✕")
        btn_clear.setMaximumWidth(40)
        btn_clear.clicked.connect(self._clear)
        
        layout.addWidget(self.edit)
        layout.addWidget(btn_calendar)
        layout.addWidget(btn_clear)

    def set_date(self, value):
        """
        Установить дату в поле.
        
        Параметры:
            None       → очистить поле
            ""         → очистить поле
            "2026-05-06" → вставить эту дату
            "2026-05-06 10:15:30" → вставить только дату (первые 10 символов)
        
        Возвращает: ничего
        
        Примеры:
        ────────────────────────────────────────
        self.date_field.set_date(None)           # Пусто
        self.date_field.set_date("")             # Пусто
        self.date_field.set_date("2026-05-06")   # Вставить дату
        self.date_field.set_date(row.birth_date) # Из БД
        ────────────────────────────────────────
        """
        if value is None or value == "":
            self.edit.clear()
        else:
            # Берём только YYYY-MM-DD (первые 10 символов)
            date_str = str(value)[:10]
            self.edit.setText(date_str)

    def get_date(self):
        """
        Получить дату из поля.
        
        Возвращает:
            ""         — если поле пусто (используй NULL для БД)
            "2026-05-06" — если дата заполнена
        
        НИКОГДА не возвращает None или "none"!
        
        Примеры:
        ────────────────────────────────────────
        date_str = self.date_field.get_date()
        
        if date_str:
            # Дата заполнена
            sql = f"UPDATE table SET birth_date = '{date_str}' WHERE id = 1"
        else:
            # Пусто → NULL
            sql = "UPDATE table SET birth_date = NULL WHERE id = 1"
        ────────────────────────────────────────
        """
        return self.edit.text().strip()

    def _open_calendar(self):
        """Открыть диалог с календарём"""
        dialog = QDialog(self.window())
        dialog.setWindowTitle("Выберите дату")
        dialog.setGeometry(200, 200, 400, 350)
        
        layout = QVBoxLayout(dialog)
        
        calendar = QCalendarWidget()
        
        # Если в поле уже есть дата, загружаем её в календарь
        current_date_str = self.get_date()
        if current_date_str:
            try:
                parts = current_date_str.split("-")
                if len(parts) == 3:
                    calendar.setSelectedDate(QDate(int(parts[0]), int(parts[1]), int(parts[2])))
                else:
                    calendar.setSelectedDate(QDate.currentDate())
            except:
                calendar.setSelectedDate(QDate.currentDate())
        else:
            calendar.setSelectedDate(QDate.currentDate())
        
        layout.addWidget(calendar)
        
        # Кнопки OK / Отмена
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("ОК")
        btn_cancel = QPushButton("Отмена")
        
        def on_ok():
            """При нажатии OK вставить выбранную дату в поле"""
            selected_date = calendar.selectedDate()
            date_str = selected_date.toString("yyyy-MM-dd")
            self.edit.setText(date_str)
            self.dateChanged.emit()
            dialog.accept()
        
        btn_ok.clicked.connect(on_ok)
        btn_cancel.clicked.connect(dialog.reject)
        
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        dialog.exec_()

    def _clear(self):
        """Очистить поле (сделать его пусто)"""
        self.edit.clear()
        self.dateChanged.emit()


# ════════════════════════════════════════════════════════════════════════════════
#  ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
# ════════════════════════════════════════════════════════════════════════════════

"""

📌 ПРИМЕР 1: Простая форма с одним полем даты
═══════════════════════════════════════════════════════════════════════════════

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton
from date import CustomDateEdit
import sys

class SimpleForm(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Форма с датой")
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Дата рождения:"))
        self.birth_date = CustomDateEdit()
        layout.addWidget(self.birth_date)
        
        btn_show = QPushButton("Показать дату")
        btn_show.clicked.connect(self.show_date)
        layout.addWidget(btn_show)
        
        layout.addStretch()
    
    def show_date(self):
        date_str = self.birth_date.get_date()
        if date_str:
            print(f"Выбрана дата: {date_str}")
        else:
            print("Дата не выбрана")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    form = SimpleForm()
    form.show()
    sys.exit(app.exec_())


📌 ПРИМЕР 2: Работа с БД
═══════════════════════════════════════════════════════════════════════════════

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QMessageBox
from date import CustomDateEdit
import sys

class EmployeeForm(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.employee_id = None
        
        self.setWindowTitle("Редактирование сотрудника")
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # ID (только для чтения)
        layout.addWidget(QLabel("ID:"))
        self.id_field = QLineEdit()
        self.id_field.setReadOnly(True)
        layout.addWidget(self.id_field)
        
        # Фамилия
        layout.addWidget(QLabel("Фамилия:"))
        self.last_name_field = QLineEdit()
        layout.addWidget(self.last_name_field)
        
        # Имя
        layout.addWidget(QLabel("Имя:"))
        self.first_name_field = QLineEdit()
        layout.addWidget(self.first_name_field)
        
        # ===== ДАТА РОЖДЕНИЯ =====
        layout.addWidget(QLabel("Дата рождения:"))
        self.birth_date_field = CustomDateEdit()  # ← ВОТ НАШ ВИДЖЕТ
        layout.addWidget(self.birth_date_field)
        
        # Кнопки
        btn_load = QPushButton("Загрузить (ID=1)")
        btn_load.clicked.connect(self.load_employee)
        layout.addWidget(btn_load)
        
        btn_save = QPushButton("💾 Сохранить")
        btn_save.clicked.connect(self.save_employee)
        layout.addWidget(btn_save)
        
        layout.addStretch()
    
    def load_employee(self):
        """Загрузить сотрудника из БД"""
        try:
            sql = "SELECT id, last_name, first_name, birth_date FROM employees WHERE id = 1"
            row = self.db.fetchone(sql)
            
            if not row:
                QMessageBox.warning(self, "Ошибка", "Сотрудник не найден")
                return
            
            self.employee_id = row.id
            self.id_field.setText(str(row.id))
            self.last_name_field.setText(row.last_name or "")
            self.first_name_field.setText(row.first_name or "")
            
            # ← КЛЮЧЕВОЙ МОМЕНТ: установить дату
            if row.birth_date:
                self.birth_date_field.set_date(row.birth_date)  # "2000-05-15"
            else:
                self.birth_date_field.set_date("")  # Пусто если NULL
            
            QMessageBox.information(self, "Успех", f"Загружен: {row.first_name} {row.last_name}")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
    
    def save_employee(self):
        """Сохранить сотрудника в БД"""
        if not self.employee_id:
            QMessageBox.warning(self, "Ошибка", "Сначала загрузите сотрудника")
            return
        
        try:
            last_name = self.last_name_field.text().strip()
            first_name = self.first_name_field.text().strip()
            
            # ← КЛЮЧЕВОЙ МОМЕНТ: получить дату
            birth_date_str = self.birth_date_field.get_date()
            
            if birth_date_str:
                # Дата заполнена → используем значение
                birth_date_sql = f"'{birth_date_str}'"
            else:
                # Дата пусто → используем NULL
                birth_date_sql = "NULL"
            
            sql = (
                f"UPDATE employees SET "
                f"last_name = '{last_name.replace(chr(39), chr(39)*2)}', "
                f"first_name = '{first_name.replace(chr(39), chr(39)*2)}', "
                f"birth_date = {birth_date_sql} "
                f"WHERE id = {self.employee_id}"
            )
            
            self.db.execute(sql)
            QMessageBox.information(self, "Успех", "Данные сохранены")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))


📌 ПРИМЕР 3: Множество полей даты в одной форме
═══════════════════════════════════════════════════════════════════════════════

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton
from date import CustomDateEdit
import sys

class ContractForm(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Форма контракта")
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Дата начала
        layout.addWidget(QLabel("Дата начала:"))
        self.start_date = CustomDateEdit()
        layout.addWidget(self.start_date)
        
        # Дата окончания
        layout.addWidget(QLabel("Дата окончания:"))
        self.end_date = CustomDateEdit()
        layout.addWidget(self.end_date)
        
        # Дата подписи
        layout.addWidget(QLabel("Дата подписи:"))
        self.sign_date = CustomDateEdit()
        layout.addWidget(self.sign_date)
        
        # Кнопка сохранения
        btn_save = QPushButton("Сохранить контракт")
        btn_save.clicked.connect(self.save_contract)
        layout.addWidget(btn_save)
        
        layout.addStretch()
    
    def save_contract(self):
        """Собрать данные из всех полей даты"""
        start = self.start_date.get_date()
        end = self.end_date.get_date()
        sign = self.sign_date.get_date()
        
        print(f"Начало: {start or 'не указана'}")
        print(f"Конец: {end or 'не указана'}")
        print(f"Подпись: {sign or 'не указана'}")
        
        # Готовим SQL
        sql_parts = []
        
        sql_parts.append(f"start_date = {f\"'{start}'\" if start else 'NULL'}")
        sql_parts.append(f"end_date = {f\"'{end}'\" if end else 'NULL'}")
        sql_parts.append(f"sign_date = {f\"'{sign}'\" if sign else 'NULL'}")
        
        sql = f"UPDATE contracts SET {', '.join(sql_parts)} WHERE id = 1"
        print(f"\\nSQL: {sql}")


📌 ПРИМЕР 4: Сигналы (реагировать на изменение даты)
═══════════════════════════════════════════════════════════════════════════════

class MyForm(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        self.date_field = CustomDateEdit()
        # При изменении даты → вызывается on_date_changed
        self.date_field.dateChanged.connect(self.on_date_changed)
        layout.addWidget(self.date_field)
    
    def on_date_changed(self):
        """Вызывается когда пользователь изменил дату"""
        new_date = self.date_field.get_date()
        print(f"Дата изменена на: {new_date or 'пусто'}")


════════════════════════════════════════════════════════════════════════════════
"""
