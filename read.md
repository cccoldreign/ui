Да, вот именно те функции, которые тебе нужны.

## 1. В `__init__()` добавить

```python
self._double_click_callbacks = double_click_callbacks or {}
self._always_new_row = always_new_row

self._new_rows = []
```

---

## 2. В `_build_ui()`

После

```python
self.table.currentCellChanged.connect(self._on_current_cell_changed)
```

добавить

```python
self.table.cellDoubleClicked.connect(self._on_double_click)
```

---

# 3. Новый обработчик двойного клика

```python
def _on_double_click(self, row: int, column: int) -> None:
    """
    Вызывает внешнюю функцию, если для данного столбца
    зарегистрирован обработчик двойного клика.
    """

    callback = self._double_click_callbacks.get(column)

    if callback is None:
        return

    if row >= len(self._current_values):
        return

    value = ""

    if column < len(self._current_values[row]):
        value = self._current_values[row][column]

    callback(
        row=row,
        column=column,
        value=value,
        row_data=self._current_values[row]
    )
```

---

Использование

```python
def open_client(**data):

    print(data["row"])
    print(data["column"])
    print(data["value"])
    print(data["row_data"])


table = UniversalTable(

    double_click_callbacks={
        0: open_client
    }

)
```

или

```python
table = UniversalTable(

    double_click_callbacks={
        3: lambda **x: print(x["row_data"])
    }

)
```

---

# 4. Добавление пустой строки

```python
def _add_empty_row(self) -> None:
    """
    Добавляет последнюю пустую строку.
    """

    row = self.table.rowCount()

    self.table.insertRow(row)

    values = []

    for col in range(self._data_column_count):

        item = QTableWidgetItem("")
        self.table.setItem(row, col, item)

        values.append("")

    self._current_values.append(values)

    if self._button_column_index is not None:
        self.table.setCellWidget(row, self._button_column_index, QWidget())
```

---

# 5. Получить новые строки

```python
def get_new_rows(self):
    """
    Возвращает все новые записи.
    """

    return list(self._new_rows)
```

---

# 6. Кусок для `_on_item_changed()`

Сразу после

```python
new_value = item.text()
```

вставить

```python
# Последняя строка предназначена для новой записи

is_last_row = (row == self.table.rowCount() - 1)

# Пользователь начал ввод новой записи

if self._always_new_row and is_last_row:

    if any(cell != "" for cell in self._current_values[row]):

        self._new_rows.append({

            "type": "insert",

            "row": row,

            "values": list(self._current_values[row])

        })

        self._add_empty_row()
```

---

# 7. Вместо старого change

```python
change = {

    "type": "update",

    "row": row,

    "column": column,

    "old": old_value,

    "new": new_value

}
```

---

# 8. Если это новая строка

После

```python
self._current_values[row][column] = new_value
```

вставить

```python
for record in self._new_rows:

    if record["row"] == row:

        record["values"] = list(self._current_values[row])

        change = {

            "type": "insert",

            "row": row,

            "values": list(self._current_values[row])

        }

        self.dataChangedSignal.emit(change)

        return
```

---

### Я бы ещё немного улучшил эту логику.

Сейчас `_new_rows` хранит **индексы строк**, а это не очень надёжно: если позже появятся удаление или сортировка, индексы изменятся. Лучше хранить у строки скрытый флаг вроде `self._is_new_row[row]` или использовать уникальный внутренний идентификатор. Тогда механизм вставки останется корректным даже после будущих расширений компонента.


Я бы сделал её отдельной, чтобы можно было вызывать после `set_data()` в любой момент.

### В `__init__`

```python
self._column_widths = column_widths or {}
```

---

### Полная функция

```python
def set_column_widths(self, column_widths: Dict[int, int]) -> None:
    """
    Устанавливает фиксированную ширину выбранных столбцов.

    Parameters
    ----------
    column_widths : dict

        {
            0: 60,
            1: 250,
            3: 120
        }

    Столбцы, отсутствующие в словаре, не изменяются.
    """

    self._column_widths = dict(column_widths)

    header = self.table.horizontalHeader()

    for column, width in self._column_widths.items():

        if column >= self.table.columnCount():
            continue

        header.setSectionResizeMode(column, QHeaderView.Fixed)
        self.table.setColumnWidth(column, width)
```

---

### И небольшая функция применения после загрузки данных

В конце `set_data()` добавить

```python
self._apply_column_widths()
```

а сама функция

```python
def _apply_column_widths(self) -> None:
    """
    Применяет сохранённые ширины столбцов.
    Вызывается автоматически после set_data().
    """

    if not self._column_widths:
        return

    header = self.table.horizontalHeader()

    for column, width in self._column_widths.items():

        if column >= self.table.columnCount():
            continue

        header.setSectionResizeMode(column, QHeaderView.Fixed)
        self.table.setColumnWidth(column, width)
```

---

### Использование

```python
table = UniversalTable()

table.set_data(rows)

table.set_column_widths({

    0: 60,
    1: 300,
    2: 120,
    5: 80

})
```

Или сразу через конструктор:

```python
table = UniversalTable(

    column_widths={
        0: 60,
        1: 300,
        2: 120
    }

)
```

После каждого `set_data()` ширины автоматически восстановятся. Это удобнее, чем вручную задавать их после каждой перезагрузки данных.
