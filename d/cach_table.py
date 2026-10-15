#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Витрина стилей PyQt5 (QSS): у каждого виджета несколько версий оформления.
Вся страница прокручивается колесом мыши; вверху — быстрый переход по разделам
и переключатель светлого/тёмного фона страницы.

Запуск:  pip install PyQt5  &&  python qss_showcase.py
Содержимое: QLabel, QLineEdit, QTextEdit, QPushButton (в т.ч. bubble/lift),
QGroupBox, QCheckBox/QRadioButton/переключатель, QComboBox/QSpinBox/QDateEdit,
QTableWidget (+делегат с приоритетом цветов модели), QMessageBox, QMdiArea
(рамки/кнопки/свой заголовок) и формы редактирования записей SQLite.
"""
import sys
import math
import sqlite3

from PyQt5.QtCore import (Qt, QTimer, QVariantAnimation, QEasingCurve, QPointF, QRectF,
                          QSize, QDate)
from PyQt5.QtGui import QPainter, QColor, QPainterPath, QPalette, QBrush, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QScrollArea, QVBoxLayout,
    QHBoxLayout, QGridLayout, QFormLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QGroupBox, QCheckBox, QRadioButton, QComboBox, QSpinBox,
    QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QMdiArea, QStyledItemDelegate, QStyle, QStyleOptionViewItem,
    QProxyStyle)


# =====================================================================
#  Вспомогательные функции
# =====================================================================
def tpl(s, **kw):
    """Подстановка токенов @name@ в шаблон QSS."""
    for k, v in kw.items():
        s = s.replace("@%s@" % k, str(v))
    return s


def L(text, name="", wrap=False, **props):
    lab = QLabel(text)
    if name:
        lab.setObjectName(name)
    for k, v in props.items():
        lab.setProperty(k, v)
    lab.setWordWrap(wrap)
    return lab


def vbox(*widgets, spacing=8):
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(spacing)
    for x in widgets:
        lay.addWidget(x)
    return w


def hbox(*widgets, spacing=8, stretch=True):
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(spacing)
    for x in widgets:
        lay.addWidget(x)
    if stretch:
        lay.addStretch(1)
    return w


def stage(widget, qss, bg):
    """Цветная «сцена», чтобы вариант выглядел одинаково на любом фоне страницы."""
    f = QFrame()
    f.setObjectName("stage")
    f.setStyleSheet("#stage{background:%s;border-radius:8px;}" % bg)
    lay = QVBoxLayout(f)
    lay.setContentsMargins(14, 14, 14, 14)
    lay.addWidget(widget)
    if qss:
        widget.setStyleSheet(qss)
    return f


def card(name, widget, qss="", bg="#FFFFFF"):
    f = QFrame()
    f.setObjectName("card")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(12, 10, 12, 12)
    lay.setSpacing(8)
    lay.addWidget(L(name, "varName", wrap=True))
    lay.addWidget(stage(widget, qss, bg))
    lay.addStretch(1)
    return f


def section(title, desc, items, cols=2):
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(10)
    lay.addWidget(L(title, "secTitle"))
    lay.addWidget(L(desc, "secDesc", wrap=True))
    grid = QGridLayout()
    grid.setSpacing(12)
    for i, (name, w, qss, bg) in enumerate(items):
        grid.addWidget(card(name, w, qss, bg), i // cols, i % cols)
    for c in range(cols):
        grid.setColumnStretch(c, 1)
    lay.addLayout(grid)
    return box


# =====================================================================
#  Кастомные виджеты
# =====================================================================
class BubbleButton(QPushButton):
    """Кнопка: при наведении от точки входа курсора расходится круг."""

    def __init__(self, text="", color="#FFFFFF", alpha=50, radius=7, parent=None):
        super().__init__(text, parent)
        self._r = 0.0
        self._center = QPointF()
        self._corner = radius            # = border-radius в QSS
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
        return max(math.hypot(c.x() - x, c.y() - y)
                   for x, y in ((0, 0), (w, 0), (0, h), (w, h)))

    def _run(self, end, duration):
        self._anim.stop()
        self._anim.setDuration(duration)
        self._anim.setStartValue(self._r)
        self._anim.setEndValue(end)
        self._anim.start()

    def enterEvent(self, e):
        self._center = QPointF(e.pos())
        self._run(self._max_r(), 450)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._run(0.0, 300)
        super().leaveEvent(e)

    def paintEvent(self, e):
        super().paintEvent(e)
        if self._r <= 0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()), self._corner, self._corner)
        p.setClipPath(clip)
        p.setPen(Qt.NoPen)
        p.setBrush(self._color)
        p.drawEllipse(self._center, self._r, self._r)


class LiftButton(QPushButton):
    """Кнопка: при наведении «приподнимается» (растущая тень)."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        from PyQt5.QtWidgets import QGraphicsDropShadowEffect
        self._sh = QGraphicsDropShadowEffect(self)
        self._sh.setColor(QColor(79, 107, 237, 140))
        self._sh.setOffset(0, 0)
        self._sh.setBlurRadius(0)
        self.setGraphicsEffect(self._sh)
        self.setCursor(Qt.PointingHandCursor)
        self._a = QVariantAnimation(self)
        self._a.setDuration(200)
        self._a.valueChanged.connect(self._apply)

    def _apply(self, v):
        self._sh.setBlurRadius(v)
        self._sh.setOffset(0, v / 4)

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


class ToggleSwitch(QCheckBox):
    """Переключатель в стиле iOS (QSS не умеет двигать «ползунок»)."""

    def __init__(self, text="", on="#4F6BED", off="#C5CCDB", parent=None):
        super().__init__(text, parent)
        self._on, self._off = QColor(on), QColor(off)
        self._pos = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(180)
        self._anim.valueChanged.connect(self._set)
        self.toggled.connect(self._toggle)
        self.setCursor(Qt.PointingHandCursor)

    def _set(self, v):
        self._pos = float(v)
        self.update()

    def _toggle(self, checked):
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def sizeHint(self):
        extra = 10 + self.fontMetrics().horizontalAdvance(self.text()) if self.text() else 0
        return QSize(44 + extra, 26)

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h, t = 40, 22, self._pos
        y = (self.height() - h) / 2
        c = QColor(*(int(self._off.getRgb()[i] + (self._on.getRgb()[i] - self._off.getRgb()[i]) * t)
                     for i in range(3)))
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        p.drawRoundedRect(QRectF(0, y, w, h), h / 2, h / 2)
        p.setBrush(QColor("white"))
        d = h - 6
        p.drawEllipse(QRectF(3 + (w - d - 6) * t, y + 3, d, d))
        if self.text():
            p.setPen(self.palette().color(QPalette.WindowText))
            p.drawText(QRectF(w + 10, 0, self.width() - w - 10, self.height()),
                       Qt.AlignVCenter | Qt.AlignLeft, self.text())


class ColorDelegate(QStyledItemDelegate):
    """Делегат: цвета из модели (BackgroundRole/ForegroundRole) главнее QSS."""

    def __init__(self, parent=None, hover="#F0F3FA", selected="#E3E9FD", sel_text="#1F2A6B"):
        super().__init__(parent)
        self.hover, self.selected, self.sel_text = QColor(hover), QColor(selected), QColor(sel_text)

    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        sel = bool(opt.state & QStyle.State_Selected)
        hov = bool(opt.state & QStyle.State_MouseOver)
        mbg = index.data(Qt.BackgroundRole)
        bg = None
        if sel:
            bg = self.selected
        elif mbg is not None:
            bg = mbg.color() if isinstance(mbg, QBrush) else QColor(mbg)
        elif hov:
            bg = self.hover
        if bg is not None:
            painter.fillRect(opt.rect, bg)
        opt.backgroundBrush = QBrush(Qt.NoBrush)
        opt.state &= ~(QStyle.State_Selected | QStyle.State_MouseOver | QStyle.State_HasFocus)
        if sel:
            opt.palette.setColor(QPalette.Text, self.sel_text)
        super().paint(painter, opt, index)


class MdiProxyStyle(QProxyStyle):
    """Размеры заголовка и рамки MDI-окон."""

    def __init__(self, title_h=30, frame=3):
        super().__init__("Fusion")
        self.th, self.fw = title_h, frame

    def pixelMetric(self, metric, option=None, widget=None):
        if metric == QStyle.PM_TitleBarHeight:
            return self.th
        if metric == QStyle.PM_MdiSubWindowFrameWidth:
            return self.fw
        return super().pixelMetric(metric, option, widget)


class TitleBar(QWidget):
    """Свой заголовок для безрамочного MDI-окна (перетаскивание мышью)."""

    def __init__(self, title):
        super().__init__()
        self.setObjectName("mbar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.sub = None
        self._p = None
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 6, 0)
        lay.addWidget(QLabel(title))
        lay.addStretch(1)
        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("mclose")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        lay.addWidget(self.btn_close)

    def mousePressEvent(self, e):
        self._p = e.globalPos()
        if self.sub:
            self.sub.raise_()

    def mouseMoveEvent(self, e):
        if self._p is not None and self.sub is not None:
            self.sub.move(self.sub.pos() + (e.globalPos() - self._p))
            self._p = e.globalPos()

    def mouseReleaseEvent(self, e):
        self._p = None


# =====================================================================
#  Раздел: QLabel
# =====================================================================
def sec_labels():
    return [
        ("Заголовок + подзаголовок",
         vbox(L("Клиенты", "t"), L("Управление записями базы данных", "s"), spacing=2),
         "#t{font-size:22px;font-weight:700;color:#111827;} #s{color:#6B7280;}", "#FFFFFF"),
        ("Бейджи статуса (динамическое свойство state)",
         hbox(L("Активен", "b", state="ok"), L("Ожидает", "b", state="warn"),
              L("Заблокирован", "b", state="bad")),
         """QLabel#b{padding:3px 10px;border-radius:11px;font-size:12px;font-weight:600;
                     background:#EEF1F6;color:#4B5563;}
            QLabel#b[state="ok"]{background:#E3F6EC;color:#1E7F52;}
            QLabel#b[state="warn"]{background:#FFF4D6;color:#8A6100;}
            QLabel#b[state="bad"]{background:#FDE8E9;color:#B42329;}""", "#FFFFFF"),
        ("Подпись поля + подсказка + ошибка",
         vbox(L("E-mail", "f"), L("Мы не будем присылать спам", "h"),
              L("Введите корректный адрес", "e"), spacing=3),
         "#f{font-weight:600;color:#4B5563;} #h{color:#9CA3AF;font-size:12px;} "
         "#e{color:#E5484D;font-size:12px;}", "#FFFFFF"),
        ("Баннер с градиентом",
         L("✨  Новое: экспорт таблицы в Excel", "ban"),
         """QLabel{color:white;font-weight:600;padding:12px 16px;border-radius:10px;
                  background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #6C86FF,stop:1 #A66CFF);}""",
         "#FFFFFF"),
        ("Тёмные теги",
         hbox(L("python", "tag"), L("pyqt5", "tag"), L("sqlite", "tag")),
         "QLabel#tag{background:#2B2F3A;color:#8EA2FF;border:1px solid #3A3F4D;"
         "border-radius:6px;padding:3px 9px;font-size:12px;}", "#1B1D23"),
        ("Счётчик-карточка",
         vbox(L("1 248", "n"), L("клиентов в базе", "c"), spacing=0),
         "#n{font-size:34px;font-weight:800;color:#4F6BED;} #c{color:#6B7280;}", "#FFFFFF"),
    ]


# =====================================================================
#  Раздел: QLineEdit
# =====================================================================
def sec_lineedit():
    def le(text="", ph="", ro=False, clear=False):
        e = QLineEdit(text)
        e.setPlaceholderText(ph)
        e.setReadOnly(ro)
        e.setClearButtonEnabled(clear)
        return e

    outline = tpl("""QLineEdit{background:@bg@;color:@fg@;border:1px solid @bd@;border-radius:@r@px;
        padding:0 12px;min-height:34px;selection-background-color:@ac@;selection-color:#fff;}
        QLineEdit:hover{border-color:@bdh@;} QLineEdit:focus{border:1px solid @ac@;}""",
                  bg="#FFFFFF", fg="#1F2937", bd="#D3D9E5", bdh="#B3BCD0", ac="#4F6BED", r=7)
    filled = tpl("""QLineEdit{background:@bg@;color:@fg@;border:2px solid @bg@;border-radius:@r@px;
        padding:0 14px;min-height:34px;selection-background-color:@ac@;selection-color:#fff;}
        QLineEdit:focus{background:#FFFFFF;border:2px solid @ac@;}""",
                 bg="#EEF1F6", fg="#1F2937", ac="#4F6BED", r=10)
    dark = tpl("""QLineEdit{background:@bg@;color:@fg@;border:1px solid @bd@;border-radius:7px;
        padding:0 12px;min-height:34px;selection-background-color:@ac@;selection-color:#fff;}
        QLineEdit:hover{border-color:#50566A;} QLineEdit:focus{border:1px solid @ac@;}""",
               bg="#2B2F3A", fg="#E5E7EB", bd="#3A3F4D", ac="#6C86FF")
    return [
        ("Контурное (светлое)", le("Анна Смирнова", "Имя"), outline, "#FFFFFF"),
        ("Заливка, крупный радиус", le("anna@mail.ru", "E-mail"), filled, "#FFFFFF"),
        ("Только нижняя линия", le("+7 900 111-22-33", "Телефон"),
         """QLineEdit{background:transparent;color:#1F2937;border:none;border-bottom:2px solid #D3D9E5;
            border-radius:0;padding:0 2px;min-height:34px;}
            QLineEdit:focus{border-bottom:2px solid #4F6BED;}""", "#FFFFFF"),
        ("Тёмное", le("Борис Лебедев", "Имя"), dark, "#1B1D23"),
        ("Ошибка валидации", le("bad@mail", "E-mail"),
         """QLineEdit{background:#FFF8F8;color:#1F2937;border:1px solid #E5484D;border-radius:7px;
            padding:0 12px;min-height:34px;}""", "#FFFFFF"),
        ("Поиск-«пилюля» + кнопка очистки", le("", "Поиск…", clear=True),
         """QLineEdit{background:#F3F5F9;color:#1F2937;border:1px solid #E1E6F0;border-radius:18px;
            padding:0 16px;min-height:36px;}
            QLineEdit:focus{background:#fff;border:1px solid #4F6BED;}""", "#FFFFFF"),
        ("Только чтение", le("ID-000124", "", ro=True),
         """QLineEdit{background:#F3F5F9;color:#6B7280;border:1px solid #E4E8F0;border-radius:7px;
            padding:0 12px;min-height:34px;}""", "#FFFFFF"),
        ("✅ Правильно: текст с «хвостами» помещается (padding 0 по вертикали)",
         le("Проверка: Щцджру gjpqy"),
         """QLineEdit{background:#fff;color:#1F2937;border:1px solid #D3D9E5;border-radius:7px;
            padding:0 12px;min-height:34px;font-size:15px;}""", "#FFFFFF"),
        ("❌ Как НЕ надо: большой padding + малая высота → текст обрезается",
         le("Проверка: Щцджру gjpqy"),
         """QLineEdit{background:#fff;color:#1F2937;border:1px solid #E5484D;border-radius:7px;
            padding:12px 12px;min-height:0;max-height:30px;font-size:15px;}""", "#FFFFFF"),
    ]


# =====================================================================
#  Раздел: QTextEdit
# =====================================================================
def sec_textedit():
    def te(text, margin=4, noframe=False):
        t = QTextEdit()
        t.setPlainText(text)
        t.setFixedHeight(110)
        t.document().setDocumentMargin(margin)
        if noframe:
            t.setFrameShape(QFrame.NoFrame)
        return t

    txt = "Постоянный клиент.\nПредпочитает связь по e-mail.\nСкидка 10%."
    return [
        ("Светлое",
         te(txt),
         """QTextEdit{background:#fff;color:#1F2937;border:1px solid #D3D9E5;border-radius:7px;
            padding:6px 8px;selection-background-color:#4F6BED;selection-color:#fff;}
            QTextEdit:focus{border:1px solid #4F6BED;}""", "#FFFFFF"),
        ("Тёмное",
         te(txt),
         """QTextEdit{background:#2B2F3A;color:#E5E7EB;border:1px solid #3A3F4D;border-radius:7px;
            padding:6px 8px;selection-background-color:#6C86FF;selection-color:#fff;}
            QTextEdit:focus{border:1px solid #6C86FF;}""", "#1B1D23"),
        ("Без рамки, линия снизу (documentMargin=2)",
         te(txt, margin=2, noframe=True),
         """QTextEdit{background:transparent;color:#1F2937;border:none;border-bottom:2px solid #D3D9E5;
            padding:0;} QTextEdit:focus{border-bottom:2px solid #4F6BED;}""", "#FFFFFF"),
    ]


# =====================================================================
#  Раздел: QPushButton
# =====================================================================
def sec_buttons():
    def pair(text):
        b1, b2 = QPushButton(text), QPushButton(text)
        b2.setEnabled(False)
        return hbox(b1, b2)

    solid = """QPushButton{background:#4F6BED;color:#fff;border:none;border-radius:7px;padding:0 20px;
               min-height:36px;font-weight:600;}"""
    items = [
        ("Основная (+ disabled)", pair("Сохранить"),
         solid + """QPushButton:hover{background:#435DD8;} QPushButton:pressed{background:#3A50BF;}
         QPushButton:disabled{background:#B9C4F5;color:#fff;}""", "#FFFFFF"),
        ("Контурная опасная (+ disabled)", pair("Удалить"),
         """QPushButton{background:#fff;color:#D13B41;border:1px solid #F1B8BA;border-radius:7px;
            padding:0 20px;min-height:36px;font-weight:600;}
            QPushButton:hover{background:#E5484D;border-color:#E5484D;color:#fff;}
            QPushButton:pressed{background:#C93A3F;}
            QPushButton:disabled{background:#F3F5F9;color:#A3ABB9;border-color:#E4E8F0;}""", "#FFFFFF"),
        ("Без фона (ghost)", pair("Отмена"),
         """QPushButton{background:transparent;color:#4F6BED;border:1px solid transparent;
            border-radius:7px;padding:0 20px;min-height:36px;font-weight:600;}
            QPushButton:hover{background:#EDF0FD;} QPushButton:pressed{background:#DEE4FB;}
            QPushButton:disabled{color:#A3ABB9;}""", "#FFFFFF"),
        ("Тональная (мягкий акцент)", pair("Экспорт"),
         """QPushButton{background:#E3E9FD;color:#2B3FA8;border:none;border-radius:7px;
            padding:0 20px;min-height:36px;font-weight:600;}
            QPushButton:hover{background:#D3DCFB;} QPushButton:pressed{background:#C3CEF8;}
            QPushButton:disabled{background:#EEF1F6;color:#A3ABB9;}""", "#FFFFFF"),
        ("Градиент-пилюля", QPushButton("Начать"),
         """QPushButton{color:#fff;border:none;border-radius:18px;padding:0 28px;min-height:36px;
            font-weight:700;background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #6C86FF,stop:1 #A66CFF);}
            QPushButton:hover{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #7F96FF,stop:1 #B787FF);}
            QPushButton:pressed{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #5A73E8,stop:1 #8E55E8);}""",
         "#FFFFFF"),
        ("Тёмная кнопка", QPushButton("Войти"),
         """QPushButton{background:#111827;color:#fff;border:1px solid #111827;border-radius:18px;
            padding:0 28px;min-height:36px;font-weight:600;}
            QPushButton:hover{background:#1F2937;} QPushButton:pressed{background:#000;}""", "#FFFFFF"),
        ("Квадратная иконка", QPushButton("＋"),
         """QPushButton{background:#4F6BED;color:#fff;border:none;border-radius:10px;font-size:20px;
            min-width:38px;max-width:38px;min-height:38px;max-height:38px;padding:0;}
            QPushButton:hover{background:#435DD8;}""", "#FFFFFF"),
        ("Переключаемая (checkable)", None,
         """QPushButton{background:#fff;color:#4B5563;border:1px solid #D3D9E5;border-radius:7px;
            padding:0 18px;min-height:34px;font-weight:600;}
            QPushButton:hover{border-color:#4F6BED;}
            QPushButton:checked{background:#E3E9FD;color:#2B3FA8;border-color:#4F6BED;}""", "#FFFFFF"),
        ("Bubble: круг от точки наведения", BubbleButton("Сохранить", "#FFFFFF", 55, 7),
         solid, "#FFFFFF"),
        ("Bubble: градиент-пилюля", BubbleButton("Попробовать", "#FFFFFF", 60, 18),
         """QPushButton{color:#fff;border:none;border-radius:18px;padding:0 28px;min-height:36px;
            font-weight:700;background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #6C86FF,stop:1 #A66CFF);}""",
         "#FFFFFF"),
        ("Bubble: контурная (круг цвета акцента)", BubbleButton("Подробнее", "#4F6BED", 38, 7),
         """QPushButton{background:#fff;color:#4F6BED;border:1px solid #4F6BED;border-radius:7px;
            padding:0 20px;min-height:36px;font-weight:600;}""", "#FFFFFF"),
        ("Lift: тень при наведении", LiftButton("Приподняться"), solid, "#FFFFFF"),
    ]
    chk = QPushButton("★ Избранное")
    chk.setCheckable(True)
    items[7] = (items[7][0], chk, items[7][2], items[7][3])
    return items


# =====================================================================
#  Раздел: QGroupBox
# =====================================================================
def sec_groupbox():
    def grp(title):
        g = QGroupBox(title)
        form = QFormLayout(g)
        form.setVerticalSpacing(8)
        form.addRow("Имя", QLineEdit("Анна"))
        form.addRow("Город", QLineEdit("Москва"))
        form.addRow("", QCheckBox("Активен"))
        return g

    inputs = ("QLineEdit{background:#fff;border:1px solid #D3D9E5;border-radius:6px;padding:0 8px;"
              "min-height:28px;color:#1F2937;}")
    return [
        ("Классический: заголовок на линии", grp("Данные клиента"),
         """QGroupBox{border:1px solid #D3D9E5;border-radius:8px;margin-top:14px;padding:16px 12px 10px 12px;
            font-weight:700;color:#374151;}
            QGroupBox::title{subcontrol-origin:margin;left:12px;padding:0 6px;color:#4F6BED;background:#fff;}
            QLabel{font-weight:normal;color:#4B5563;}""" + inputs, "#FFFFFF"),
        ("Вкладка-заголовок цветная", grp("Контакты"),
         """QGroupBox{background:#fff;border:1px solid #C5D0F8;border-radius:0 10px 10px 10px;margin-top:30px;
            padding:14px 12px 10px 12px;}
            QGroupBox::title{subcontrol-origin:margin;subcontrol-position:top left;background:#4F6BED;
            color:#fff;padding:6px 16px;border-top-left-radius:10px;border-top-right-radius:10px;font-weight:700;}
            QLabel{color:#4B5563;}""" + inputs, "#FFFFFF"),
        ("Минимализм: линия сверху", grp("ДОПОЛНИТЕЛЬНО"),
         """QGroupBox{border:none;border-top:1px solid #DDE2EC;margin-top:12px;padding:16px 0 4px 0;}
            QGroupBox::title{subcontrol-origin:margin;left:0;padding:0 8px 0 0;font-size:11px;
            font-weight:800;color:#9CA3AF;background:#fff;}
            QLabel{color:#4B5563;}""" + inputs, "#FFFFFF"),
        ("Тёмная карточка", grp("Данные клиента"),
         """QGroupBox{background:#242730;border:1px solid #343845;border-radius:10px;margin-top:14px;
            padding:16px 12px 10px 12px;font-weight:700;color:#D1D5DB;}
            QGroupBox::title{subcontrol-origin:margin;left:14px;padding:0 8px;color:#8EA2FF;background:#1B1D23;}
            QLabel{font-weight:normal;color:#B4BAC6;} QCheckBox{color:#E5E7EB;}
            QLineEdit{background:#2B2F3A;border:1px solid #3A3F4D;border-radius:6px;padding:0 8px;
            min-height:28px;color:#E5E7EB;}""", "#1B1D23"),
    ]


# =====================================================================
#  Раздел: QCheckBox / QRadioButton / переключатель
# =====================================================================
def sec_checks():
    def checks(*texts, cls=QCheckBox, checked=(0,)):
        ws = []
        for i, t in enumerate(texts):
            w = cls(t)
            w.setChecked(i in checked)
            ws.append(w)
        return vbox(*ws, spacing=10)

    return [
        ("Квадрат, акцент", checks("Активен", "Подписка на рассылку", "Согласен с условиями", checked=(0, 2)),
         """QCheckBox{spacing:9px;color:#1F2937;}
            QCheckBox::indicator{width:18px;height:18px;border:1.5px solid #B3BCD0;border-radius:5px;background:#fff;}
            QCheckBox::indicator:hover{border-color:#4F6BED;}
            QCheckBox::indicator:checked{background:#4F6BED;border-color:#4F6BED;}
            QCheckBox::indicator:disabled{background:#F3F5F9;}""", "#FFFFFF"),
        ("Круглый «пузырь»", checks("Выполнено", "В архиве", "Важное", checked=(1,)),
         """QCheckBox{spacing:9px;color:#1F2937;}
            QCheckBox::indicator{width:20px;height:20px;border:2px solid #C5CCDB;border-radius:11px;background:#fff;}
            QCheckBox::indicator:hover{border-color:#2FA36B;}
            QCheckBox::indicator:checked{background:#2FA36B;border-color:#2FA36B;}""", "#FFFFFF"),
        ("Радио-кнопки", checks("Мужской", "Женский", "Не указывать", cls=QRadioButton),
         """QRadioButton{spacing:9px;color:#1F2937;}
            QRadioButton::indicator{width:18px;height:18px;border:1.5px solid #B3BCD0;border-radius:10px;background:#fff;}
            QRadioButton::indicator:hover{border-color:#4F6BED;}
            QRadioButton::indicator:checked{width:8px;height:8px;border:5px solid #4F6BED;border-radius:9px;background:#fff;}""", "#FFFFFF"),
        ("Переключатель (кастомный paintEvent)",
         vbox(ToggleSwitch("Уведомления"), ToggleSwitch("Тёмная тема", on="#2FA36B"),
              ToggleSwitch("Автосохранение", on="#E5484D"), spacing=10),
         "color:#1F2937;", "#FFFFFF"),
        ("Тёмные чекбоксы", checks("Активен", "Подписка", "Согласен", checked=(0, 1)),
         """QCheckBox{spacing:9px;color:#E5E7EB;}
            QCheckBox::indicator{width:18px;height:18px;border:1.5px solid #50566A;border-radius:5px;background:#2B2F3A;}
            QCheckBox::indicator:hover{border-color:#6C86FF;}
            QCheckBox::indicator:checked{background:#6C86FF;border-color:#6C86FF;}""", "#1B1D23"),
        ("Переключатель на тёмном фоне",
         vbox(ToggleSwitch("Wi-Fi", on="#6C86FF", off="#3A3F4D"),
              ToggleSwitch("Bluetooth", on="#6C86FF", off="#3A3F4D"), spacing=10),
         "color:#E5E7EB;", "#1B1D23"),
    ]


# =====================================================================
#  Раздел: QComboBox / QSpinBox / QDateEdit
# =====================================================================
def sec_combos():
    def build():
        cb = QComboBox()
        cb.addItems(["Москва", "Санкт-Петербург", "Казань", "Новосибирск"])
        sp = QSpinBox()
        sp.setRange(0, 120)
        sp.setValue(32)
        de = QDateEdit(QDate.currentDate())
        de.setCalendarPopup(True)
        return vbox(cb, sp, de)

    base = """QComboBox,QSpinBox,QDateEdit{background:@bg@;color:@fg@;border:1px solid @bd@;border-radius:@r@px;
        padding:0 10px;min-height:34px;selection-background-color:@ac@;selection-color:#fff;}
        QComboBox:hover,QSpinBox:hover,QDateEdit:hover{border-color:@bdh@;}
        QComboBox:focus,QSpinBox:focus,QDateEdit:focus{border:1px solid @ac@;}
        QComboBox QAbstractItemView{background:@bg@;color:@fg@;border:1px solid @bd@;padding:4px;
        selection-background-color:@sel@;selection-color:@selfg@;outline:0;}"""
    return [
        ("Светлые", build(),
         tpl(base, bg="#FFFFFF", fg="#1F2937", bd="#D3D9E5", bdh="#B3BCD0", ac="#4F6BED", r=7,
             sel="#E3E9FD", selfg="#1F2A6B"), "#FFFFFF"),
        ("Заливка, крупный радиус", build(),
         tpl(base, bg="#EEF1F6", fg="#1F2937", bd="#EEF1F6", bdh="#D3D9E5", ac="#4F6BED", r=12,
             sel="#E3E9FD", selfg="#1F2A6B"), "#FFFFFF"),
        ("Тёмные", build(),
         tpl(base, bg="#2B2F3A", fg="#E5E7EB", bd="#3A3F4D", bdh="#50566A", ac="#6C86FF", r=7,
             sel="#34406B", selfg="#FFFFFF"), "#1B1D23"),
    ]


# =====================================================================
#  Раздел: QTableWidget
# =====================================================================
DATA = [
    (1, "Анна Смирнова", "+7 900 111-22-33", "Активен"),
    (2, "Борис Лебедев", "+7 900 222-33-44", "Ожидает"),
    (3, "Вера Орлова", "+7 900 333-44-55", "Заблокирован"),
    (4, "Глеб Кузнецов", "+7 900 444-55-66", "Активен"),
    (5, "Дарья Попова", "+7 900 555-66-77", "Ожидает"),
    (6, "Егор Волков", "+7 900 666-77-88", "Активен"),
]
STATUS_COLORS = {"Активен": ("#E3F6EC", "#1E7F52"),
                 "Ожидает": ("#FFF4D6", "#8A6100"),
                 "Заблокирован": ("#FDE8E9", "#B42329")}


def make_table(row_h=32, grid=False, colored=False, delegate=None):
    t = QTableWidget(len(DATA), 4)
    t.setHorizontalHeaderLabels(["ID", "Имя", "Телефон", "Статус"])
    for r, rec in enumerate(DATA):
        for c, v in enumerate(rec):
            it = QTableWidgetItem(str(v))
            if c in (0, 3):
                it.setTextAlignment(Qt.AlignCenter)
            if colored and c == 3:
                bg, fg = STATUS_COLORS[v]
                it.setBackground(QColor(bg))
                it.setForeground(QColor(fg))
            t.setItem(r, c, it)
    t.verticalHeader().setVisible(False)
    t.verticalHeader().setDefaultSectionSize(row_h)
    hh = t.horizontalHeader()
    hh.setSectionResizeMode(QHeaderView.Stretch)
    hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
    hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
    t.setAlternatingRowColors(True)
    t.setShowGrid(grid)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.SingleSelection)
    t.setEditTriggers(QAbstractItemView.DoubleClicked)
    t.setMouseTracking(True)
    t.setFixedHeight(row_h * 6 + 52)
    if delegate:
        t.setItemDelegate(delegate(t))
    return t


def sec_tables():
    clean = """
    QTableWidget{background:#fff;alternate-background-color:#F8FAFD;border:1px solid #DDE2EC;border-radius:8px;
      gridline-color:#EBEEF4;selection-background-color:#E3E9FD;selection-color:#1F2A6B;outline:0;color:#1F2937;}
    QTableWidget::item{padding:4px 10px;border:none;}
    QTableWidget::item:hover{background:#F0F3FA;}
    QTableWidget::item:selected{background:#E3E9FD;color:#1F2A6B;}
    QTableWidget::item:focus{border:none;outline:none;}
    QTableWidget QLineEdit{margin:0;padding:0 8px;min-height:0;border:1px solid #4F6BED;border-radius:0;background:#fff;}
    QHeaderView::section{background:#F3F5F9;color:#4B5563;padding:8px 10px;border:none;
      border-bottom:1px solid #DDE2EC;border-right:1px solid #EBEEF4;font-weight:700;font-size:12px;}
    QTableCornerButton::section{background:#F3F5F9;border:none;}"""
    dark = """
    QTableWidget{background:#242730;alternate-background-color:#282B35;border:1px solid #343845;border-radius:8px;
      gridline-color:#2F333F;selection-background-color:#34406B;selection-color:#fff;outline:0;color:#E5E7EB;}
    QTableWidget::item{padding:4px 10px;border:none;}
    QTableWidget::item:hover{background:#2D313D;}
    QTableWidget::item:selected{background:#34406B;color:#fff;}
    QTableWidget::item:focus{border:none;outline:none;}
    QTableWidget QLineEdit{margin:0;padding:0 8px;min-height:0;border:1px solid #6C86FF;border-radius:0;
      background:#1B1D23;color:#fff;}
    QHeaderView::section{background:#1F222A;color:#AEB4C0;padding:8px 10px;border:none;
      border-bottom:1px solid #343845;border-right:1px solid #2B2F3A;font-weight:700;font-size:12px;}
    QTableCornerButton::section{background:#1F222A;border:none;}"""
    grid = """
    QTableWidget{background:#fff;alternate-background-color:#FAFBFE;border:1px solid #4F6BED;
      gridline-color:#D9DFF0;selection-background-color:#FFE9A8;selection-color:#3D2E00;outline:0;color:#1F2937;}
    QTableWidget::item{padding:4px 8px;}
    QTableWidget::item:focus{border:none;outline:none;}
    QTableWidget QLineEdit{margin:0;padding:0 6px;min-height:0;border:2px solid #4F6BED;border-radius:0;}
    QHeaderView::section{background:#4F6BED;color:#fff;padding:8px;border:none;
      border-right:1px solid #6D84F0;font-weight:700;}
    QTableCornerButton::section{background:#4F6BED;border:none;}"""
    rows = """
    QTableWidget{background:#fff;border:none;gridline-color:transparent;selection-background-color:#EDF0FD;
      selection-color:#1F2A6B;outline:0;color:#1F2937;}
    QTableWidget::item{padding:4px 12px;border:none;border-bottom:1px solid #EEF1F6;}
    QTableWidget::item:selected{background:#EDF0FD;color:#1F2A6B;border-bottom:1px solid #C5D0F8;}
    QTableWidget::item:focus{border:none;outline:none;}
    QHeaderView::section{background:#fff;color:#9CA3AF;padding:10px 12px;border:none;
      border-bottom:2px solid #EEF1F6;font-weight:700;font-size:11px;}
    QTableCornerButton::section{background:#fff;border:none;}"""
    delegated = """
    QTableWidget{background:#fff;alternate-background-color:#F8FAFD;border:1px solid #DDE2EC;border-radius:8px;
      gridline-color:#EBEEF4;outline:0;color:#1F2937;}
    QTableWidget::item{padding:4px 10px;}
    QHeaderView::section{background:#F3F5F9;color:#4B5563;padding:8px 10px;border:none;
      border-bottom:1px solid #DDE2EC;font-weight:700;font-size:12px;}
    QTableCornerButton::section{background:#F3F5F9;border:none;}"""
    return [
        ("Чистая светлая (без сетки, зебра, без рамки фокуса)", make_table(), clean, "#FFFFFF"),
        ("Тёмная", make_table(), dark, "#1B1D23"),
        ("Сетка + цветная шапка, жёлтое выделение", make_table(row_h=30, grid=True), grid, "#FFFFFF"),
        ("Строки-линии (минимализм), крупная высота", make_table(row_h=36), rows, "#FFFFFF"),
        ("Делегат: цвет статуса из модели главнее QSS (в QSS нет ::item background)",
         make_table(colored=True, delegate=ColorDelegate), delegated, "#FFFFFF"),
        ("Без делегата: QSS-правило ::item{background} перекрывает цвета модели (виден только цвет текста)",
         make_table(colored=True),
         clean.replace("QTableWidget::item:hover{background:#F0F3FA;}", "")
              .replace("QTableWidget::item:selected{background:#E3E9FD;color:#1F2A6B;}",
                       "QTableWidget::item{background:#FFFFFF;}"), "#FFFFFF"),
    ]


# =====================================================================
#  Раздел: QMessageBox
# =====================================================================
MSG_TPL = """
QMessageBox{background:@bg@;}
QMessageBox QLabel{color:@fg@;min-width:300px;font-size:14px;background:transparent;}
QPushButton{background:@b@;color:@bf@;border:1px solid @bb@;border-radius:7px;padding:0 18px;
  min-height:32px;min-width:84px;font-weight:600;}
QPushButton:hover{background:@bh@;}"""

MSG_KINDS = {
    "light": dict(bg="#FFFFFF", fg="#1F2937", b="#4F6BED", bf="#fff", bb="#4F6BED", bh="#435DD8"),
    "dark": dict(bg="#242730", fg="#E5E7EB", b="#6C86FF", bf="#fff", bb="#6C86FF", bh="#7F96FF"),
    "danger": dict(bg="#FFF8F8", fg="#7A1F23", b="#E5484D", bf="#fff", bb="#E5484D", bh="#C93A3F"),
    "mint": dict(bg="#F2FBF6", fg="#14553A", b="#2FA36B", bf="#fff", bb="#2FA36B", bh="#278F5C"),
}


def open_box(parent, kind):
    box = QMessageBox(parent)
    box.setWindowTitle("Подтверждение")
    box.setIcon(QMessageBox.Warning if kind == "danger" else QMessageBox.Question)
    box.setText("Удалить выбранную запись?" if kind == "danger" else "Сохранить изменения?")
    box.setInformativeText("Это действие нельзя отменить." if kind == "danger" else "Данные будут записаны в базу.")
    ok = box.addButton("Удалить" if kind == "danger" else "Сохранить", QMessageBox.AcceptRole)
    box.addButton("Отмена", QMessageBox.RejectRole)
    ok.setCursor(Qt.PointingHandCursor)
    box.setStyleSheet(tpl(MSG_TPL, **MSG_KINDS[kind]))
    box.exec_()


def sec_messagebox(parent):
    items = []
    names = {"light": "Светлый (акцент индиго)", "dark": "Тёмный",
             "danger": "Опасное действие (красный)", "mint": "Мятный (зелёный)"}
    for kind, name in names.items():
        b = QPushButton("Открыть окно")
        b.clicked.connect(lambda _=False, k=kind: open_box(parent, k))
        items.append((name, b,
                      """QPushButton{background:#fff;color:#1F2937;border:1px solid #D3D9E5;border-radius:7px;
                         padding:0 18px;min-height:34px;font-weight:600;}
                         QPushButton:hover{border-color:#4F6BED;color:#4F6BED;}""", "#FFFFFF"))
    return items


# =====================================================================
#  Раздел: QMdiArea
# =====================================================================
def mdi_inner(dark=False):
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.addWidget(QLabel("Редактирование клиента"))
    lay.addWidget(QLineEdit("Анна Смирнова"))
    lay.addWidget(QCheckBox("Активен"))
    lay.addStretch(1)
    lay.addWidget(QPushButton("Сохранить"))
    if dark:
        w.setStyleSheet("""QWidget{background:#242730;color:#E5E7EB;}
            QLineEdit{background:#2B2F3A;border:1px solid #3A3F4D;border-radius:6px;padding:0 8px;min-height:28px;}
            QPushButton{background:#6C86FF;color:#fff;border:none;border-radius:6px;min-height:30px;}""")
    else:
        w.setStyleSheet("""QWidget{background:#fff;color:#1F2937;}
            QLineEdit{background:#fff;border:1px solid #D3D9E5;border-radius:6px;padding:0 8px;min-height:28px;}
            QPushButton{background:#4F6BED;color:#fff;border:none;border-radius:6px;min-height:30px;}""")
    return w


def make_mdi(kind):
    area = QMdiArea()
    area.setMinimumHeight(320)
    if kind in ("indigo", "dark"):
        dark = kind == "dark"
        style = MdiProxyStyle(title_h=32 if not dark else 28, frame=4 if not dark else 2)
        style.setParent(QApplication.instance())  # C++-владелец — приложение (иначе падение при выходе)
        area._style = style                      # и ссылка на стороне Python
        pal = QPalette(area.palette())
        if dark:
            pal.setColor(QPalette.Window, QColor("#242730"))
            pal.setColor(QPalette.WindowText, QColor("#E5E7EB"))
            pal.setColor(QPalette.Active, QPalette.Highlight, QColor("#2FA36B"))
            pal.setColor(QPalette.Inactive, QPalette.Highlight, QColor("#3A3F4D"))
            pal.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
            area.setBackground(QBrush(QColor("#15171B")))
        else:
            pal.setColor(QPalette.Window, QColor("#F3F5F9"))
            pal.setColor(QPalette.WindowText, QColor("#1F2937"))
            pal.setColor(QPalette.Active, QPalette.Highlight, QColor("#4F6BED"))
            pal.setColor(QPalette.Inactive, QPalette.Highlight, QColor("#9AA7DB"))
            pal.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
            area.setBackground(QBrush(QColor("#E9EDF4")))
        s1 = area.addSubWindow(mdi_inner(dark))
        s1.setWindowTitle("Клиент #1")
        s1.setWindowFlags(Qt.SubWindow | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        s1.resize(240, 190)
        s1.move(10, 10)
        s2 = area.addSubWindow(mdi_inner(dark))
        s2.setWindowTitle("Клиент #2")
        s2.resize(240, 190)
        s2.move(110, 70)
        for sw in (s1, s2):
            sw.setWindowIcon(QIcon(QPixmap(1, 1)))   # убираем значок Qt из заголовка
            sw.setStyle(style)                       # стиль задаём САМОМУ подокну
        # Палитру заголовка ставим ПОСЛЕ первого показа: при активном глобальном QSS
        # (QStyleSheetStyle) более ранняя палитра сбрасывается при polish.
        QTimer.singleShot(0, lambda: [sw.setPalette(pal) for sw in (s1, s2)])
        area.setActiveSubWindow(s2)
    else:
        area.setBackground(QBrush(QColor("#E9EDF4")))
        card_ = QFrame()
        card_.setObjectName("mcard")
        lay = QVBoxLayout(card_)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        bar = TitleBar("Клиент #1 — свой заголовок")
        lay.addWidget(bar)
        lay.addWidget(mdi_inner())
        sub = area.addSubWindow(card_, Qt.SubWindow | Qt.FramelessWindowHint)
        sub.setAttribute(Qt.WA_TranslucentBackground, True)
        bar.sub = sub
        bar.btn_close.clicked.connect(sub.close)
        sub.resize(260, 210)
        sub.move(14, 14)
        area.setStyleSheet("""
            #mcard{background:#fff;border:1px solid #4F6BED;border-radius:10px;}
            #mbar{background:#4F6BED;border-top-left-radius:9px;border-top-right-radius:9px;min-height:34px;max-height:34px;}
            #mbar QLabel{color:#fff;font-weight:700;background:transparent;}
            #mclose{background:transparent;color:#fff;border:none;border-radius:6px;
              min-width:26px;max-width:26px;min-height:26px;max-height:26px;padding:0;}
            #mclose:hover{background:#E5484D;}""")
    for w in area.subWindowList():
        w.show()
    return area


def sec_mdi():
    plain = ""
    return [
        ("Fusion + палитра (индиго), заголовок 32px, рамка 4px", make_mdi("indigo"), plain, "#FFFFFF"),
        ("Тёмная палитра, зелёный активный заголовок, тонкая рамка", make_mdi("dark"), plain, "#FFFFFF"),
        ("Безрамочное окно со своим заголовком (перетаскивается)", make_mdi("card"), plain, "#FFFFFF"),
    ]


# =====================================================================
#  Раздел: формы редактирования записей БД (SQLite)
# =====================================================================
FORM_TPL = """
QWidget#dbform{background:@bg@;}
QLabel{background:transparent;color:@fg@;}
QLabel#h{font-size:18px;font-weight:700;}
QLabel#f{color:@mut@;font-weight:600;}
QLabel#err{color:@dng@;font-size:12px;}
QLineEdit,QTextEdit{background:@in@;color:@fg@;border:1px solid @bd@;border-radius:7px;padding:0 10px;
  selection-background-color:@ac@;selection-color:#fff;}
QLineEdit{min-height:32px;} QTextEdit{padding:6px 8px;}
QLineEdit:focus,QTextEdit:focus{border:1px solid @ac@;}
QLineEdit[invalid="true"]{border:1px solid @dng@;}
QGroupBox{background:@pn@;border:1px solid @bd@;border-radius:10px;margin-top:14px;padding:16px 12px 12px 12px;
  font-weight:700;color:@fg@;}
QGroupBox::title{subcontrol-origin:margin;left:14px;padding:0 8px;color:@ac@;background:@bg@;}
QCheckBox{color:@fg@;spacing:8px;background:transparent;}
QCheckBox::indicator{width:18px;height:18px;border:1.5px solid @bd2@;border-radius:5px;background:@in@;}
QCheckBox::indicator:checked{background:@ac@;border-color:@ac@;}
QPushButton{background:@in@;color:@fg@;border:1px solid @bd@;border-radius:7px;padding:0 16px;
  min-height:34px;font-weight:600;}
QPushButton:hover{background:@hov@;}
QPushButton#save{background:@ac@;border-color:@ac@;color:#fff;}
QPushButton#save:hover{background:@acH@;border-color:@acH@;}
QPushButton#del{background:transparent;border-color:@dngb@;color:@dng@;}
QPushButton#del:hover{background:@dng@;border-color:@dng@;color:#fff;}
QTableWidget{background:@pn@;alternate-background-color:@alt@;border:1px solid @bd@;border-radius:8px;
  gridline-color:@grid@;selection-background-color:@sel@;selection-color:@selfg@;outline:0;color:@fg@;}
QTableWidget::item{padding:4px 8px;border:none;}
QTableWidget::item:selected{background:@sel@;color:@selfg@;}
QTableWidget::item:focus{border:none;outline:none;}
QHeaderView::section{background:@hdr@;color:@hdrfg@;padding:8px 10px;border:none;
  border-bottom:1px solid @bd@;font-weight:700;}
QTableCornerButton::section{background:@hdr@;border:none;}
QScrollBar:vertical{background:transparent;width:10px;margin:2px;}
QScrollBar::handle:vertical{background:@bd2@;min-height:24px;border-radius:4px;}
QScrollBar::add-line,QScrollBar::sub-line{height:0;}
QScrollBar::add-page,QScrollBar::sub-page{background:none;}"""

THEMES = {
    "light": dict(bg="#F3F5F9", pn="#FFFFFF", **{"in": "#FFFFFF"}, fg="#1F2937", mut="#6B7280", bd="#D3D9E5",
                  bd2="#B3BCD0", ac="#4F6BED", acH="#435DD8", hov="#F6F8FC", dng="#E5484D", dngb="#F1B8BA",
                  hdr="#F3F5F9", hdrfg="#4B5563", sel="#E3E9FD", selfg="#1F2A6B", alt="#F8FAFD", grid="#EBEEF4"),
    "dark": dict(bg="#1B1D23", pn="#242730", **{"in": "#2B2F3A"}, fg="#E5E7EB", mut="#9CA3AF", bd="#3A3F4D",
                 bd2="#50566A", ac="#6C86FF", acH="#7F96FF", hov="#343946", dng="#FF6369", dngb="#6B3036",
                 hdr="#1F222A", hdrfg="#AEB4C0", sel="#34406B", selfg="#FFFFFF", alt="#282B35", grid="#2F333F"),
    "mint": dict(bg="#F2F7F4", pn="#FFFFFF", **{"in": "#FFFFFF"}, fg="#17352A", mut="#5F7A6D", bd="#CFE1D8",
                 bd2="#A9C5B7", ac="#2FA36B", acH="#278F5C", hov="#F0F8F4", dng="#E5484D", dngb="#F1B8BA",
                 hdr="#E7F1EB", hdrfg="#3F6150", sel="#DDF1E6", selfg="#14553A", alt="#F7FBF9", grid="#E3EFE8"),
}

SEED = [
    ("Анна Смирнова", "+7 900 111-22-33", "anna@mail.ru", "Постоянный клиент", 1),
    ("Борис Лебедев", "+7 900 222-33-44", "boris@mail.ru", "", 1),
    ("Вера Орлова", "+7 900 333-44-55", "vera@mail.ru", "Просит звонить после 18:00", 0),
    ("Глеб Кузнецов", "+7 900 444-55-66", "gleb@mail.ru", "", 1),
]


class DbForm(QWidget):
    """Список записей + форма редактирования. БД — SQLite в памяти."""

    def __init__(self, theme):
        super().__init__()
        self.setObjectName("dbform")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.cur = None
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE c(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, "
                        "phone TEXT, email TEXT, note TEXT, active INTEGER DEFAULT 1)")
        self.db.executemany("INSERT INTO c(name,phone,email,note,active) VALUES(?,?,?,?,?)", SEED)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ID", "Имя", "Телефон"])
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.on_select)

        self.name = QLineEdit()
        self.name.setPlaceholderText("Имя *")
        self.phone = QLineEdit()
        self.email = QLineEdit()
        self.note = QTextEdit()
        self.note.setFixedHeight(80)
        self.active = QCheckBox("Активен")
        self.err = L("", "err")

        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        for t, w in (("Имя", self.name), ("Телефон", self.phone), ("E-mail", self.email), ("Заметка", self.note)):
            form.addRow(L(t, "f"), w)
        form.addRow("", self.active)
        grp = QGroupBox("Карточка клиента")
        grp.setLayout(form)

        b_new, b_del, b_save = QPushButton("Новый"), QPushButton("Удалить"), QPushButton("Сохранить")
        b_del.setObjectName("del")
        b_save.setObjectName("save")
        b_new.clicked.connect(self.new)
        b_del.clicked.connect(self.delete)
        b_save.clicked.connect(self.save)
        bar = QHBoxLayout()
        bar.addWidget(b_del)
        bar.addStretch(1)
        bar.addWidget(b_new)
        bar.addWidget(b_save)

        right = QVBoxLayout()
        right.addWidget(grp)
        right.addWidget(self.err)
        right.addLayout(bar)
        left = QVBoxLayout()
        left.addWidget(L("Клиенты", "h"))
        left.addWidget(self.table)
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(18)
        root.addLayout(left, 5)
        root.addLayout(right, 6)
        self.setMinimumHeight(380)
        self.setStyleSheet(tpl(FORM_TPL, **THEMES[theme]))
        self.reload()

    def reload(self, select_id=None):
        rows = self.db.execute("SELECT id,name,phone FROM c ORDER BY id").fetchall()
        self.table.blockSignals(True)
        self.table.setRowCount(len(rows))
        for r, rec in enumerate(rows):
            for c, v in enumerate(rec):
                self.table.setItem(r, c, QTableWidgetItem(str(v or "")))
        self.table.blockSignals(False)
        target = select_id or self.cur
        for r, rec in enumerate(rows):
            if rec[0] == target:
                self.table.selectRow(r)
                return
        if rows:
            self.table.selectRow(0)
        else:
            self.new()

    def _mark(self, bad):
        self.name.setProperty("invalid", bad)
        self.name.style().unpolish(self.name)
        self.name.style().polish(self.name)

    def on_select(self):
        r = self.table.currentRow()
        if r < 0 or not self.table.selectedItems():
            return
        rid = int(self.table.item(r, 0).text())
        row = self.db.execute("SELECT name,phone,email,note,active FROM c WHERE id=?", (rid,)).fetchone()
        self.cur = rid
        self.name.setText(row[0])
        self.phone.setText(row[1] or "")
        self.email.setText(row[2] or "")
        self.note.setPlainText(row[3] or "")
        self.active.setChecked(bool(row[4]))
        self._mark(False)
        self.err.setText("")

    def new(self):
        self.cur = None
        self.table.blockSignals(True)            # иначе clearSelection() перезагрузит старую строку
        self.table.clearSelection()
        self.table.setCurrentCell(-1, -1)
        self.table.blockSignals(False)
        for w in (self.name, self.phone, self.email):
            w.clear()
        self.note.clear()
        self.active.setChecked(True)
        self._mark(False)
        self.err.setText("")
        self.name.setFocus()

    def save(self):
        name = self.name.text().strip()
        self._mark(not name)
        if not name:
            self.err.setText("Укажите имя клиента")
            return
        self.err.setText("")
        args = (name, self.phone.text(), self.email.text().strip(), self.note.toPlainText(),
                int(self.active.isChecked()))
        if self.cur is None:
            cur = self.db.execute("INSERT INTO c(name,phone,email,note,active) VALUES(?,?,?,?,?)", args)
            self.cur = cur.lastrowid
        else:
            self.db.execute("UPDATE c SET name=?,phone=?,email=?,note=?,active=? WHERE id=?", args + (self.cur,))
        self.reload(self.cur)

    def delete(self):
        if self.cur is None:
            return
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Удаление")
        box.setText("Удалить выбранную запись?")
        yes = box.addButton("Удалить", QMessageBox.AcceptRole)
        no = box.addButton("Отмена", QMessageBox.RejectRole)
        box.setDefaultButton(no)
        box.setStyleSheet(tpl(MSG_TPL, **MSG_KINDS["danger"]))
        box.exec_()
        if box.clickedButton() is yes:
            self.db.execute("DELETE FROM c WHERE id=?", (self.cur,))
            self.cur = None
            self.reload()


def sec_forms():
    return [("Светлая тема — добавить / изменить / удалить / валидация", DbForm("light"), "", "#FFFFFF"),
            ("Тёмная тема", DbForm("dark"), "", "#FFFFFF"),
            ("Мятная тема", DbForm("mint"), "", "#FFFFFF")]


# =====================================================================
#  Фон страницы (светлый / тёмный)
# =====================================================================
PAGE_QSS = """
QMainWindow,QScrollArea,#page{background:@bg@;}
#card{background:@cd@;border:1px solid @bd@;border-radius:12px;}
QLabel#pageTitle{font-size:28px;font-weight:800;color:@fg@;}
QLabel#pageSub{color:@mut@;font-size:14px;}
QLabel#secTitle{font-size:21px;font-weight:700;color:@fg@;}
QLabel#secDesc{color:@mut@;}
QLabel#varName{color:@mut@;font-size:11px;font-weight:700;}
QCheckBox#themeToggle{color:@fg@;}
QComboBox#jump{background:@cd@;color:@fg@;border:1px solid @bd@;border-radius:7px;padding:0 10px;min-height:32px;min-width:200px;}
QComboBox#jump QAbstractItemView{background:@cd@;color:@fg@;border:1px solid @bd@;selection-background-color:#4F6BED;selection-color:#fff;}
QScrollBar:vertical{background:transparent;width:12px;margin:2px;}
QScrollBar::handle:vertical{background:@sb@;min-height:30px;border-radius:4px;}
QScrollBar::add-line,QScrollBar::sub-line{height:0;}
QScrollBar::add-page,QScrollBar::sub-page{background:none;}"""
PAGE_LIGHT = tpl(PAGE_QSS, bg="#EEF1F6", cd="#FFFFFF", bd="#DDE2EC", fg="#111827", mut="#6B7280", sb="#C5CCDB")
PAGE_DARK = tpl(PAGE_QSS, bg="#111317", cd="#1E2128", bd="#2E323D", fg="#F3F4F6", mut="#9CA3AF", sb="#444A5A")


# =====================================================================
#  Главное окно
# =====================================================================
class Showcase(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt5 QSS — витрина виджетов")
        self.resize(1240, 860)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        page = QWidget()
        page.setObjectName("page")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 26, 32, 40)
        lay.setSpacing(34)

        jump = QComboBox()
        jump.setObjectName("jump")
        theme = ToggleSwitch("Тёмный фон страницы", on="#6C86FF")
        theme.setObjectName("themeToggle")
        theme.toggled.connect(self.set_dark)
        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.addWidget(L("Витрина QSS-стилей PyQt5", "pageTitle"))
        titles.addWidget(L("Прокручивайте страницу: у каждого виджета несколько вариантов оформления. "
                           "Наведите курсор на кнопки, кликайте по таблицам, чекбоксам и формам.", "pageSub", wrap=True))
        head.addLayout(titles, 1)
        head.addWidget(jump)
        head.addWidget(theme)
        lay.addLayout(head)

        sections = [
            ("QLabel — надписи, бейджи, баннеры", "Заголовки, статусы, подсказки, ошибки.", sec_labels(), 2),
            ("QLineEdit — поля ввода", "От контурных до «пилюль», состояние ошибки и пример, как НЕ надо делать "
             "(текст обрезается из-за padding).", sec_lineedit(), 3),
            ("QTextEdit — многострочный ввод", "Светлый, тёмный и вариант с убранными внутренними отступами.",
             sec_textedit(), 3),
            ("QPushButton — кнопки и hover-эффекты", "Обычные QSS-кнопки и классы с анимацией: Bubble и Lift "
             "(анимации в чистом QSS невозможны).", sec_buttons(), 3),
            ("QGroupBox — группы", "Заголовок на линии, вкладка, минимализм, тёмная карточка.", sec_groupbox(), 2),
            ("QCheckBox / QRadioButton / переключатель", "Индикаторы через ::indicator и кастомный ToggleSwitch.",
             sec_checks(), 3),
            ("QComboBox / QSpinBox / QDateEdit", "Один набор полей в трёх стилях.", sec_combos(), 3),
            ("QTableWidget — таблицы", "Без рамки фокуса, редактор ячейки (двойной клик) без обрезки текста, "
             "делегат с приоритетом цветов модели.", sec_tables(), 2),
            ("QMessageBox — диалоги", "Стиль задаётся на самом окне сообщения.", sec_messagebox(self), 4),
            ("QMdiArea — окна: рамки, заголовки, кнопки", "Заголовок красится палитрой и QProxyStyle; "
             "или рисуется свой.", sec_mdi(), 2),
            ("Формы редактирования записей БД (SQLite)", "Рабочие примеры: выберите строку, измените, "
             "сохраните; «Новый», «Удалить», проверка пустого имени.", sec_forms(), 1),
        ]
        self.anchors = []
        for title, desc, items, cols in sections:
            s = section(title, desc, items, cols)
            lay.addWidget(s)
            self.anchors.append(s)
            jump.addItem(title.split(" — ")[0])
        lay.addStretch(1)
        jump.activated.connect(lambda i: self.scroll.verticalScrollBar().setValue(self.anchors[i].y() - 10))

        self.scroll.setWidget(page)
        self.setCentralWidget(self.scroll)

    def set_dark(self, on):
        QApplication.instance().setStyleSheet(PAGE_DARK if on else PAGE_LIGHT)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(PAGE_LIGHT)
    w = Showcase()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()