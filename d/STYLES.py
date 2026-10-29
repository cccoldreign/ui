#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  QSS TOOLKIT — набор «бери и копируй» для PyQt5                          ║
╚══════════════════════════════════════════════════════════════════════════╝

Запуск витрины:   pip install PyQt5   →   python qss_toolkit.py

КАК ПОЛЬЗОВАТЬСЯ ЭТИМ ФАЙЛОМ
────────────────────────────
Файл разбит на 4 независимых части. Ищите по маркеру  ">>>"  (Ctrl+F):

  ЧАСТЬ 1. QSS — по одному блоку на виджет. Каждый блок — отдельная строка-константа,
           не зависит от других. Скопировал QSS_BUTTON → получил все кнопки.
              >>> QSS_BASE          шрифт, фон окна, убрать пунктир фокуса
              >>> QSS_LABEL         QLabel: заголовки, бейджи, выноски
              >>> QSS_LINEEDIT      QLineEdit (+ варианты)
              >>> QSS_TEXTEDIT      QTextEdit / QPlainTextEdit
              >>> QSS_COMBO_SPIN    QComboBox / QSpinBox / QDateEdit
              >>> QSS_BUTTON        QPushButton (+ варианты, сегмент)
              >>> QSS_GROUPBOX      QGroupBox
              >>> QSS_CHECK_RADIO   QCheckBox / QRadioButton
              >>> QSS_TABLE         QTableWidget / QHeaderView (без рамки фокуса)
              >>> QSS_SCROLLBAR     полосы прокрутки
              >>> QSS_TABS_MISC     вкладки, прогресс, слайдер
              >>> QSS_MENU_TOOLTIP  меню, тулбар, подсказки
              >>> QSS_MESSAGEBOX    QMessageBox
              >>> QSS_MDI           QMdiArea / QMdiSubWindow

  ЧАСТЬ 2. КЛАССЫ — каждый самодостаточный, копируется целиком вместе с импортами,
           указанными в его шапке.
              >>> class BubbleButton     кнопка с «бабл»-эффектом при наведении
              >>> class LiftButton       кнопка, «приподнимающаяся» тенью
              >>> class NoFocusDelegate  убирает рамку фокуса в ячейке таблицы
              >>> class ColorDelegate    цвета ячеек из модели важнее QSS
              >>> class MdiStyle         высота заголовка/рамка у MDI-окна
              >>> def apply_mdi_palette  цвет заголовка MDI-окна
              >>> class WheelGuard       колесо не меняет combo/spin без фокуса

  ЧАСТЬ 3. ВИТРИНА — просто демонстрация. Под каждым примером подписан короткий
           код (какое property поставить / какой класс использовать).
           Функции demo_* можно смело удалять.

ПАЛИТРА (светлая тема) — чтобы сменить цвета, сделайте Найти/Заменить:
  акцент #4F6BED (hover #435DD8, pressed #3A50BF, disabled #B9C4F5, мягкий #E3E9FD, текст на мягком #1F2A6B)
  опасность #E5484D (текст #D13B41, рамка #F1B8BA, фон #FFF8F8)   успех #2FA36B
  фон окна #F3F5F9   карточка/поле #FFFFFF   рамка #DDE2EC / #D3D9E5 / hover #B3BCD0
  текст #1F2937   заголовок #111827   серый #6B7280   светло-серый #9CA3AF
"""
import sys
import math
import sqlite3

from PyQt5.QtCore import (Qt, QObject, QEvent, QVariantAnimation, QEasingCurve,
                          QPointF, QRectF)
from PyQt5.QtGui import QPainter, QColor, QPainterPath, QPalette, QBrush, QCursor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QLineEdit, QTextEdit,
    QPlainTextEdit, QPushButton, QCheckBox, QRadioButton, QGroupBox, QComboBox,
    QSpinBox, QDoubleSpinBox, QDateEdit, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFormLayout, QScrollArea, QMdiArea, QMenu, QTabWidget,
    QProgressBar, QSlider, QButtonGroup, QStyledItemDelegate, QStyle,
    QStyleOptionViewItem, QGraphicsDropShadowEffect, QProxyStyle, QSizePolicy,
)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  ЧАСТЬ 1.  QSS — ПО ОДНОМУ БЛОКУ НА ВИДЖЕТ                               ║
# ╚══════════════════════════════════════════════════════════════════════════╝

# >>> QSS_BASE ───────────────────────────────────────────────────────────────
# Шрифт, цвет текста, фон окон. `* { outline: 0 }` убирает пунктирную рамку
# фокуса у кнопок, чекбоксов, списков и т.д.
QSS_BASE = r"""
* { outline: 0; }
QWidget {
    font-family: "Segoe UI", "Inter", "Roboto", "Helvetica Neue", sans-serif;
    font-size: 13px;
    color: #1F2937;
}
QMainWindow, QDialog { background: #F3F5F9; }
"""

# >>> QSS_LABEL ──────────────────────────────────────────────────────────────
# Использование:
#     lbl.setObjectName("pageTitle")         # по имени
#     lbl.setProperty("role", "error")       # по свойству
#     badge.setObjectName("badge"); badge.setProperty("state", "ok")
QSS_LABEL = r"""
QLabel { background: transparent; padding: 0; }

QLabel#pageTitle    { font-size: 24px; font-weight: 700; color: #111827; }
QLabel#pageSubtitle { color: #6B7280; }
QLabel#formLabel    { color: #6B7280; font-weight: 600; }
QLabel#hint         { color: #9CA3AF; font-size: 12px; }

QLabel[role="error"]   { color: #E5484D; font-size: 12px; }
QLabel[role="link"]    { color: #4F6BED; text-decoration: underline; }
QLabel[role="stat"]    { font-size: 30px; font-weight: 700; color: #111827; }
QLabel[role="mono"]    { font-family: Consolas, "Courier New", monospace; background: #1E2330;
                         color: #D6DEEB; padding: 4px 8px; border-radius: 5px; }
QLabel[role="callout"] { background: #E3E9FD; color: #1F2A6B; border-left: 4px solid #4F6BED;
                         padding: 10px 14px; border-radius: 6px; }
QLabel[role="warn"]    { background: #FFF4D6; color: #8A6100; border-left: 4px solid #8A6100;
                         padding: 10px 14px; border-radius: 6px; }

/* бейдж-«таблетка»: objectName = badge, цвет через state */
QLabel#badge { padding: 2px 10px; border-radius: 10px; font-size: 12px; font-weight: 600;
               background: #EEF1F6; color: #4B5563; }
QLabel#badge[state="ok"]     { background: #E3F6EC; color: #1E7F52; }
QLabel#badge[state="warn"]   { background: #FFF4D6; color: #8A6100; }
QLabel#badge[state="bad"]    { background: #FDE8E9; color: #B42329; }
QLabel#badge[state="accent"] { background: #E3E9FD; color: #1F2A6B; }
QLabel#badge[shape="square"]  { border-radius: 4px; }
QLabel#badge[shape="outline"] { background: transparent; border: 1px solid #B3BCD0; color: #6B7280; }
"""

# >>> QSS_LINEEDIT ──────────────────────────────────────────────────────────
# Высота 32 + padding 0×10 → текст не обрезается (главная причина обрезки —
# вертикальный padding при малой высоте). Варианты:  le.setProperty("variant", "pill")
# Ошибка валидации:  set_prop(le, "invalid", True)   (см. set_prop в части 2)
QSS_LINEEDIT = r"""
QLineEdit {
    background: #FFFFFF;
    border: 1px solid #D3D9E5;
    border-radius: 7px;
    padding: 0px 10px;
    min-height: 32px;
    selection-background-color: #4F6BED;
    selection-color: #FFFFFF;
}
QLineEdit:hover    { border-color: #B3BCD0; }
QLineEdit:focus    { border: 1px solid #4F6BED; }
QLineEdit:read-only{ background: #F3F5F9; color: #6B7280; }
QLineEdit:disabled { background: #F3F5F9; color: #A3ABB9; border-color: #E4E8F0; }
QLineEdit[invalid="true"] { border: 1px solid #E5484D; background: #FFF8F8; }

QLineEdit[variant="filled"]   { background: #EEF1F6; border: 1px solid transparent; }
QLineEdit[variant="filled"]:focus { background: #FFFFFF; border: 1px solid #4F6BED; }
QLineEdit[variant="underline"] { background: transparent; border: none; border-bottom: 2px solid #D3D9E5;
                                 border-radius: 0; padding: 0px 2px; }
QLineEdit[variant="underline"]:focus { border: none; border-bottom: 2px solid #4F6BED; }
QLineEdit[variant="pill"]  { border-radius: 17px; padding: 0px 16px; min-height: 34px; }
QLineEdit[variant="mono"]  { font-family: Consolas, "Courier New", monospace; background: #1E2330;
                             color: #D6DEEB; border: 1px solid #1E2330; }
QLineEdit[variant="mono"]:focus { border: 1px solid #4F6BED; }
QLineEdit[variant="big"]   { font-size: 16px; min-height: 44px; border-radius: 10px; padding: 0 14px; }
"""

# >>> QSS_TEXTEDIT ──────────────────────────────────────────────────────────
# Скрытый отступ документа задаётся из кода:  te.document().setDocumentMargin(4)
QSS_TEXTEDIT = r"""
QTextEdit, QPlainTextEdit {
    background: #FFFFFF;
    border: 1px solid #D3D9E5;
    border-radius: 7px;
    padding: 6px 8px;
    selection-background-color: #4F6BED;
    selection-color: #FFFFFF;
}
QTextEdit:hover, QPlainTextEdit:hover { border-color: #B3BCD0; }
QTextEdit:focus, QPlainTextEdit:focus { border: 1px solid #4F6BED; }
QTextEdit:disabled, QPlainTextEdit:disabled { background: #F3F5F9; color: #A3ABB9; border-color: #E4E8F0; }
QTextEdit[invalid="true"], QPlainTextEdit[invalid="true"] { border: 1px solid #E5484D; background: #FFF8F8; }

QTextEdit[variant="flat"], QPlainTextEdit[variant="flat"] {
    background: transparent; border: none; border-bottom: 2px solid #D3D9E5; border-radius: 0; padding: 4px 2px;
}
QTextEdit[variant="flat"]:focus, QPlainTextEdit[variant="flat"]:focus { border: none; border-bottom: 2px solid #4F6BED; }
QTextEdit[variant="mono"], QPlainTextEdit[variant="mono"] {
    font-family: Consolas, "Courier New", monospace; background: #1E2330; color: #D6DEEB;
    border: 1px solid #1E2330; border-radius: 8px; padding: 10px;
}
QTextEdit[variant="panel"], QPlainTextEdit[variant="panel"] { background: #EEF1F6; border: 1px solid transparent; color: #6B7280; }
QTextEdit[variant="bubble"], QPlainTextEdit[variant="bubble"] { border-radius: 16px; padding: 10px 14px; }
"""

# >>> QSS_COMBO_SPIN ────────────────────────────────────────────────────────
# Варианты те же, что у QLineEdit:  combo.setProperty("variant", "pill")
QSS_COMBO_SPIN = r"""
QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {
    background: #FFFFFF;
    border: 1px solid #D3D9E5;
    border-radius: 7px;
    padding: 0px 10px;
    min-height: 32px;
    selection-background-color: #4F6BED;
    selection-color: #FFFFFF;
}
QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover { border-color: #B3BCD0; }
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus { border: 1px solid #4F6BED; }
QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled {
    background: #F3F5F9; color: #A3ABB9; border-color: #E4E8F0;
}
QComboBox[invalid="true"], QSpinBox[invalid="true"], QDoubleSpinBox[invalid="true"], QDateEdit[invalid="true"] {
    border: 1px solid #E5484D; background: #FFF8F8;
}

QComboBox[variant="filled"], QSpinBox[variant="filled"], QDoubleSpinBox[variant="filled"], QDateEdit[variant="filled"] {
    background: #EEF1F6; border: 1px solid transparent;
}
QComboBox[variant="underline"], QSpinBox[variant="underline"], QDoubleSpinBox[variant="underline"], QDateEdit[variant="underline"] {
    background: transparent; border: none; border-bottom: 2px solid #D3D9E5; border-radius: 0; padding: 0 2px;
}
QComboBox[variant="underline"]:focus, QSpinBox[variant="underline"]:focus,
QDoubleSpinBox[variant="underline"]:focus, QDateEdit[variant="underline"]:focus { border: none; border-bottom: 2px solid #4F6BED; }
QComboBox[variant="pill"], QSpinBox[variant="pill"], QDoubleSpinBox[variant="pill"], QDateEdit[variant="pill"] {
    border-radius: 17px; padding: 0 16px; min-height: 34px;
}

QComboBox::drop-down, QDateEdit::drop-down { border: none; width: 28px; }
QComboBox QAbstractItemView {
    background: #FFFFFF; border: 1px solid #D3D9E5; border-radius: 6px; padding: 4px;
    selection-background-color: #E3E9FD; selection-color: #1F2A6B; outline: 0;
}
QComboBox QAbstractItemView::item { min-height: 28px; padding: 0 8px; border-radius: 4px; }
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
QDateEdit::up-button, QDateEdit::down-button { width: 20px; border: none; background: transparent; }
"""

# >>> QSS_BUTTON ────────────────────────────────────────────────────────────
# Вид:      btn.setProperty("kind", "primary")   # primary|danger|success|outline|ghost|
#                                                # gradient|dark|soft|pill|link|seg
# Размер:   btn.setProperty("sz", "s")           # s | l | sq (квадратная)
# Сегмент:  kind="seg" + pos="first"/"mid"/"last" + setCheckable(True) + QButtonGroup
QSS_BUTTON = r"""
QPushButton {
    background: #FFFFFF; color: #1F2937;
    border: 1px solid #D3D9E5; border-radius: 7px;
    padding: 0px 18px; min-height: 34px; font-weight: 600;
}
QPushButton:hover    { background: #F6F8FC; border-color: #B3BCD0; }
QPushButton:pressed  { background: #EAEEF6; }
QPushButton:focus    { border: 1px solid #4F6BED; }
QPushButton:disabled { background: #F3F5F9; color: #A3ABB9; border-color: #E4E8F0; }
QPushButton:checked  { background: #E3E9FD; color: #1F2A6B; border-color: #4F6BED; }
QPushButton::menu-indicator { subcontrol-position: right center; right: 8px; }

QPushButton[kind="primary"] { background: #4F6BED; border: 1px solid #4F6BED; color: #FFFFFF; }
QPushButton[kind="primary"]:hover    { background: #435DD8; border-color: #435DD8; }
QPushButton[kind="primary"]:pressed  { background: #3A50BF; border-color: #3A50BF; }
QPushButton[kind="primary"]:disabled { background: #B9C4F5; border-color: #B9C4F5; color: #FFFFFF; }

QPushButton[kind="danger"] { background: transparent; border: 1px solid #F1B8BA; color: #D13B41; }
QPushButton[kind="danger"]:hover   { background: #E5484D; border-color: #E5484D; color: #FFFFFF; }
QPushButton[kind="danger"]:pressed { background: #C93A3F; border-color: #C93A3F; color: #FFFFFF; }

QPushButton[kind="success"] { background: #2FA36B; border: 1px solid #2FA36B; color: #FFFFFF; }
QPushButton[kind="success"]:hover { background: #27895A; border-color: #27895A; }

QPushButton[kind="outline"] { background: transparent; border: 1.5px solid #4F6BED; color: #4F6BED; }
QPushButton[kind="outline"]:hover   { background: #4F6BED; color: #FFFFFF; }
QPushButton[kind="outline"]:pressed { background: #3A50BF; color: #FFFFFF; }

QPushButton[kind="ghost"] { background: transparent; border: 1px solid transparent; color: #4F6BED; }
QPushButton[kind="ghost"]:hover   { background: #EDF0FD; }
QPushButton[kind="ghost"]:pressed { background: #DEE4FB; }

QPushButton[kind="gradient"] {
    border: none; color: #FFFFFF;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F6BED, stop:1 #9B5CF6);
}
QPushButton[kind="gradient"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #435DD8, stop:1 #8A48E8);
}

QPushButton[kind="dark"] { background: #1F2937; border: 1px solid #1F2937; color: #FFFFFF; }
QPushButton[kind="dark"]:hover { background: #374151; border-color: #374151; }

QPushButton[kind="soft"] { background: #E3E9FD; border: 1px solid transparent; color: #1F2A6B; }
QPushButton[kind="soft"]:hover { border-color: #4F6BED; }

QPushButton[kind="pill"] { background: #E3E9FD; border: none; color: #1F2A6B; border-radius: 17px; padding: 0 22px; }
QPushButton[kind="pill"]:hover { background: #4F6BED; color: #FFFFFF; }

QPushButton[kind="link"] { background: transparent; border: none; color: #4F6BED; padding: 0 4px; min-height: 24px; }
QPushButton[kind="link"]:hover { text-decoration: underline; }

QPushButton[sz="s"]  { min-height: 26px; padding: 0 12px; font-size: 12px; border-radius: 6px; }
QPushButton[sz="l"]  { min-height: 46px; padding: 0 28px; font-size: 15px; border-radius: 10px; }
QPushButton[sz="sq"] { min-width: 34px; max-width: 34px; padding: 0; font-size: 16px; }

/* сегментированный переключатель */
QPushButton[kind="seg"] { border-radius: 0; border-right-width: 0; padding: 0 18px; }
QPushButton[kind="seg"][pos="first"] { border-top-left-radius: 7px; border-bottom-left-radius: 7px; }
QPushButton[kind="seg"][pos="last"]  { border-top-right-radius: 7px; border-bottom-right-radius: 7px; border-right-width: 1px; }
QPushButton[kind="seg"]:checked { background: #4F6BED; color: #FFFFFF; border-color: #4F6BED; }

QToolButton { background: transparent; border: 1px solid transparent; border-radius: 6px; padding: 5px; }
QToolButton:hover   { background: #EAEEF6; }
QToolButton:checked { background: #E3E9FD; border-color: #C5D0F8; }
"""

# >>> QSS_GROUPBOX ──────────────────────────────────────────────────────────
# ВАЖНО: фон `::title` должен совпадать с цветом того, ЧТО ЗА ГРУППОЙ
# (здесь #FFFFFF — белая карточка). Иначе рамка будет «просвечивать» под заголовком.
# Если заголовок наезжает на рамку — увеличьте margin-top и padding-top.
QSS_GROUPBOX = r"""
QGroupBox {
    background: transparent;
    border: 1px solid #DDE2EC;
    border-radius: 10px;
    margin-top: 16px;
    padding: 18px 14px 14px 14px;
    font-weight: 700;
}
QGroupBox::title {
    subcontrol-origin: margin; subcontrol-position: top left;
    left: 14px; padding: 0 8px;
    color: #4F6BED; background: #FFFFFF;
}
QGroupBox QLabel { font-weight: normal; }
QGroupBox::indicator { width: 16px; height: 16px; }

QGroupBox[variant="center"]::title { subcontrol-position: top center; }
QGroupBox[variant="accent"]  { border: 2px solid #4F6BED; }
QGroupBox[variant="filled"]  { background: #F3F5F9; border: 1px solid transparent; }
QGroupBox[variant="filled"]::title { background: transparent; }
QGroupBox[variant="flat"]    { border: none; border-top: 1px solid #DDE2EC; border-radius: 0; margin-top: 12px; padding-top: 16px; }
QGroupBox[variant="flat"]::title { left: 0; padding: 0 8px 0 0; color: #6B7280; background: #FFFFFF; }
QGroupBox[variant="dashed"]  { border: 1.5px dashed #B3BCD0; }
QGroupBox[variant="danger"]  { border: 1px solid #F1B8BA; }
QGroupBox[variant="danger"]::title { color: #D13B41; }
"""

# >>> QSS_CHECK_RADIO ───────────────────────────────────────────────────────
# Свой индикатор без картинок (залитый квадрат). Для галочки добавьте
#   QCheckBox::indicator:checked { image: url(check.svg); }
QSS_CHECK_RADIO = r"""
QCheckBox, QRadioButton { spacing: 9px; background: transparent; }
QCheckBox:disabled, QRadioButton:disabled { color: #A3ABB9; }

QCheckBox::indicator { width: 18px; height: 18px; border: 1.5px solid #B3BCD0; border-radius: 5px; background: #FFFFFF; }
QCheckBox::indicator:hover   { border-color: #4F6BED; }
QCheckBox::indicator:checked { background: #4F6BED; border-color: #4F6BED; }
QCheckBox::indicator:indeterminate { background: #B9C4F5; border-color: #B9C4F5; }
QCheckBox::indicator:disabled { background: #F3F5F9; border-color: #E4E8F0; }

QCheckBox[variant="round"]::indicator  { width: 20px; height: 20px; border-radius: 10px; }
QCheckBox[variant="big"]::indicator    { width: 24px; height: 24px; border-radius: 7px; }
QCheckBox[variant="ok"]::indicator:checked     { background: #2FA36B; border-color: #2FA36B; }
QCheckBox[variant="danger"]::indicator:checked { background: #E5484D; border-color: #E5484D; }

QRadioButton::indicator { width: 18px; height: 18px; border: 1.5px solid #B3BCD0; border-radius: 10px; background: #FFFFFF; }
QRadioButton::indicator:hover   { border-color: #4F6BED; }
QRadioButton::indicator:checked { border: 5px solid #4F6BED; background: #FFFFFF; }

/* «плитка»: весь контрол выглядит как карточка */
QCheckBox[variant="tile"], QRadioButton[variant="tile"] {
    border: 1.5px solid #DDE2EC; border-radius: 10px; padding: 12px 14px; background: #FFFFFF; font-weight: 600;
}
QCheckBox[variant="tile"]:hover, QRadioButton[variant="tile"]:hover { border-color: #B3BCD0; }
QCheckBox[variant="tile"]:checked, QRadioButton[variant="tile"]:checked {
    border-color: #4F6BED; background: #E3E9FD; color: #1F2A6B;
}
"""

# >>> QSS_TABLE ─────────────────────────────────────────────────────────────
# • `outline: 0` + `::item:focus` — убирают внутреннюю рамку фокуса в ячейке.
#   Для 100% гарантии добавьте ещё NoFocusDelegate (часть 2).
# • Для hover/selected из QSS используйте variant="default".
#   Если нужны цвета ячеек из модели (setBackground) — variant="colors" + ColorDelegate.
# • Варианты:  table.setProperty("variant", "compact|grid|accent|borderless|colors")
QSS_TABLE = r"""
QTableWidget, QTableView {
    background: #FFFFFF;
    alternate-background-color: #F8FAFD;
    border: 1px solid #DDE2EC;
    border-radius: 8px;
    gridline-color: #EBEEF4;
    selection-background-color: #E3E9FD;
    selection-color: #1F2A6B;
    outline: 0;
}
QTableWidget::item, QTableView::item { padding: 4px 10px; border: none; }
QTableWidget::item:focus, QTableView::item:focus { border: none; outline: none; }

QTableWidget[variant="default"]::item:hover    { background: #F0F3FA; }
QTableWidget[variant="default"]::item:selected { background: #E3E9FD; color: #1F2A6B; }
QTableWidget[variant="compact"]::item { padding: 1px 6px; }
QTableWidget[variant="compact"]       { font-size: 12px; }
QTableWidget[variant="grid"]       { border: 1px solid #B3BCD0; gridline-color: #B3BCD0; border-radius: 0; }
QTableWidget[variant="borderless"] { border: none; background: transparent; border-radius: 0; }
QTableWidget[variant="accent"] QHeaderView::section { background: #4F6BED; color: #FFFFFF; border: none; border-right: 1px solid #435DD8; }

/* редактор внутри ячейки (двойной клик) — без обрезки текста */
QTableWidget QLineEdit, QTableView QLineEdit {
    margin: 0; padding: 0px 8px; min-height: 0;
    border: 1px solid #4F6BED; border-radius: 0; background: #FFFFFF;
}

QHeaderView { background: transparent; }
QHeaderView::section {
    background: #F3F5F9; color: #4B5563; padding: 9px 10px; border: none;
    border-bottom: 1px solid #DDE2EC; border-right: 1px solid #EBEEF4;
    font-weight: 700; font-size: 12px;
}
QHeaderView::section:hover { background: #EAEEF6; }
QTableCornerButton::section { background: #F3F5F9; border: none; }
"""

# >>> QSS_SCROLLBAR ─────────────────────────────────────────────────────────
QSS_SCROLLBAR = r"""
QScrollBar:vertical   { background: transparent; width: 12px;  margin: 2px; }
QScrollBar:horizontal { background: transparent; height: 12px; margin: 2px; }
QScrollBar::handle:vertical   { background: #C5CCDB; min-height: 30px; border-radius: 4px; }
QScrollBar::handle:horizontal { background: #C5CCDB; min-width: 30px;  border-radius: 4px; }
QScrollBar::handle:hover { background: #A3ADC2; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }
"""

# >>> QSS_TABS_MISC ─────────────────────────────────────────────────────────
QSS_TABS_MISC = r"""
QTabWidget::pane { background: #FFFFFF; border: 1px solid #DDE2EC; border-radius: 8px; top: -1px; }
QTabBar::tab { background: transparent; color: #6B7280; padding: 9px 18px; margin-right: 2px;
               border: none; border-bottom: 2px solid transparent; font-weight: 600; }
QTabBar::tab:hover:!selected { color: #1F2937; background: #EAEEF6; }
QTabBar::tab:selected { color: #4F6BED; border-bottom: 2px solid #4F6BED; }

QProgressBar { background: #E4E8F0; border: none; border-radius: 5px; min-height: 10px; max-height: 10px; color: transparent; }
QProgressBar::chunk { background: #4F6BED; border-radius: 5px; }

QSlider::groove:horizontal { height: 4px; background: #D3D9E5; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #4F6BED; border-radius: 2px; }
QSlider::handle:horizontal { background: #FFFFFF; border: 2px solid #4F6BED; width: 14px; height: 14px;
                             margin: -7px 0; border-radius: 9px; }
"""

# >>> QSS_MENU_TOOLTIP ──────────────────────────────────────────────────────
QSS_MENU_TOOLTIP = r"""
QMenuBar { background: #FFFFFF; border-bottom: 1px solid #DDE2EC; padding: 2px 6px; }
QMenuBar::item { background: transparent; padding: 6px 12px; border-radius: 6px; }
QMenuBar::item:selected { background: #EAEEF6; }
QMenu { background: #FFFFFF; border: 1px solid #DDE2EC; border-radius: 8px; padding: 6px; }
QMenu::item { padding: 7px 28px 7px 14px; border-radius: 5px; }
QMenu::item:selected { background: #E3E9FD; color: #1F2A6B; }
QMenu::item:disabled { color: #A3ABB9; }
QMenu::separator { height: 1px; background: #EBEEF4; margin: 5px 8px; }
QToolBar { background: #FFFFFF; border: none; border-bottom: 1px solid #DDE2EC; padding: 6px 10px; spacing: 8px; }
QStatusBar { background: #FFFFFF; border-top: 1px solid #DDE2EC; color: #6B7280; }
QToolTip { background: #1F2937; color: #FFFFFF; border: none; border-radius: 5px; padding: 5px 8px; }
"""

# >>> QSS_MESSAGEBOX ────────────────────────────────────────────────────────
# Чтобы окно было шире, задавайте min-width у QLabel (а не у самого QMessageBox).
# Кнопки красятся через QSS_BUTTON: button.setProperty("kind", "danger") до exec_().
QSS_MESSAGEBOX = r"""
QMessageBox, QInputDialog { background: #FFFFFF; }
QMessageBox QLabel { background: transparent; min-width: 320px; font-size: 14px; }
QMessageBox QPushButton, QInputDialog QPushButton { min-width: 92px; }
"""

# >>> QSS_MDI ───────────────────────────────────────────────────────────────
# QSS красит только область и рамку содержимого. Заголовок и кнопки окна рисует
# QStyle → см. MdiStyle и apply_mdi_palette в части 2.
QSS_MDI = r"""
QMdiArea { background: #E9EDF4; border-radius: 8px; }
QMdiSubWindow { background: #F3F5F9; }
"""

# ── Всё вместе (для app.setStyleSheet). Можно оставить только нужные блоки. ──
ALL_QSS = "\n".join([
    QSS_BASE, QSS_LABEL, QSS_LINEEDIT, QSS_TEXTEDIT, QSS_COMBO_SPIN, QSS_BUTTON,
    QSS_GROUPBOX, QSS_CHECK_RADIO, QSS_TABLE, QSS_SCROLLBAR, QSS_TABS_MISC,
    QSS_MENU_TOOLTIP, QSS_MESSAGEBOX, QSS_MDI,
])


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  ЧАСТЬ 2.  КЛАССЫ И ФУНКЦИИ — КАЖДЫЙ САМОДОСТАТОЧНЫЙ                     ║
# ╚══════════════════════════════════════════════════════════════════════════╝

# >>> set_prop ───────────────────────────────────────────────────────────────
# Нужен, когда меняете property уже показанного виджета (например invalid):
#     set_prop(line_edit, "invalid", True)
def set_prop(widget, name, value):
    widget.setProperty(name, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


# >>> class BubbleButton ─────────────────────────────────────────────────────
# Бабл-эффект: круг расходится от точки, где курсор зашёл на кнопку, и сжимается при уходе.
# Импорты: math; QtCore: Qt, QVariantAnimation, QEasingCurve, QPointF, QRectF;
#          QtGui: QPainter, QColor, QPainterPath, QCursor; QtWidgets: QPushButton
# Стиль берётся из QSS_BUTTON как у обычной кнопки.
#   BubbleButton("Сохранить", color="#FFFFFF", alpha=60)   # для цветных кнопок
#   BubbleButton("Отмена",    color="#4F6BED", alpha=35)   # для светлых кнопок
#   radius должен совпадать с border-radius в QSS (у кнопки в QSS_BUTTON это 7)
class BubbleButton(QPushButton):
    def __init__(self, text="", color="#FFFFFF", alpha=50, radius=7, parent=None):
        super().__init__(text, parent)
        self._r = 0.0
        self._center = QPointF()
        self._corner = radius
        self._color = QColor(color)
        self._color.setAlpha(alpha)
        self.setCursor(Qt.PointingHandCursor)
        self._anim = QVariantAnimation(self)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._set_r)

    def _set_r(self, v):
        self._r = float(v)
        self.update()

    def _max_r(self):
        w, h, c = self.width(), self.height(), self._center
        return max(math.hypot(c.x() - x, c.y() - y) for x, y in ((0, 0), (w, 0), (0, h), (w, h)))

    def _run(self, end, ms):
        self._anim.stop()
        self._anim.setDuration(ms)
        self._anim.setStartValue(self._r)
        self._anim.setEndValue(end)
        self._anim.start()

    def enterEvent(self, e):
        self._center = QPointF(self.mapFromGlobal(QCursor.pos()))
        self._run(self._max_r(), 450)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._run(0.0, 300)
        super().leaveEvent(e)

    def paintEvent(self, e):
        super().paintEvent(e)                    # обычный вид кнопки из QSS
        if self._r <= 0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()), self._corner, self._corner)
        p.setClipPath(clip)                      # круг не вылезает за скругления
        p.setPen(Qt.NoPen)
        p.setBrush(self._color)
        p.drawEllipse(self._center, self._r, self._r)


# >>> class LiftButton ───────────────────────────────────────────────────────
# Кнопка «приподнимается»: при наведении плавно растёт тень.
# Импорты: QtCore: Qt, QVariantAnimation; QtGui: QColor;
#          QtWidgets: QPushButton, QGraphicsDropShadowEffect
#   LiftButton("Текст")            # не используйте внутри ячеек таблицы (артефакты)
class LiftButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._sh = QGraphicsDropShadowEffect(self)
        self._sh.setColor(QColor(0, 0, 0, 80))
        self._sh.setOffset(0, 0)
        self._sh.setBlurRadius(0)
        self.setGraphicsEffect(self._sh)
        self._a = QVariantAnimation(self)
        self._a.setDuration(200)
        self._a.valueChanged.connect(self._tick)
        self.setCursor(Qt.PointingHandCursor)

    def _tick(self, v):
        self._sh.setBlurRadius(float(v))
        self._sh.setOffset(0, float(v) / 4)

    def _go(self, end):
        self._a.stop()
        self._a.setStartValue(self._sh.blurRadius())
        self._a.setEndValue(end)
        self._a.start()

    def enterEvent(self, e):
        self._go(20)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._go(0)
        super().leaveEvent(e)


# >>> class NoFocusDelegate ──────────────────────────────────────────────────
# Убирает внутреннюю рамку фокуса вокруг текста ячейки (гарантированно).
# Импорты: QtWidgets: QStyledItemDelegate, QStyle
#   table.setItemDelegate(NoFocusDelegate(table))
class NoFocusDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        option.state &= ~QStyle.State_HasFocus
        super().paint(painter, option, index)


# >>> class ColorDelegate ────────────────────────────────────────────────────
# Цвета из модели (item.setBackground / setForeground) имеют приоритет над QSS;
# заодно сам рисует hover и выделение. Таблице поставьте variant="colors"
# (в QSS_TABLE для него нет ::item:hover/selected) и table.setMouseTracking(True).
# Импорты: QtGui: QColor, QBrush, QPalette; QtWidgets: QStyledItemDelegate, QStyle, QStyleOptionViewItem
#   table.setItemDelegate(ColorDelegate(table, hover="#F0F3FA", selected="#E3E9FD", sel_text="#1F2A6B"))
class ColorDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, hover="#F0F3FA", selected="#E3E9FD", sel_text="#1F2A6B"):
        super().__init__(parent)
        self.hover, self.selected, self.sel_text = QColor(hover), QColor(selected), QColor(sel_text)

    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        is_sel = bool(opt.state & QStyle.State_Selected)
        is_hov = bool(opt.state & QStyle.State_MouseOver)
        bg = index.data(Qt.BackgroundRole)
        if is_sel:
            painter.fillRect(opt.rect, self.selected)
        elif bg is not None:
            painter.fillRect(opt.rect, bg.color() if isinstance(bg, QBrush) else QColor(bg))
        elif is_hov:
            painter.fillRect(opt.rect, self.hover)
        opt.backgroundBrush = QBrush(Qt.NoBrush)
        opt.state &= ~(QStyle.State_Selected | QStyle.State_MouseOver | QStyle.State_HasFocus)
        if is_sel:
            opt.palette.setColor(QPalette.Text, self.sel_text)
        super().paint(painter, opt, index)


# >>> class MdiStyle  +  def apply_mdi_palette ───────────────────────────────
# Заголовок MDI-окна рисует стиль, а не QSS:
#   • высота заголовка и толщина рамки — QProxyStyle (MdiStyle)
#   • цвет активного заголовка — QPalette.Highlight (стиль должен быть Fusion)
# Импорты: QtGui: QPalette, QColor; QtWidgets: QProxyStyle, QStyle
#   app.setStyle(MdiStyle("Fusion"))
#   apply_mdi_palette(app, active="#4F6BED")
# Кнопки окна:  sub.setWindowFlags(Qt.SubWindow | Qt.CustomizeWindowHint |
#                                  Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
class MdiStyle(QProxyStyle):
    TITLE_HEIGHT = 30
    FRAME_WIDTH = 3

    def pixelMetric(self, metric, option=None, widget=None):
        if metric == QStyle.PM_TitleBarHeight:
            return self.TITLE_HEIGHT
        if metric == QStyle.PM_MdiSubWindowFrameWidth:
            return self.FRAME_WIDTH
        return super().pixelMetric(metric, option, widget)


def apply_mdi_palette(app, active="#4F6BED", window="#F3F5F9", text="#1F2937"):
    pal = app.palette()
    pal.setColor(QPalette.Window, QColor(window))
    pal.setColor(QPalette.WindowText, QColor(text))
    pal.setColor(QPalette.Highlight, QColor(active))          # активный заголовок
    pal.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(pal)


# >>> class WheelGuard ───────────────────────────────────────────────────────
# Внутри QScrollArea колесо мыши случайно меняет значения combo/spin.
# Фильтр блокирует колесо, пока виджет не в фокусе.
# Импорты: QtCore: Qt, QObject, QEvent
#   guard = WheelGuard(); combo.setFocusPolicy(Qt.StrongFocus); combo.installEventFilter(guard)
class WheelGuard(QObject):
    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Wheel and not obj.hasFocus():
            ev.ignore()
            return True
        return False


_WHEEL = WheelGuard()


def guard_wheel(widget):
    widget.setFocusPolicy(Qt.StrongFocus)
    widget.installEventFilter(_WHEEL)
    return widget


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  ЧАСТЬ 3.  ВИТРИНА (только демонстрация — можно удалять целиком)         ║
# ╚══════════════════════════════════════════════════════════════════════════╝
# Здесь используются: ALL_QSS + классы выше. Под каждым примером подписан
# код, который нужно взять. Стили карточек ниже нужны только витрине.

QSS_DEMO_ONLY = r"""
#demoPage { background: #F3F5F9; }
#card { background: #FFFFFF; border: 1px solid #DDE2EC; border-radius: 12px; }
QLabel#sectionTitle { font-size: 17px; font-weight: 700; color: #111827; }
QLabel#takeLine { color: #435DD8; font-family: Consolas, "Courier New", monospace; font-size: 12px;
                  background: #EDF0FD; border-radius: 5px; padding: 4px 8px; }
QLabel#demoCode { color: #9CA3AF; font-family: Consolas, "Courier New", monospace; font-size: 11px; }
QScrollArea { border: none; background: transparent; }
"""


def demo_label(text, obj=None, role=None, wrap=False):
    lb = QLabel(text)
    if obj:
        lb.setObjectName(obj)
    if role:
        lb.setProperty("role", role)
    lb.setWordWrap(wrap)
    return lb


def demo_item(widget, code):
    """Виджет + подпись «как это сделано»."""
    box = QWidget()
    v = QVBoxLayout(box)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(4)
    v.addWidget(widget)
    c = demo_label(code, "demoCode", wrap=True)
    v.addWidget(c)
    return box


def demo_grid(items, cols=3):
    g = QGridLayout()
    g.setHorizontalSpacing(16)
    g.setVerticalSpacing(14)
    for i, w in enumerate(items):
        g.addWidget(w, i // cols, i % cols)
    for c in range(cols):
        g.setColumnStretch(c, 1)
    return g


def demo_section(title, take):
    card = QFrame()
    card.setObjectName("card")
    card.setAttribute(Qt.WA_StyledBackground, True)
    lay = QVBoxLayout(card)
    lay.setContentsMargins(22, 20, 22, 22)
    lay.setSpacing(14)
    lay.addWidget(demo_label(title, "sectionTitle"))
    lay.addWidget(demo_label("ЧТО БРАТЬ:  " + take, "takeLine", wrap=True))
    return card, lay


# ---------------------------- QLabel ----------------------------
def demo_labels():
    card, lay = demo_section("QLabel", "QSS_LABEL")
    for text, obj, role, code in [
        ("Заголовок страницы", "pageTitle", None, 'setObjectName("pageTitle")'),
        ("Подзаголовок — серый вспомогательный текст", "pageSubtitle", None, 'setObjectName("pageSubtitle")'),
        ("Подпись поля", "formLabel", None, 'setObjectName("formLabel")'),
        ("Подсказка под полем", "hint", None, 'setObjectName("hint")'),
        ("Текст ошибки", None, "error", 'setProperty("role", "error")'),
        ("Ссылка", None, "link", 'setProperty("role", "link")'),
        ("Информационная выноска: данные сохранены.", None, "callout", 'setProperty("role", "callout")'),
        ("Предупреждение: запись изменена другим пользователем.", None, "warn", 'setProperty("role", "warn")'),
    ]:
        lay.addWidget(demo_item(demo_label(text, obj, role, wrap=True), code))

    row = QHBoxLayout()
    for text, st, shape in [("Активен", "ok", None), ("Ожидает", "warn", None), ("Заблокирован", "bad", None),
                            ("Новый", "accent", None), ("Архив", None, None), ("Квадрат", "accent", "square"),
                            ("Контур", None, "outline")]:
        b = QLabel(text)
        b.setObjectName("badge")
        if st:
            b.setProperty("state", st)
        if shape:
            b.setProperty("shape", shape)
        row.addWidget(b)
    row.addStretch()
    w = QWidget()
    w.setLayout(row)
    lay.addWidget(demo_item(w, 'setObjectName("badge");  setProperty("state","ok|warn|bad|accent");  setProperty("shape","square|outline")'))
    return card


# ---------------------------- QPushButton ----------------------------
def demo_buttons(win):
    card, lay = demo_section("QPushButton", "QSS_BUTTON   (+ BubbleButton / LiftButton для анимации)")
    items = []
    for text, kind in [("Обычная", None), ("Основная", "primary"), ("Опасная", "danger"), ("Успех", "success"),
                       ("Контур", "outline"), ("Ghost", "ghost"), ("Градиент", "gradient"), ("Тёмная", "dark"),
                       ("Мягкая", "soft"), ("Pill", "pill"), ("Ссылка", "link")]:
        b = QPushButton(text)
        b.setCursor(Qt.PointingHandCursor)
        code = "QPushButton(...)"
        if kind:
            b.setProperty("kind", kind)
            code = f'setProperty("kind", "{kind}")'
        items.append(demo_item(b, code))
    lay.addLayout(demo_grid(items, 4))

    sizes = []
    for text, sz in [("Малая", "s"), ("Большая", "l")]:
        b = QPushButton(text)
        b.setProperty("kind", "primary")
        b.setProperty("sz", sz)
        sizes.append(demo_item(b, f'setProperty("sz", "{sz}")'))
    for sym in ("✚", "✎"):
        b = QPushButton(sym)
        b.setProperty("sz", "sq")
        sizes.append(demo_item(b, 'setProperty("sz", "sq")'))
    lay.addLayout(demo_grid(sizes, 4))

    seg = QHBoxLayout()
    seg.setSpacing(0)
    grp = QButtonGroup(card)
    for i, (t, pos) in enumerate([("День", "first"), ("Неделя", "mid"), ("Месяц", "mid"), ("Год", "last")]):
        b = QPushButton(t)
        b.setCheckable(True)
        b.setProperty("kind", "seg")
        b.setProperty("pos", pos)
        b.setChecked(i == 1)
        grp.addButton(b)
        seg.addWidget(b)
    seg.addStretch()
    w = QWidget()
    w.setLayout(seg)
    lay.addWidget(demo_item(w, 'kind="seg" + pos="first|mid|last" + setCheckable(True) + QButtonGroup'))

    d = QPushButton("Отключена")
    d.setProperty("kind", "primary")
    d.setEnabled(False)
    tg = QPushButton("Переключаемая")
    tg.setCheckable(True)
    tg.setChecked(True)
    ic = QPushButton(" С иконкой")
    ic.setIcon(win.style().standardIcon(QStyle.SP_DialogApplyButton))
    mn = QPushButton("С меню")
    menu = QMenu(mn)
    menu.addAction("Экспорт в CSV")
    menu.addAction("Экспорт в PDF")
    mn.setMenu(menu)
    lay.addLayout(demo_grid([demo_item(d, "setEnabled(False)"), demo_item(tg, "setCheckable(True)"),
                             demo_item(ic, "setIcon(...)"), demo_item(mn, "setMenu(QMenu)")], 4))
    return card


def demo_animated_buttons():
    card, lay = demo_section("Анимированные кнопки", "class BubbleButton  /  class LiftButton   (+ QSS_BUTTON)")
    b1 = BubbleButton("Bubble основная", color="#FFFFFF", alpha=60)
    b1.setProperty("kind", "primary")
    b2 = BubbleButton("Bubble светлая", color="#4F6BED", alpha=35)
    b3 = BubbleButton("Bubble опасная", color="#E5484D", alpha=45)
    b3.setProperty("kind", "danger")
    b4 = LiftButton("Lift (тень)")
    b5 = LiftButton("Lift основная")
    b5.setProperty("kind", "primary")
    lay.addLayout(demo_grid([
        demo_item(b1, 'BubbleButton("…", color="#FFFFFF", alpha=60) + kind="primary"'),
        demo_item(b2, 'BubbleButton("…", color="#4F6BED", alpha=35)'),
        demo_item(b3, 'BubbleButton("…", color="#E5484D", alpha=45) + kind="danger"'),
        demo_item(b4, 'LiftButton("…")'),
        demo_item(b5, 'LiftButton("…") + kind="primary"'),
    ], 3))
    return card


# ---------------------------- QLineEdit ----------------------------
def demo_lineedit():
    card, lay = demo_section("QLineEdit", "QSS_LINEEDIT   (+ set_prop для ошибки)")
    items = []

    def add(variant=None, text="", ph="", code="", **kw):
        e = QLineEdit(text)
        e.setPlaceholderText(ph)
        if variant:
            e.setProperty("variant", variant)
            code = f'setProperty("variant", "{variant}")'
        if kw.get("ro"):
            e.setReadOnly(True)
        if kw.get("dis"):
            e.setEnabled(False)
        if kw.get("bad"):
            e.setProperty("invalid", True)
        if kw.get("clear"):
            e.setClearButtonEnabled(True)
        if kw.get("pwd"):
            e.setEchoMode(QLineEdit.Password)
        items.append(demo_item(e, code))
        return e

    add(ph="Обычное", code="QLineEdit()")
    add(text="С текстом", clear=True, code="setClearButtonEnabled(True)")
    add("filled", ph="Filled")
    add("underline", ph="Underline")
    add("pill", ph="🔍  Pill")
    add("mono", text="SELECT * FROM t")
    add("big", ph="Big")
    add(text="secret", pwd=True, code="setEchoMode(QLineEdit.Password)")
    add(text="ошибка", bad=True, code='setProperty("invalid", True)  # или set_prop(...)')
    add(text="Только чтение", ro=True, code="setReadOnly(True)")
    add(text="Отключено", dis=True, code="setEnabled(False)")
    add(ph="+7 (___) ___-__-__", code='setInputMask("+7 (000) 000-00-00;_")').setInputMask("+7 (000) 000-00-00;_")
    lay.addLayout(demo_grid(items, 3))
    return card


# ---------------------------- QTextEdit ----------------------------
def demo_textedit():
    card, lay = demo_section("QTextEdit / QPlainTextEdit", "QSS_TEXTEDIT")
    items = []

    def add(variant=None, text="", ph="", mono=False, ro=False, h=90):
        t = QPlainTextEdit() if mono else QTextEdit()
        if variant:
            t.setProperty("variant", variant)
        t.setPlaceholderText(ph)
        if text:
            t.setPlainText(text)
        t.setReadOnly(ro)
        t.setFixedHeight(h)
        code = f'setProperty("variant", "{variant}")' if variant else "QTextEdit()"
        items.append(demo_item(t, code))

    add(ph="Комментарий…")
    add("flat", ph="Только нижняя линия", h=60)
    add("mono", text="def hello():\n    print('Привет')", mono=True)
    add("panel", text="Служебное поле только для чтения.", ro=True)
    add("bubble", ph="Сообщение…", h=60)
    lay.addLayout(demo_grid(items, 3))
    return card


# ---------------------------- Combo / Spin / Date ----------------------------
def demo_combo():
    card, lay = demo_section("QComboBox / QSpinBox / QDateEdit", "QSS_COMBO_SPIN   (+ WheelGuard внутри прокрутки)")
    items = []
    for variant in (None, "filled", "underline", "pill", "invalid"):
        c = guard_wheel(QComboBox())
        c.addItems(["Москва", "Санкт-Петербург", "Казань"])
        if variant == "invalid":
            c.setProperty("invalid", True)
            code = 'setProperty("invalid", True)'
        elif variant:
            c.setProperty("variant", variant)
            code = f'setProperty("variant", "{variant}")'
        else:
            code = "QComboBox()"
        items.append(demo_item(c, code))
    s = guard_wheel(QSpinBox())
    s.setValue(42)
    items.append(demo_item(s, "QSpinBox()"))
    s2 = guard_wheel(QDoubleSpinBox())
    s2.setValue(12.5)
    s2.setProperty("variant", "filled")
    items.append(demo_item(s2, 'QDoubleSpinBox(), variant="filled"'))
    d = guard_wheel(QDateEdit())
    d.setCalendarPopup(True)
    d.setDate(d.date().currentDate())
    items.append(demo_item(d, "QDateEdit(), setCalendarPopup(True)"))
    lay.addLayout(demo_grid(items, 3))
    return card


# ---------------------------- Check / Radio ----------------------------
def demo_checks():
    card, lay = demo_section("QCheckBox / QRadioButton", "QSS_CHECK_RADIO")
    items = []
    for text, variant, chk in [("Обычный", None, True), ("Круглый", "round", True), ("Крупный", "big", True),
                               ("Зелёный", "ok", True), ("Красный", "danger", True), ("Не отмечен", None, False)]:
        c = QCheckBox(text)
        c.setChecked(chk)
        if variant:
            c.setProperty("variant", variant)
        items.append(demo_item(c, f'setProperty("variant", "{variant}")' if variant else "QCheckBox()"))
    c3 = QCheckBox("Частично")
    c3.setTristate(True)
    c3.setCheckState(Qt.PartiallyChecked)
    items.append(demo_item(c3, "setTristate(True)"))
    cd = QCheckBox("Отключён")
    cd.setChecked(True)
    cd.setEnabled(False)
    items.append(demo_item(cd, "setEnabled(False)"))
    lay.addLayout(demo_grid(items, 4))

    rb = QHBoxLayout()
    g = QButtonGroup(card)
    for i, t in enumerate(["Вариант A", "Вариант B", "Вариант C"]):
        r = QRadioButton(t)
        r.setChecked(i == 1)
        g.addButton(r)
        rb.addWidget(r)
    rb.addStretch()
    w = QWidget()
    w.setLayout(rb)
    lay.addWidget(demo_item(w, "QRadioButton + QButtonGroup"))

    tiles = QHBoxLayout()
    for t, chk in [("📧  E-mail", True), ("📱  SMS", False), ("🔔  Push", True)]:
        c = QCheckBox(t)
        c.setProperty("variant", "tile")
        c.setChecked(chk)
        tiles.addWidget(c)
    w = QWidget()
    w.setLayout(tiles)
    lay.addWidget(demo_item(w, 'QCheckBox: setProperty("variant", "tile")'))

    rt = QHBoxLayout()
    g2 = QButtonGroup(card)
    for i, t in enumerate(["Базовый — 0 ₽", "Стандарт — 490 ₽", "Про — 990 ₽"]):
        r = QRadioButton(t)
        r.setProperty("variant", "tile")
        r.setChecked(i == 1)
        g2.addButton(r)
        rt.addWidget(r)
    w = QWidget()
    w.setLayout(rt)
    lay.addWidget(demo_item(w, 'QRadioButton: setProperty("variant", "tile")'))
    return card


# ---------------------------- QGroupBox ----------------------------
def demo_groupbox():
    card, lay = demo_section("QGroupBox", "QSS_GROUPBOX   (фон ::title = цвет родителя)")
    items = []
    for title, variant, checkable in [("Обычная", None, False), ("По центру", "center", False),
                                      ("Акцентная", "accent", False), ("Залитая", "filled", False),
                                      ("Flat", "flat", False), ("Пунктир", "dashed", False),
                                      ("С чекбоксом", None, True), ("Опасная зона", "danger", False)]:
        g = QGroupBox(title)
        if variant:
            g.setProperty("variant", variant)
        if checkable:
            g.setCheckable(True)
            g.setChecked(True)
        v = QVBoxLayout(g)
        e = QLineEdit()
        e.setPlaceholderText("Поле внутри")
        v.addWidget(e)
        code = f'variant="{variant}"' if variant else ("setCheckable(True)" if checkable else "QGroupBox()")
        items.append(demo_item(g, code))
    lay.addLayout(demo_grid(items, 4))
    return card


# ---------------------------- QTableWidget ----------------------------
ROWS = [
    (1, "Анна Лебедева",  "+7 900 111-22-33", "anna@mail.ru",   "Активен"),
    (2, "Игорь Смирнов",  "+7 911 222-33-44", "igor@corp.ru",   "Ожидает"),
    (3, "Мария Ковалёва", "+7 922 333-44-55", "maria@site.com", "Заблокирован"),
    (4, "Пётр Орлов",     "+7 933 444-55-66", "petr@mail.ru",   "Активен"),
    (5, "Елена Фролова",  "+7 944 555-66-77", "elena@corp.ru",  "Ожидает"),
]
_STATE = {"Активен": "ok", "Ожидает": "warn", "Заблокирован": "bad"}
_BG = {"Активен": "#E3F6EC", "Ожидает": "#FFF4D6", "Заблокирован": "#FDE8E9"}
_FG = {"Активен": "#1E7F52", "Ожидает": "#8A6100", "Заблокирован": "#B42329"}


def _centered(widget):
    box = QWidget()
    lay = QHBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setAlignment(Qt.AlignCenter)
    lay.addWidget(widget)
    return box


def _table(variant="default", mode="plain", zebra=True, grid=False, row_h=36):
    t = QTableWidget(len(ROWS), 5)
    t.setProperty("variant", variant)
    t.setHorizontalHeaderLabels(["ID", "Имя", "Телефон", "E-mail", "Статус"])
    t.verticalHeader().setVisible(False)
    t.verticalHeader().setDefaultSectionSize(row_h)
    t.horizontalHeader().setFixedHeight(38)
    t.horizontalHeader().setHighlightSections(False)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    t.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.SingleSelection)
    t.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed
                      if mode == "edit" else QAbstractItemView.NoEditTriggers)
    t.setAlternatingRowColors(zebra)
    t.setShowGrid(grid)
    t.setMouseTracking(True)
    t.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    t.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    t.setItemDelegate(NoFocusDelegate(t))
    for r, row in enumerate(ROWS):
        for c, val in enumerate(row):
            it = QTableWidgetItem(str(val))
            if c == 0:
                it.setTextAlignment(Qt.AlignCenter)
            if mode == "colors" and c == 4:
                it.setBackground(QColor(_BG[row[4]]))
                it.setForeground(QColor(_FG[row[4]]))
                it.setTextAlignment(Qt.AlignCenter)
            t.setItem(r, c, it)
    if mode == "colors":
        t.setItemDelegate(ColorDelegate(t))
    if mode == "badges":
        t.setHorizontalHeaderLabels(["✓", "Имя", "Телефон", "E-mail", "Статус"])
        for r, row in enumerate(ROWS):
            cb = QCheckBox()
            cb.setChecked(r % 2 == 0)
            t.setCellWidget(r, 0, _centered(cb))
            t.item(r, 0).setText("")
            b = QLabel(row[4])
            b.setObjectName("badge")
            b.setProperty("state", _STATE[row[4]])
            t.setCellWidget(r, 4, _centered(b))
            t.item(r, 4).setText("")
    t.setFixedHeight(38 + row_h * len(ROWS) + 4)
    return t


def demo_tables():
    card, lay = demo_section("QTableWidget",
                             "QSS_TABLE   (+ NoFocusDelegate;  для цветов ячеек — ColorDelegate;  бейджи — QSS_LABEL)")
    for cap, t in [
        ('default: table.setProperty("variant","default")  — hover и выделение из QSS', _table("default")),
        ('compact: variant="compact", setDefaultSectionSize(26)', _table("compact", row_h=26)),
        ('grid: variant="grid", setShowGrid(True), без зебры', _table("grid", zebra=False, grid=True)),
        ('accent: variant="accent" — цветная шапка', _table("accent", zebra=False)),
        ('colors: variant="colors" + setItemDelegate(ColorDelegate(table)) — цвета модели важнее QSS',
         _table("colors", mode="colors", zebra=False)),
        ('badges: table.setCellWidget(row, col, QLabel#badge / QCheckBox)', _table("default", mode="badges")),
        ('edit: setEditTriggers(DoubleClicked) — двойной клик по ячейке', _table("default", mode="edit")),
        ('borderless: variant="borderless"', _table("borderless", zebra=False)),
    ]:
        lay.addWidget(demo_item(t, cap))
    return card


def demo_misc():
    card, lay = demo_section("Вкладки / прогресс / слайдер", "QSS_TABS_MISC")
    tabs = QTabWidget()
    for name in ("Основное", "Контакты", "История"):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel(f"Вкладка «{name}»"))
        v.addStretch()
        tabs.addTab(w, name)
    tabs.setFixedHeight(120)
    lay.addWidget(tabs)
    pb = QProgressBar()
    pb.setValue(64)
    lay.addWidget(pb)
    sl = QSlider(Qt.Horizontal)
    sl.setValue(40)
    lay.addWidget(sl)
    return card


# ---------------------------- QMessageBox ----------------------------
def demo_messagebox(win):
    card, lay = demo_section("QMessageBox", "QSS_MESSAGEBOX + QSS_BUTTON  (кнопкам: setProperty(\"kind\", ...) до exec_())")

    def show(icon, title, text, info, buttons, details=""):
        box = QMessageBox(win)
        box.setIcon(icon)
        box.setWindowTitle(title)
        box.setText(text)
        box.setInformativeText(info)
        if details:
            box.setDetailedText(details)
        made = []
        for caption, role, kind in buttons:
            b = box.addButton(caption, role)
            if kind:
                b.setProperty("kind", kind)
            made.append(b)
        box.setDefaultButton(made[-1] if buttons[-1][1] == QMessageBox.RejectRole else made[0])
        box.exec_()

    acts = [
        ("Информация", "primary", lambda: show(QMessageBox.Information, "Готово", "Данные сохранены.",
                                               "Изменения видны всем.", [("Понятно", QMessageBox.AcceptRole, "primary")])),
        ("Предупреждение", None, lambda: show(QMessageBox.Warning, "Внимание", "Запись изменена другим пользователем.",
                                              "Перезаписать?", [("Перезаписать", QMessageBox.AcceptRole, "danger"),
                                                                ("Отмена", QMessageBox.RejectRole, None)])),
        ("Вопрос (удаление)", "danger", lambda: show(QMessageBox.Question, "Удаление", "Удалить запись?",
                                                    "Действие нельзя отменить.",
                                                    [("Удалить", QMessageBox.DestructiveRole, "danger"),
                                                     ("Оставить", QMessageBox.RejectRole, "primary")])),
        ("Ошибка + детали", None, lambda: show(QMessageBox.Critical, "Ошибка", "Не удалось подключиться к БД.",
                                               "Проверьте сеть.", [("Повторить", QMessageBox.AcceptRole, "primary"),
                                                                   ("Закрыть", QMessageBox.RejectRole, None)],
                                               details="sqlite3.OperationalError: unable to open database file")),
    ]
    row = QHBoxLayout()
    for text, kind, fn in acts:
        b = QPushButton(text)
        if kind:
            b.setProperty("kind", kind)
        b.clicked.connect(fn)
        row.addWidget(b)
    row.addStretch()
    lay.addLayout(row)
    return card


# ---------------------------- MDI ----------------------------
class _MdiDemo(QWidget):
    def __init__(self):
        super().__init__()
        self.n = 0
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        self.mdi = QMdiArea()
        self.mdi.setMinimumHeight(340)
        bar = QHBoxLayout()
        for text, kind, fn in [("Новое окно", "primary", lambda: self.add("full")),
                               ("Только «закрыть»", None, lambda: self.add("close")),
                               ("Фикс. размер", None, lambda: self.add("fixed")),
                               ("Каскад", "ghost", lambda: self.mdi.cascadeSubWindows()),
                               ("Плитка", "ghost", lambda: self.mdi.tileSubWindows())]:
            b = QPushButton(text)
            if kind:
                b.setProperty("kind", kind)
            b.clicked.connect(fn)
            bar.addWidget(b)
        bar.addStretch()
        v.addLayout(bar)
        v.addWidget(self.mdi)
        self.add("full")
        self.add("close")

    def add(self, kind):
        self.n += 1
        w = QWidget()
        f = QFormLayout(w)
        f.setContentsMargins(16, 16, 16, 16)
        e = QLineEdit()
        e.setPlaceholderText("Имя")
        f.addRow(demo_label("Имя", "formLabel"), e)
        f.addRow("", QCheckBox("Получать рассылку"))
        ok = QPushButton("Сохранить")
        ok.setProperty("kind", "primary")
        f.addRow("", ok)
        sub = self.mdi.addSubWindow(w)
        sub.setWindowTitle(f"Окно {self.n}")
        if kind in ("close", "fixed"):
            sub.setWindowFlags(Qt.SubWindow | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        if kind == "fixed":
            sub.setFixedSize(300, 190)
        else:
            sub.resize(320, 190)
        off = 26 * ((self.n - 1) % 7)
        sub.move(off + 8, off + 8)
        sub.setAttribute(Qt.WA_DeleteOnClose)
        sub.show()


def demo_mdi():
    card, lay = demo_section("QMdiArea / QMdiSubWindow", "QSS_MDI + class MdiStyle + apply_mdi_palette")
    lay.addWidget(_MdiDemo())
    return card


# ---------------------------- Форма БД (пример приложения) ----------------------------
class _DbDemo(QWidget):
    """Список + карточка редактирования. Это не стиль, а пример использования."""
    def __init__(self):
        super().__init__()
        self.db = sqlite3.connect(":memory:")
        self.db.execute("""CREATE TABLE clients(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
                           phone TEXT, email TEXT, note TEXT, status TEXT DEFAULT 'Активен', vip INTEGER DEFAULT 0)""")
        for r in ROWS:
            self.db.execute("INSERT INTO clients(name,phone,email,status) VALUES(?,?,?,?)", (r[1], r[2], r[3], r[4]))
        self.db.commit()
        self.cur_id = None

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(18)

        left = QVBoxLayout()
        self.search = QLineEdit()
        self.search.setProperty("variant", "pill")
        self.search.setPlaceholderText("🔍  Поиск по имени…")
        self.search.textChanged.connect(self.reload)
        left.addWidget(self.search)
        self.table = QTableWidget(0, 4)
        self.table.setProperty("variant", "default")
        self.table.setHorizontalHeaderLabels(["ID", "Имя", "E-mail", "Статус"])
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.horizontalHeader().setFixedHeight(38)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setMouseTracking(True)
        self.table.setItemDelegate(NoFocusDelegate(self.table))
        self.table.setMinimumHeight(330)
        self.table.itemSelectionChanged.connect(self.on_select)
        left.addWidget(self.table, 1)
        root.addLayout(left, 3)

        self.box = QGroupBox("Карточка клиента")
        form = QFormLayout(self.box)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)
        self.f_name = QLineEdit()
        self.f_name.setPlaceholderText("Имя *")
        self.f_phone = QLineEdit()
        self.f_phone.setInputMask("+7 (000) 000-00-00;_")
        self.f_email = QLineEdit()
        self.f_email.setPlaceholderText("name@example.com")
        self.f_status = guard_wheel(QComboBox())
        self.f_status.addItems(["Активен", "Ожидает", "Заблокирован"])
        self.f_vip = QCheckBox("VIP-клиент")
        self.f_note = QTextEdit()
        self.f_note.setFixedHeight(80)
        self.err = demo_label("", role="error")
        for cap, w in [("Имя", self.f_name), ("Телефон", self.f_phone), ("E-mail", self.f_email),
                       ("Статус", self.f_status), ("", self.f_vip), ("Заметка", self.f_note)]:
            form.addRow(demo_label(cap, "formLabel") if cap else QLabel(""), w)
        form.addRow("", self.err)
        self.btn_new = QPushButton("Новая")
        self.btn_del = QPushButton("Удалить")
        self.btn_del.setProperty("kind", "danger")
        self.btn_save = QPushButton("Сохранить")
        self.btn_save.setProperty("kind", "primary")
        self.btn_new.clicked.connect(self.new)
        self.btn_del.clicked.connect(self.delete)
        self.btn_save.clicked.connect(self.save)
        btns = QHBoxLayout()
        btns.addWidget(self.btn_del)
        btns.addStretch()
        btns.addWidget(self.btn_new)
        btns.addWidget(self.btn_save)
        form.addRow(btns)
        right = QVBoxLayout()
        right.addWidget(self.box)
        right.addStretch()
        root.addLayout(right, 2)

        self.reload()
        self.table.selectRow(0)

    def reload(self):
        q = self.search.text().strip()
        rows = self.db.execute("SELECT id,name,email,status FROM clients WHERE name LIKE ? ORDER BY id",
                               (f"%{q}%",)).fetchall()
        self.table.blockSignals(True)
        self.table.setRowCount(len(rows))
        for r, rec in enumerate(rows):
            for c, val in enumerate(rec):
                it = QTableWidgetItem(str(val or ""))
                if c == 0:
                    it.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, c, it)
        self.table.blockSignals(False)
        if self.cur_id is not None:
            for r in range(self.table.rowCount()):
                if int(self.table.item(r, 0).text()) == self.cur_id:
                    self.table.selectRow(r)
                    break

    def on_select(self):
        r = self.table.currentRow()
        if r < 0 or self.table.item(r, 0) is None:
            return
        self.cur_id = int(self.table.item(r, 0).text())
        rec = self.db.execute("SELECT name,phone,email,note,status,vip FROM clients WHERE id=?",
                              (self.cur_id,)).fetchone()
        self.f_name.setText(rec[0])
        self.f_phone.setText(rec[1] or "")
        self.f_email.setText(rec[2] or "")
        self.f_note.setPlainText(rec[3] or "")
        self.f_status.setCurrentText(rec[4])
        self.f_vip.setChecked(bool(rec[5]))
        self.box.setTitle(f"Карточка клиента · #{self.cur_id}")
        self.validate(silent=True)

    def new(self):
        self.cur_id = None
        self.table.clearSelection()
        for w in (self.f_name, self.f_phone, self.f_email):
            w.clear()
        self.f_note.clear()
        self.f_vip.setChecked(False)
        self.f_status.setCurrentIndex(0)
        self.box.setTitle("Новый клиент")
        self.f_name.setFocus()
        self.validate(silent=True)

    def validate(self, silent=False):
        bad_name = not self.f_name.text().strip()
        mail = self.f_email.text().strip()
        bad_mail = bool(mail) and ("@" not in mail or "." not in mail.split("@")[-1])
        set_prop(self.f_name, "invalid", bad_name and not silent)
        set_prop(self.f_email, "invalid", bad_mail)
        msg = "Укажите имя" if bad_name else ("Некорректный e-mail" if bad_mail else "")
        self.err.setText("" if silent and bad_name else msg)
        return not (bad_name or bad_mail)

    def save(self):
        if not self.validate():
            return
        vals = (self.f_name.text().strip(), self.f_phone.text(), self.f_email.text().strip(),
                self.f_note.toPlainText(), self.f_status.currentText(), int(self.f_vip.isChecked()))
        if self.cur_id is None:
            cur = self.db.execute("INSERT INTO clients(name,phone,email,note,status,vip) VALUES(?,?,?,?,?,?)", vals)
            self.cur_id = cur.lastrowid
        else:
            self.db.execute("UPDATE clients SET name=?,phone=?,email=?,note=?,status=?,vip=? WHERE id=?",
                            vals + (self.cur_id,))
        self.db.commit()
        self.reload()

    def delete(self):
        if self.cur_id is None:
            return
        box = QMessageBox(self.window())
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Удаление")
        box.setText("Удалить выбранную запись?")
        box.setInformativeText("Действие нельзя отменить.")
        yes = box.addButton("Удалить", QMessageBox.DestructiveRole)
        yes.setProperty("kind", "danger")
        no = box.addButton("Отмена", QMessageBox.RejectRole)
        box.setDefaultButton(no)
        box.exec_()
        if box.clickedButton() is yes:
            self.db.execute("DELETE FROM clients WHERE id=?", (self.cur_id,))
            self.db.commit()
            self.cur_id = None
            self.reload()
            if self.table.rowCount():
                self.table.selectRow(0)
            else:
                self.new()


def demo_db():
    card, lay = demo_section("Форма редактирования строки БД",
                             "ничего нового — комбинация QSS_LINEEDIT + QSS_TEXTEDIT + QSS_COMBO_SPIN + QSS_BUTTON + "
                             "QSS_TABLE + QSS_GROUPBOX;  ошибка поля: set_prop(w, \"invalid\", True)")
    lay.addWidget(_DbDemo())
    return card


# ---------------------------- Окно ----------------------------
class Gallery(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QSS Toolkit — витрина")
        self.resize(1160, 860)
        page = QWidget()
        page.setObjectName("demoPage")
        v = QVBoxLayout(page)
        v.setContentsMargins(28, 24, 28, 32)
        v.setSpacing(22)
        v.addWidget(demo_label("QSS Toolkit", "pageTitle"))
        v.addWidget(demo_label("Прокручивайте колесом мыши. В каждой карточке строка «ЧТО БРАТЬ» говорит, "
                               "какие блоки QSS и какие классы из файла нужны для этого виджета.",
                               "pageSubtitle", wrap=True))
        for s in (demo_labels(), demo_buttons(self), demo_animated_buttons(), demo_lineedit(), demo_textedit(),
                  demo_combo(), demo_checks(), demo_groupbox(), demo_tables(), demo_misc(),
                  demo_messagebox(self), demo_mdi(), demo_db()):
            v.addWidget(s)
        v.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        scroll.verticalScrollBar().setSingleStep(40)
        self.setCentralWidget(scroll)


def main():
    app = QApplication(sys.argv)
    app.setStyle(MdiStyle("Fusion"))          # >>> MdiStyle
    apply_mdi_palette(app)                     # >>> apply_mdi_palette
    app.setStyleSheet(ALL_QSS + QSS_DEMO_ONLY) # >>> ALL_QSS (в своём проекте только ALL_QSS)
    w = Gallery()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()