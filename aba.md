# Стилизация виджетов PyQt5 с помощью QSS (Qt Style Sheets)

QSS похож на CSS, но имеет свои особенности: работает через **селекторы виджетов**, псевдо-состояния (`:hover`, `:pressed` и т.д.) и подконтролы (`::sub-control`). Ниже — разбор возможностей для каждого виджета.

---

## Общие свойства (применимы почти ко всем виджетам)

```css
QWidget {
    background-color: #2b2b2b;
    color: #ffffff;
    border: 1px solid #555;
    border-radius: 6px;
    padding: 4px;
    margin: 2px;
    font-family: "Segoe UI";
    font-size: 14px;
    font-weight: bold;
}
```

Псевдо-состояния, которые работают почти везде:
- `:hover` — курсор над виджетом
- `:pressed` — нажатие
- `:focus` — в фокусе
- `:disabled` / `:enabled`
- `:checked` / `:unchecked`

---

## 1. QLineEdit (однострочное поле ввода)

Можно менять:
- `background-color`, `color` — фон и цвет текста
- `border`, `border-radius` — рамка и скругление
- `padding` — внутренние отступы (влияет на положение текста)
- `selection-background-color`, `selection-color` — цвет выделенного текста
- `font-*` — шрифт

```css
QLineEdit {
    background-color: #3c3f41;
    color: #dcdcdc;
    border: 1px solid #5c5c5c;
    border-radius: 4px;
    padding: 3px 6px;
    selection-background-color: #3399ff;
}
QLineEdit:focus {
    border: 1px solid #3399ff;
}
QLineEdit:disabled {
    color: #888888;
    background-color: #2a2a2a;
}
QLineEdit[readOnly="true"] {
    background-color: #333333;
}
```

> Можно даже стилизовать иконку очистки через `QLineEdit QToolButton`.

---

## 2. QTextEdit / QPlainTextEdit (многострочное поле)

Аналогично QLineEdit, но дополнительно можно стилизовать **полосы прокрутки**, так как это составной виджет.

```css
QTextEdit {
    background-color: #1e1e1e;
    color: #d4d4d4;
    border: 1px solid #444;
    border-radius: 5px;
    padding: 6px;
    selection-background-color: #264f78;
}

/* Скроллбар внутри QTextEdit */
QTextEdit QScrollBar:vertical {
    background: #2b2b2b;
    width: 10px;
}
QTextEdit QScrollBar::handle:vertical {
    background: #5c5c5c;
    border-radius: 5px;
}
```

Важно: свойства типа `line-height` в QSS **не поддерживаются** — интерлиньяж настраивается через `QTextCharFormat` в коде, не через QSS.

---

## 3. QPushButton (кнопка)

Самый гибкий виджет — поддерживает подконтролы и множество состояний.

```css
QPushButton {
    background-color: #4a90d9;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 6px 16px;
    min-width: 80px;
    min-height: 24px;
}
QPushButton:hover {
    background-color: #5aa0e9;
}
QPushButton:pressed {
    background-color: #3a80c9;
    padding-top: 8px; /* эффект "утапливания" */
}
QPushButton:disabled {
    background-color: #7f7f7f;
    color: #cccccc;
}
QPushButton:checked {
    background-color: #2ecc71; /* если setCheckable(True) */
}
QPushButton:flat {
    border: none;
    background: transparent;
}

/* Стрелка меню у кнопки (если QMenu назначен) */
QPushButton::menu-indicator {
    subcontrol-position: right center;
    right: 8px;
}
```

Также можно задать **градиенты**:
```css
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #6fb1fc, stop:1 #4a90d9);
}
```

---

## 4. QLabel (текстовая/графическая метка)

```css
QLabel {
    color: #ffffff;
    font-size: 16px;
    font-style: italic;
    background-color: transparent;
    border: none;
    qproperty-alignment: AlignCenter; /* выравнивание через свойство Qt */
}
QLabel:disabled {
    color: #999999;
}
```

- Можно задать `border-image` или `background-image` для декоративных подложек.
- `qproperty-*` — специальный синтаксис QSS для установки свойств Qt (не CSS-стандарт), например `qproperty-pixmap`, `qproperty-wordWrap`.

---

## 5. QLayout (важный нюанс!)

**QLayout напрямую через QSS стилизовать нельзя** — это не виджет, а объект компоновки, у него нет `paintEvent`. QSS применяется только к `QWidget` и его потомкам.

Что можно сделать вместо этого:
- Настроить отступы **в коде**: `layout.setContentsMargins()`, `layout.setSpacing()`
- Стилизовать **контейнер**, в который вложен layout (например, `QWidget` или `QGroupBox`, на котором сделан `setLayout()`):
```css
#containerWidget {
    background-color: #333;
    border-radius: 10px;
    padding: 10px;
}
```
Через `objectName` и `padding` контейнера можно визуально имитировать отступы layout'а.

---

## 6. QGroupBox (группирующая рамка с заголовком)

Составной виджет — есть подконтрол `::title`.

```css
QGroupBox {
    background-color: #2b2b2b;
    border: 2px solid #5c5c5c;
    border-radius: 8px;
    margin-top: 12px; /* место для заголовка */
    padding-top: 10px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 5px;
    color: #4a90d9;
    background-color: #2b2b2b; /* перекрывает рамку под текстом */
}
QGroupBox::indicator {
    /* если checkable(True) — стилизация чекбокса заголовка */
    width: 14px;
    height: 14px;
}
```

---

## 7. QTableWidget (таблица)

Самый сложный по количеству подконтролов виджет: сама таблица, заголовки, ячейки, скроллбары — стилизуются отдельно.

```css
QTableWidget {
    background-color: #1e1e1e;
    gridline-color: #444444;   /* цвет линий сетки */
    color: #e0e0e0;
    border: 1px solid #444;
    selection-background-color: #3399ff; /* выделенные ячейки */
    selection-color: #ffffff;
    alternate-background-color: #262626; /* если setAlternatingRowColors(True) */
}

/* Заголовки столбцов/строк */
QHeaderView::section {
    background-color: #3c3f41;
    color: #ffffff;
    padding: 4px;
    border: 1px solid #555;
    font-weight: bold;
}
QHeaderView::section:checked {
    background-color: #4a90d9; /* выбранный заголовок */
}

/* Угловая кнопка (пересечение заголовков) */
QTableCornerButton::section {
    background-color: #3c3f41;
    border: 1px solid #555;
}

/* Отдельные элементы (при желании через delegate/item) */
QTableWidget::item {
    padding: 4px;
    border: none;
}
QTableWidget::item:selected {
    background-color: #3399ff;
    color: white;
}
QTableWidget::item:hover {
    background-color: #2f4f4f;
}
```

---

## Полезные общие возможности QSS

| Возможность | Пример |
|---|---|
| Селектор по имени объекта | `QPushButton#myButton { ... }` |
| Селектор по свойству | `QLineEdit[echoMode="2"] { ... }` |
| Наследование от базового класса | `QAbstractButton { ... }` затронет QPushButton и QCheckBox |
| Иконки/изображения | `border-image`, `background-image: url(:/icons/x.png);` |
| Скругления только с одной стороны | `border-top-left-radius: 10px;` |
| Курсор | нельзя через QSS — только `setCursor()` в коде |

---

### Итог по ограничениям QSS
- Не поддерживаются: `line-height`, `box-shadow` (частично, только через `QGraphicsDropShadowEffect` в коде), CSS-анимации/transition.
- Layout стилизуется только через контейнер-виджет, а не напрямую.
- Составные виджеты (QGroupBox, QTableWidget, QScrollBar, QComboBox) требуют использования `::sub-control` для доступа к внутренним частям.

Если нужно — могу собрать это всё в единый готовый `.qss`-файл с полной темной темой под все эти виджеты.