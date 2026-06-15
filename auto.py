"""
AutoComplete demo app with:
- Fuzzy/contains matching that updates as you type
- Dropdown arrow button showing all matches with (name | id)
- Disambiguation of duplicates by ID
- Enter prints selected name + id to terminal
"""

import sys
from typing import List, Optional
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QCompleter, QListWidget, QListWidgetItem,
    QFrame, QPushButton, QToolButton, QMenu, QAction, QSizePolicy
)
from PyQt5.QtCore import (
    Qt, QStringListModel, QSortFilterProxyModel, QAbstractListModel,
    QModelIndex, pyqtSignal, QPoint, QEvent
)
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette

# ─────────────────────────── Data Model ───────────────────────────

class Item:
    def __init__(self, name: str, item_id: str):
        self.name = name
        self.id = item_id

    def __repr__(self):
        return f"Item({self.name!r}, id={self.id!r})"


DATASET: List[Item] = [
    Item("Samsung",  "10"),
    Item("Samsung",  "12"),
    Item("Toshiba",  "13"),
    Item("Sony",     "20"),
    Item("Sony",     "21"),
    Item("LG",       "30"),
    Item("Panasonic","40"),
    Item("Philips",  "50"),
    Item("Philips",  "55"),
    Item("Apple",    "60"),
    Item("Huawei",   "70"),
    Item("Xiaomi",   "80"),
    Item("Nokia",    "90"),
    Item("Nokia",    "91"),
    Item("HP",      "100"),
    Item("Dell",    "110"),
    Item("Lenovo",  "120"),
]


# ─────────────────────── AutoComplete Widget ───────────────────────

class AutoCompleteLineEdit(QWidget):
    """
    Composite widget: QLineEdit + dropdown arrow button.
    - Completer suggests names that CONTAIN the typed text (case-insensitive).
    - Arrow button opens a popup list of ALL matches, showing "Name  |  ID".
    - Selecting from either completer or popup sets the internal selected Item.
    - Enter / Return prints ID + name to terminal.
    """

    itemSelected = pyqtSignal(object)   # emits Item or None

    def __init__(self, data: List[Item], parent=None):
        super().__init__(parent)
        self._data = data
        self._selected: Optional[Item] = None
        self._popup: Optional[QListWidget] = None
        self._building_completer = False

        self._build_ui()
        self._connect_signals()

    # ── UI ──────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Main text input
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("Start typing a brand name…")
        self.line_edit.setMinimumHeight(38)
        self.line_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)


        # Completer — suggest names containing typed text
        self._completer = QCompleter()
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self.line_edit.setCompleter(self._completer)

        # Dropdown arrow button
        self.arrow_btn = QToolButton()
        self.arrow_btn.setText("▾")
        self.arrow_btn.setMinimumHeight(38)
        self.arrow_btn.setMinimumWidth(32)
        self.arrow_btn.setCursor(Qt.ArrowCursor)

        layout.addWidget(self.line_edit)
        layout.addWidget(self.arrow_btn)

    def _connect_signals(self):
        self.line_edit.textEdited.connect(self._on_text_edited)
        self.line_edit.returnPressed.connect(self._on_enter)
        self.arrow_btn.clicked.connect(self._show_popup)
        # When user picks from completer popup
        self._completer.activated.connect(self._on_completer_activated)

    # ── Internal helpers ─────────────────────────────────────────────

    def _matches_for(self, text: str) -> List[Item]:
        """Return all items whose name contains `text` (case-insensitive)."""
        t = text.strip().lower()
        if not t:
            return list(self._data)
        return [item for item in self._data if t in item.name.lower()]

    def _update_completer(self, text: str):
        """Rebuild completer model with distinct names from current matches."""
        matches = self._matches_for(text)
        # Keep unique names in order; preserve duplicates only if they have
        # different names (for completer display we show names only)
        seen = set()
        names = []
        for item in matches:
            if item.name not in seen:
                seen.add(item.name)
                names.append(item.name)
        model = QStringListModel(names)
        self._completer.setModel(model)

    def _select_item(self, item: Item):
        """Mark an item as selected and update the field."""
        self._selected = item
        self._building_completer = True
        self.line_edit.setText(item.name)
        self._building_completer = False
        self.itemSelected.emit(item)

    # ── Slots ────────────────────────────────────────────────────────

    def _on_text_edited(self, text: str):
        """Update completer suggestions whenever the user types."""
        self._selected = None           # typing breaks any earlier selection
        self._update_completer(text)

    def _on_completer_activated(self, text: str):
        """
        Called when user picks a suggestion from the completer popup.
        If name is unique → select it. If ambiguous → show popup to pick ID.
        """
        matches = [item for item in self._data if item.name == text]
        if len(matches) == 1:
            self._select_item(matches[0])
        else:
            # Multiple IDs for same name → let user disambiguate
            self._show_popup(matches)

    def _on_enter(self):
        """Print selected item or best match to terminal."""
        text = self.line_edit.text().strip()

        # If user has explicitly selected something, use it
        if self._selected:
            print(f"ID: {self._selected.id}  |  Name: {self._selected.name}")
            return

        # Try exact name match
        exact = [item for item in self._data if item.name.lower() == text.lower()]
        if len(exact) == 1:
            self._select_item(exact[0])
            print(f"ID: {exact[0].id}  |  Name: {exact[0].name}")
        elif len(exact) > 1:
            print(f"[!] Ambiguous name '{text}' — {len(exact)} items found:")
            for item in exact:
                print(f"    ID: {item.id}  |  Name: {item.name}")
            print("    → Use the ▾ button or choose from the dropdown to pick one.")
        elif text:
            print(f"[?] No match for '{text}'")
        else:
            print("[?] Nothing entered.")

    def _show_popup(self, items: Optional[List[Item]] = None):
        """
        Open a floating list widget below the input.
        `items` overrides the default (all matches for current text).
        """
        if items is None:
            text = self.line_edit.text()
            items = self._matches_for(text)

        if not items:
            return

        # Destroy previous popup
        self._close_popup()

        popup = QListWidget()
        popup.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        popup.setAttribute(Qt.WA_DeleteOnClose)
        
        popup.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        for item in items:
            label = f"{item.name}   |   ID: {item.id}"
            list_item = QListWidgetItem(label)
            list_item.setData(Qt.UserRole, item)
            popup.addItem(list_item)

        # Position below the widget
        global_pos = self.mapToGlobal(QPoint(0, self.height()))
        popup.move(global_pos)
        popup.resize(max(self.width(), 260), min(len(items) * 36 + 4, 280))

        def on_item_clicked(li: QListWidgetItem):
            selected_item: Item = li.data(Qt.UserRole)
            self._select_item(selected_item)
            popup.close()

        popup.itemClicked.connect(on_item_clicked)
        popup.installEventFilter(self)
        self._popup = popup
        popup.show()
        popup.setFocus()

    def _close_popup(self):
        if self._popup is not None:
            try:
                self._popup.close()
            except RuntimeError:
                pass
            self._popup = None

    def eventFilter(self, obj, event):
        """Close popup when focus leaves it."""
        if obj is self._popup and event.type() == QEvent.FocusOut:
            self._close_popup()
        return super().eventFilter(obj, event)

    # ── Public API (mirrors original class) ──────────────────────────

    def get_selected_id(self) -> Optional[str]:
        return self._selected.id if self._selected else None

    def get_selected_item(self) -> Optional[Item]:
        return self._selected

    def set_value_by_id(self, item_id: str):
        match = next((i for i in self._data if i.id == item_id), None)
        if match:
            self._select_item(match)
        else:
            self.line_edit.clear()
            self._selected = None


# ─────────────────────────── Main Window ───────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoComplete Demo")
        self.setMinimumWidth(480)
        self.resize(520, 320)

        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(18)

        # Title
        title = QLabel("Brand Lookup")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        root.addWidget(title)

        hint = QLabel(
            "Type to search · press <b>▾</b> to browse all matches · "
            "press <b>Enter</b> to confirm and print"
        )
        hint.setWordWrap(True)
        root.addWidget(hint)

        # AutoComplete widget
        self.ac = AutoCompleteLineEdit(DATASET)
        root.addWidget(self.ac)

        # Status line
        self.status = QLabel("No item selected.")
        
        root.addWidget(self.status)

        root.addStretch()

        # Connect selection signal to update status label
        self.ac.itemSelected.connect(self._on_item_selected)

        # Style the window
        

    def _on_item_selected(self, item: Optional[Item]):
        if item:
            self.status.setText(
                f"✔  Selected:  <b>{item.name}</b>   (ID: {item.id})"
            )
            
        else:
            self.status.setText("No item selected.")
            


# ──────────────────────────── Entry point ──────────────────────────

def main():
    app = QApplication(sys.argv)


    # Light palette
    palette = QPalette()
    app.setPalette(palette)

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()