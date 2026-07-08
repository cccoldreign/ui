# -*- coding: utf-8 -*-
"""
demo_app.py
===========

Минимальное демонстрационное приложение для компонента UniversalTable.

Окно содержит:
    * две кнопки, каждая из которых вызывает свою внешнюю функцию,
      передающую в таблицу новый набор тестовых данных;
    * саму универсальную таблицу.

Внешние функции load_dataset_one() и load_dataset_two() ничего не знают о
внутреннем устройстве UniversalTable — они лишь вызывают его публичный
метод set_data(). Это иллюстрирует, что вся логика отображения и
отслеживания изменений находится внутри компонента, а внешний код
взаимодействует с ним только через публичный API.

Дополнительно продемонстрирована подписка на сигналы rowChanged и
dataChangedSignal, а также callback-функция для кнопки в последнем
столбце каждой строки.
"""

from __future__ import annotations

import sys
from typing import Any, List, Tuple

from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from tab import UniversalTable


# --------------------------------------------------------------------------- #
#  Внешние функции-поставщики данных
#  (компонент таблицы ничего не знает об их существовании)
# --------------------------------------------------------------------------- #


def load_dataset_one(table: UniversalTable) -> None:
    """
    Внешняя функция, передающая в таблицу первый тестовый набор данных.

    Формат каждой строки: (id, ФИО, дата рождения, статус, город).
    """
    rows: List[Tuple[Any, ...]] = [
        (1, "Иванов Иван Иванович", "1990-05-14", "Да", "Москва"),
        (2, "Петров Петр Петрович", "1985-11-02", "Нет", "Санкт-Петербург"),
        (3, "Сидорова Анна Юрьевна", "1998-01-23", "Да", "Казань"),
    ]
    table.set_data(rows)


def load_dataset_two(table: UniversalTable) -> None:
    """
    Внешняя функция, передающая в таблицу второй тестовый набор данных
    (другого размера и с другими значениями — для проверки корректной
    полной замены содержимого таблицы без пересоздания виджета).
    """
    rows: List[Tuple[Any, ...]] = [
        (10, "Кузнецов Алексей Сергеевич", "1979-07-30", "Нет", "Новосибирск"),
        (11, "Смирнова Ольга Дмитриевна", "2001-09-09", "Да", "Екатеринбург"),
        (12, "Морозов Дмитрий Олегович", "1993-03-17", "Да", "Челябинск"),
        (13, "Волкова Мария Андреевна", "1988-12-25", "Нет", "Самара"),
    ]
    table.set_data(rows)


# --------------------------------------------------------------------------- #
#  Callback для кнопки в служебном столбце строки
# --------------------------------------------------------------------------- #


def on_row_button_clicked(record_id: Any) -> None:
    """Вызывается при нажатии кнопки в строке; выводит id записи."""
    print(f"[row_button_callback] Нажата кнопка в строке с id = {record_id!r}")


def on_city_double_clicked(row: int, city: Any) -> None:
    """Пример внешней функции, привязанной к двойному клику по столбцу
    "Город" — компонент таблицы ничего не знает об этой функции."""
    print(f"[double_click: город] Строка {row}, город = {city!r}")


# --------------------------------------------------------------------------- #
#  Главное окно демонстрационного приложения
# --------------------------------------------------------------------------- #


class DemoWindow(QMainWindow):
    """Простое окно без какого-либо особого дизайна для демонстрации
    работы компонента UniversalTable."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Демонстрация UniversalTable")
        self.resize(800, 400)

        self.table = UniversalTable(
            date_columns=[2],
            combo_columns={3: ["Да", "Нет"]},
            row_button_callback=on_row_button_clicked,
            button_text="Выбрать",
            column_headers=["ID", "ФИО", "Дата рождения", "Активен", "Город"],
            # Столбец ID — фиксированной, небольшой ширины.
            column_widths={0: 500},
            # Столбец "Город" — широкий, с переносом слов.
            wrap_columns=[4],
            # Двойной клик по столбцу "Город" вызывает внешнюю функцию.
            double_click_handlers={4: on_city_double_clicked},
        )

        self.table.rowChanged.connect(self._on_row_changed)
        self.table.dataChangedSignal.connect(self._on_data_changed)

        # Пример привязки/отвязки обработчика двойного клика уже ПОСЛЕ
        # создания таблицы, а не только через конструктор:
        # self.table.set_double_click_handler(1, lambda row, value: print(row, value))
        # self.table.remove_double_click_handler(1)

        button_one = QPushButton("Загрузить набор данных 1")
        button_two = QPushButton("Загрузить набор данных 2")
        button_new_rows = QPushButton("Показать введённые новые строки")
        button_one.clicked.connect(lambda: load_dataset_one(self.table))
        button_two.clicked.connect(lambda: load_dataset_two(self.table))
        button_new_rows.clicked.connect(self._show_new_rows)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(button_one)
        buttons_layout.addWidget(button_two)
        buttons_layout.addWidget(button_new_rows)

        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.addLayout(buttons_layout)
        main_layout.addWidget(self.table)
        self.setCentralWidget(central_widget)

        # Загружаем первый набор данных сразу при старте для удобства демонстрации.
        load_dataset_one(self.table)

    def _on_row_changed(self, row: int, record_id: Any) -> None:
        print(f"[rowChanged] Активная строка изменилась: row={row}, id={record_id!r}")

    def _on_data_changed(self, change: dict) -> None:
        print(f"[dataChangedSignal] Изменение: {change}")

    def _show_new_rows(self) -> None:
        """
        Демонстрирует get_new_rows(): показывает записи, которые
        пользователь начал вводить в последнюю (всегда пустую) строку
        таблицы, но которые ещё нигде не сохранены.
        """
        new_rows = self.table.get_new_rows()
        if not new_rows:
            text = "Новых (несохранённых) строк пока нет."
        else:
            text = "\n".join(str(row) for row in new_rows)
        QMessageBox.information(self, "Новые строки", text)


def main() -> None:
    app = QApplication(sys.argv)
    window = DemoWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()