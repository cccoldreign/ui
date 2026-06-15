"""
SearchSelectWidget — переиспользуемый виджет поиска с автодополнением и выбором из списка.

Архитектура:
  - SearchSelectWidget   — основной виджет
  - DemoWindow           — демонстрационное окно

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 КАК СТИЛИЗОВАТЬ ВИДЖЕТ СНАРУЖИ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  widget = SearchSelectWidget()

  # --- Стиль поля ввода ---
  widget.edit_stylesheet = \"\"\"
      QLineEdit {
          border: 2px solid #C0C8D8;
          border-radius: 6px;
          padding: 4px 8px;
          font-size: 14px;
          background: #FFFFFF;
          color: #1A2233;
      }
      QLineEdit:focus {
          border-color: #4A7FD4;
      }
  \"\"\"

  # --- Стиль кнопки-стрелки ---
  widget.btn_stylesheet = \"\"\"
      QPushButton {
          border: 1px solid #C0C8D8;
          border-left: none;
          border-top-right-radius: 6px;
          border-bottom-right-radius: 6px;
          background: #F5F7FA;
          color: #6B7A99;
          font-size: 11px;
      }
      QPushButton:hover {
          background: #E8EEF8;
          color: #4A7FD4;
      }
  \"\"\"

  # Вызвать apply_styles() ПОСЛЕ установки обоих свойств
  widget.apply_styles()

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QHBoxLayout, QVBoxLayout,
    QMainWindow, QLabel, QSizePolicy, QAbstractItemView
)
from PyQt5.QtCore import Qt, QPoint, QSize, QEvent
from PyQt5.QtGui import QFont


# ---------------------------------------------------------------------------
# SearchSelectWidget
# ---------------------------------------------------------------------------

class SearchSelectWidget(QWidget):
    """
    Виджет поиска с автодополнением и выбором из выпадающего списка.

    Публичный API:
        set_data(data)               — загрузить датасет [(id, text), ...]
        get_selected_id()            -> int | None
        get_selected_text()          -> str | None
        set_selected_id(id_value)    — выбрать по ID
        set_selected_text(text)      — выбрать первый совпадающий по тексту
        apply_styles()               — применить edit_stylesheet / btn_stylesheet
        edit_stylesheet: str         — QSS для поля ввода
        btn_stylesheet:  str         — QSS для кнопки ▼
    """

    _ROW_HEIGHT = 24
    _MAX_VISIBLE_ROWS = 8

    def __init__(self, parent=None):
        super().__init__(parent)

        self._data: list[tuple[int, str]] = []
        self._filtered: list[tuple[int, str]] = []
        self._selected_id: int | None = None
        self._selected_text: str | None = None
        self._suppress_filter = False

        # публичные свойства для стилизации
        self.edit_stylesheet: str = ""
        self.btn_stylesheet: str = ""

        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # Построение UI (без стилей)
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._edit = QLineEdit()
        self._edit.setPlaceholderText("Поиск…")
        self._edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._btn = QPushButton("▼")
        self._btn.setFixedWidth(24)
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.setFocusPolicy(Qt.NoFocus)

        root.addWidget(self._edit)
        root.addWidget(self._btn)

        # popup создаётся лениво в _ensure_popup()
        self._popup: QListWidget | None = None

    def apply_styles(self):
        """Применить edit_stylesheet и btn_stylesheet к дочерним виджетам."""
        if self.edit_stylesheet:
            self._edit.setStyleSheet(self.edit_stylesheet)
        if self.btn_stylesheet:
            self._btn.setStyleSheet(self.btn_stylesheet)

    # ------------------------------------------------------------------
    # Сигналы
    # ------------------------------------------------------------------

    def _connect_signals(self):
        self._edit.textChanged.connect(self._on_text_changed)
        self._edit.returnPressed.connect(self._on_enter)
        self._btn.clicked.connect(self._toggle_popup)
        self._edit.installEventFilter(self)

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def set_data(self, data: list[tuple[int, str]]) -> None:
        self._data = list(data)
        self._filtered = list(data)

    def get_selected_id(self) -> int | None:
        return self._selected_id

    def get_selected_text(self) -> str | None:
        return self._selected_text

    def set_selected_id(self, id_value: int) -> None:
        for item_id, item_text in self._data:
            if item_id == id_value:
                self._select(item_id, item_text)
                return

    def set_selected_text(self, text: str) -> None:
        for item_id, item_text in self._data:
            if item_text == text:
                self._select(item_id, item_text)
                return

    # ------------------------------------------------------------------
    # Внутренняя логика
    # ------------------------------------------------------------------

    def _select(self, item_id: int, item_text: str) -> None:
        self._selected_id = item_id
        self._selected_text = item_text
        self._suppress_filter = True
        self._edit.setText(item_text)
        self._suppress_filter = False
        self._edit.setFocus()
        self._close_popup()

    def _filter(self, query: str) -> None:
        q = query.strip().lower()
        if q:
            self._filtered = [(i, t) for i, t in self._data if q in t.lower()]
        else:
            self._filtered = list(self._data)

    # ------------------------------------------------------------------
    # Popup
    # ------------------------------------------------------------------

    def _ensure_popup(self):
        """Создать popup как дочерний виджет верхнего окна (без захвата фокуса)."""
        if self._popup is not None:
            return

        top = self.window()
        self._popup = QListWidget(top)
        self._popup.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
        )
        self._popup.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self._popup.setFocusPolicy(Qt.NoFocus)
        self._popup.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._popup.setSelectionMode(QAbstractItemView.SingleSelection)
        self._popup.hide()

        self._popup.itemClicked.connect(self._on_item_clicked)
        top.installEventFilter(self)

    def _populate_popup(self):
        self._popup.clear()
        for item_id, item_text in self._filtered:
            item = QListWidgetItem(f"{item_text} | {item_id}")
            item.setData(Qt.UserRole, (item_id, item_text))
            self._popup.addItem(item)

    def _show_popup(self):
        self._ensure_popup()
        if not self._filtered:
            self._close_popup()
            return

        self._populate_popup()

        visible = min(len(self._filtered), self._MAX_VISIBLE_ROWS)
        h = visible * self._ROW_HEIGHT + 8
        w = self.width()
        pos = self.mapToGlobal(QPoint(0, self.height()))

        self._popup.setFixedSize(QSize(w, h))
        self._popup.move(pos)
        self._popup.show()
        self._popup.raise_()
        self._edit.setFocus()

    def _close_popup(self):
        if self._popup:
            self._popup.hide()

    def _toggle_popup(self):
        self._ensure_popup()
        if self._popup.isVisible():
            self._close_popup()
        else:
            self._filter("")
            self._show_popup()
        self._edit.setFocus()

    # ------------------------------------------------------------------
    # Обработчики
    # ------------------------------------------------------------------

    def _on_text_changed(self, text: str):
        if self._suppress_filter:
            return
        # сброс явного выбора при ручном вводе
        self._selected_id = None
        self._selected_text = None
        self._filter(text)
        self._show_popup()

    def _on_item_clicked(self, list_item: QListWidgetItem):
        item_id, item_text = list_item.data(Qt.UserRole)
        self._select(item_id, item_text)

    def _on_enter(self):
        """
        Enter:
          - Если элемент уже выбран явно (через список) — сразу печатаем.
          - Иначе — берём первое совпадение по введённому тексту.
            Если совпадений несколько — выбирается первый из списка (не просим уточнять).
          - Если совпадений нет — сообщаем.
        """
        self._close_popup()

        if self._selected_id is not None:
            # явный выбор через клик по списку
            print(f"ID: {self._selected_id}, Name: {self._selected_text}")
            return

        # текст введён вручную — ищем первое совпадение
        current_text = self._edit.text().strip()
        matches = [(i, t) for i, t in self._data if t.lower() == current_text.lower()]

        if matches:
            # берём первый совпавший (уникальность не требуется)
            self._select(matches[0][0], matches[0][1])
            print(f"ID: {self._selected_id}, Name: {self._selected_text}")
        else:
            print(f"Ничего не найдено для: '{current_text}'")

    # ------------------------------------------------------------------
    # Event filter
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event):
        if obj is self._edit and event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Escape:
                self._close_popup()
                return True
            if self._popup and self._popup.isVisible():
                if key == Qt.Key_Down:
                    self._move_selection(1)
                    return True
                if key == Qt.Key_Up:
                    self._move_selection(-1)
                    return True
                if key in (Qt.Key_Return, Qt.Key_Enter):
                    cur = self._popup.currentItem()
                    if cur:
                        self._on_item_clicked(cur)
                        return True

        # клик вне виджета и вне popup — закрыть список
        if event.type() == QEvent.MouseButtonPress:
            if self._popup and self._popup.isVisible():
                gp = event.globalPos()
                if (not self._popup.geometry().contains(gp) and
                        not self.geometry().translated(
                            self.mapToGlobal(QPoint(0, 0)) - self.pos()
                        ).contains(gp)):
                    self._close_popup()

        return super().eventFilter(obj, event)

    def _move_selection(self, direction: int):
        n = self._popup.count()
        if not n:
            return
        row = max(0, min(n - 1, self._popup.currentRow() + direction))
        self._popup.setCurrentRow(row)

    # ------------------------------------------------------------------
    # Перемещать popup при resize / move
    # ------------------------------------------------------------------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._popup and self._popup.isVisible():
            self._show_popup()

    def moveEvent(self, event):
        super().moveEvent(event)
        if self._popup and self._popup.isVisible():
            self._show_popup()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._close_popup()


# ---------------------------------------------------------------------------
# DemoWindow
# ---------------------------------------------------------------------------

class DemoWindow(QMainWindow):

    DATASET = [
        (10, "Samsung"),
        (12, "Samsung"),
        (13, "Toshiba"),
        (14, "Apple"),
        (15, "Apple"),
        (16, "Sony"),
        (17, "LG"),
        (18, "Huawei"),
        (19, "Xiaomi"),
        (20, "Lenovo"),
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SearchSelectWidget — Demo")
        self.resize(400, 120)

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Выбор производителя:"))

        self._widget = SearchSelectWidget()
        self._widget.set_data(self.DATASET)
        layout.addWidget(self._widget)
        layout.addStretch()


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DemoWindow()
    window.show()
    sys.exit(app.exec_())