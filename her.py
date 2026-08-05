# -*- coding: utf-8 -*-
"""
main_demo.py
============

Демонстрационное приложение без стилизации.

Позволяет выбрать один из двух вариантов таблицы и загрузить в неё один
и тот же сгенерированный набор данных, чтобы наглядно увидеть разницу
в потреблении памяти и во времени загрузки:

    1) QTableWidget       -- "наивный" способ (создаёт QTableWidgetItem
                              на каждую ячейку), эталон "плохого" подхода.
    2) DataFrameTableWidget -- собственный виджет на pandas + Qt Model/View
                              с виртуализацией строк.

Использование:
    python main_demo.py

В окне: указываете количество строк, выбираете тип таблицы, жмёте
"Загрузить" -- приложение покажет время загрузки и потребление памяти
процессом (RSS) до/после.
"""

from __future__ import annotations

import gc
import os
import random
import string
import sys
import time
from typing import List, Tuple

from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ger import DataFrameTableWidget

# psutil опционален -- если его нет, просто не показываем память,
# но приложение всё равно работает.
try:
    import psutil

    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


COLUMNS = ["id", "name", "category", "price", "quantity", "created_at"]
CATEGORIES = ["Electronics", "Books", "Toys", "Home", "Sports", "Clothing"]


def generate_dataset(row_count: int) -> List[Tuple]:
    """Сгенерировать синтетический набор данных из row_count строк.

    Возвращает список кортежей -- ровно тот формат, который ожидает
    DataFrameTableWidget.set_dataset(), и который также используется
    для наполнения QTableWidget (построчно), чтобы сравнение было честным.
    """
    rng = random.Random(42)
    letters = string.ascii_uppercase

    def random_name() -> str:
        return "".join(rng.choice(letters) for _ in range(8))

    data: List[Tuple] = []
    base_ts = 1_700_000_000  # произвольная базовая unix-метка времени
    for i in range(row_count):
        data.append(
            (
                i,
                f"{random_name()}-{i}",
                CATEGORIES[i % len(CATEGORIES)],
                round(rng.uniform(1.0, 2000.0), 2),
                rng.randint(0, 500),
                base_ts + i * 60,
            )
        )
    return data


def current_memory_mb() -> float:
    """Текущее потребление памяти процессом (RSS) в мегабайтах."""
    if not _HAS_PSUTIL:
        return -1.0
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


class DemoWindow(QMainWindow):
    """Главное окно демо-приложения. Без стилизации -- только логика."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Демо: QTableWidget vs DataFrameTableWidget")
        self.resize(1000, 700)

        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)

        # -- панель управления -------------------------------------------------
        controls_layout = QHBoxLayout()

        controls_layout.addWidget(QLabel("Тип таблицы:"))
        self.table_type_combo = QComboBox()
        self.table_type_combo.addItems(["DataFrameTableWidget (виртуализация)", "QTableWidget (наивный)"])
        controls_layout.addWidget(self.table_type_combo)

        controls_layout.addWidget(QLabel("Количество строк:"))
        self.row_count_spin = QSpinBox()
        self.row_count_spin.setRange(100, 5_000_000)
        self.row_count_spin.setSingleStep(10_000)
        self.row_count_spin.setValue(200_000)
        controls_layout.addWidget(self.row_count_spin)

        self.load_button = QPushButton("Загрузить")
        self.load_button.clicked.connect(self._on_load_clicked)
        controls_layout.addWidget(self.load_button)

        self.filter_demo_button = QPushButton("Применить пример фильтра (только для DataFrameTableWidget)")
        self.filter_demo_button.clicked.connect(self._on_apply_demo_filter)
        controls_layout.addWidget(self.filter_demo_button)

        controls_layout.addStretch(1)
        root_layout.addLayout(controls_layout)

        # -- строка статуса -------------------------------------------------
        self.status_label = QLabel("Готово к загрузке.")
        root_layout.addWidget(self.status_label)
        if not _HAS_PSUTIL:
            warn = QLabel(
                "Модуль psutil не найден -- замер памяти недоступен "
                "(установите: pip install psutil)."
            )
            root_layout.addWidget(warn)

        # -- контейнер для таблицы (виджет таблицы пересоздаётся при выборе) --
        self.table_container_layout = QVBoxLayout()
        root_layout.addLayout(self.table_container_layout)

        self.current_table_widget: QWidget = None  # type: ignore[assignment]

    # -- обработчики -------------------------------------------------

    def _on_load_clicked(self) -> None:
        row_count = self.row_count_spin.value()
        use_dataframe_widget = self.table_type_combo.currentIndex() == 0

        # Предупреждение для "наивного" варианта на больших объёмах,
        # чтобы не заморозить UI на минуты без объяснения причин.
        if not use_dataframe_widget and row_count > 300_000:
            answer = QMessageBox.warning(
                self,
                "Возможное зависание интерфейса",
                (
                    f"QTableWidget создаёт объект QTableWidgetItem на каждую "
                    f"ячейку. Для {row_count:,} строк x {len(COLUMNS)} колонок "
                    f"это {row_count * len(COLUMNS):,} объектов Qt -- загрузка "
                    "может занять много времени и памяти. Продолжить?"
                ).replace(",", " "),
                QMessageBox.Yes | QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return

        self.status_label.setText("Генерация данных...")
        QApplication.processEvents()

        data = generate_dataset(row_count)

        # Удаляем предыдущую таблицу и просим сборщик мусора освободить
        # память ДО замера "начального" уровня -- иначе сравнение
        # между запусками будет искажено предыдущим виджетом.
        self._clear_current_table()
        gc.collect()
        mem_before = current_memory_mb()

        start_time = time.perf_counter()
        if use_dataframe_widget:
            widget = DataFrameTableWidget()
            widget.set_dataset(data, columns=COLUMNS)
        else:
            widget = self._build_qtablewidget(data)
        elapsed = time.perf_counter() - start_time

        self.current_table_widget = widget
        self.table_container_layout.addWidget(widget)

        gc.collect()
        mem_after = current_memory_mb()

        self._report_result(row_count, use_dataframe_widget, elapsed, mem_before, mem_after)

    def _on_apply_demo_filter(self) -> None:
        """Пример использования публичного API DataFrameTableWidget."""
        if not isinstance(self.current_table_widget, DataFrameTableWidget):
            QMessageBox.information(
                self,
                "Недоступно",
                "Пример фильтра работает только для загруженного DataFrameTableWidget.",
            )
            return

        widget: DataFrameTableWidget = self.current_table_widget
        widget.clear_filters()
        widget.add_filter(column="price", operator=">", value=500)
        widget.add_filter(column="category", operator="equals", value="Electronics")
        widget.apply_filters()

        self.status_label.setText(
            f"Фильтр применён: price > 500 AND category == 'Electronics'. "
            f"Строк после фильтрации: {widget.row_count():,}".replace(",", " ")
        )

    # -- вспомогательные методы -------------------------------------------------

    def _build_qtablewidget(self, data: List[Tuple]) -> QTableWidget:
        """Наивная загрузка в QTableWidget -- по одному QTableWidgetItem
        на каждую ячейку. Специально сделана простой и "в лоб", чтобы
        служить контрастным примером к DataFrameTableWidget."""
        table = QTableWidget()
        table.setColumnCount(len(COLUMNS))
        table.setHorizontalHeaderLabels(COLUMNS)
        table.setRowCount(len(data))

        for row_index, row_values in enumerate(data):
            for col_index, value in enumerate(row_values):
                item = QTableWidgetItem(str(value))
                table.setItem(row_index, col_index, item)

        return table

    def _clear_current_table(self) -> None:
        if self.current_table_widget is not None:
            self.table_container_layout.removeWidget(self.current_table_widget)
            self.current_table_widget.deleteLater()
            self.current_table_widget = None  # type: ignore[assignment]

    def _report_result(
        self,
        row_count: int,
        used_dataframe_widget: bool,
        elapsed_seconds: float,
        mem_before_mb: float,
        mem_after_mb: float,
    ) -> None:
        widget_name = "DataFrameTableWidget" if used_dataframe_widget else "QTableWidget"
        lines = [
            f"Таблица: {widget_name}",
            f"Строк загружено: {row_count:,}".replace(",", " "),
            f"Время загрузки: {elapsed_seconds:.3f} c",
        ]
        if _HAS_PSUTIL:
            lines.append(f"Память до: {mem_before_mb:.1f} МБ")
            lines.append(f"Память после: {mem_after_mb:.1f} МБ")
            lines.append(f"Прирост памяти: {mem_after_mb - mem_before_mb:.1f} МБ")
        self.status_label.setText(" | ".join(lines))


def main() -> None:
    app = QApplication(sys.argv)
    window = DemoWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()