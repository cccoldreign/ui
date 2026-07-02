# -*- coding: utf-8 -*-
"""
universal_table.py
===================

Универсальный, переиспользуемый компонент таблицы на PyQt5.

Компонент предназначен для того, чтобы в будущем полностью заменить область
отображения данных Microsoft Access в существующем приложении. На данном
этапе никакой работы с базой данных не производится — все методы,
связанные с БД (загрузка, сохранение, вставка, удаление, обновление),
реализованы в виде "заглушек" с подробными docstring, описывающими их
будущее поведение.

Компонент ничего не знает о pyodbc, SQL, Access, UPDATE/INSERT/DELETE —
он занимается исключительно отображением данных и отслеживанием
изменений, внесённых пользователем. Взаимодействие с внешним миром
происходит только через публичный API (методы и сигналы), что позволяет
использовать этот класс в любом другом PyQt5-проекте без изменения его
внутреннего кода.

Основные возможности:
    * приём данных в формате, который возвращает pyodbc (list[tuple]);
    * многократная загрузка новых наборов данных без пересоздания виджета;
    * отслеживание изменений ячеек (строка, столбец, старое и новое значение);
    * сигнал смены активной строки (для последующего UPDATE конкретной записи);
    * сигнал изменения данных (для реакции на правки "на лету");
    * столбцы с датой (редактор-календарь);
    * столбцы-списки (редактируемый ComboBox с произвольными вариантами);
    * автоматическая кнопка в последнем столбце каждой строки, которая
      передаёт во внешнюю функцию значение первого столбца строки
      (идентификатор записи).

Автор: сгенерировано по техническому заданию.
"""

from __future__ import annotations

from functools import partial
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from PyQt5.QtCore import QDate, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QHeaderView,
    QPushButton,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


# --------------------------------------------------------------------------- #
#  Делегаты редактирования ячеек
# --------------------------------------------------------------------------- #


class _DateColumnDelegate(QStyledItemDelegate):
    """
    Делегат редактирования для столбцов типа "дата".

    Открывает QDateEdit со всплывающим календарём (calendarPopup=True).
    Если в ячейке нет значения либо оно не распознано как дата, редактор
    открывается с текущей датой по умолчанию.

    Формат хранения/отображения даты в ячейке: "yyyy-MM-dd".
    """

    DATE_FORMAT = "yyyy-MM-dd"

    #: Дополнительные форматы, которые делегат пытается распознать при
    #: разборе уже имеющегося в ячейке текста (для совместимости с данными,
    #: которые могли прийти из Access в ином виде).
    _PARSE_FORMATS = ("yyyy-MM-dd", "dd.MM.yyyy", "MM/dd/yyyy", "dd-MM-yyyy")

    def createEditor(self, parent, option, index):  # noqa: N802 (Qt naming)
        editor = QDateEdit(parent)
        editor.setCalendarPopup(True)
        editor.setDisplayFormat(self.DATE_FORMAT)
        return editor

    def setEditorData(self, editor: QDateEdit, index):  # noqa: N802
        text = index.model().data(index, Qt.EditRole) or ""
        parsed_date = self._parse_date(text)
        editor.setDate(parsed_date if parsed_date.isValid() else QDate.currentDate())

    def setModelData(self, editor: QDateEdit, model, index):  # noqa: N802
        model.setData(index, editor.date().toString(self.DATE_FORMAT), Qt.EditRole)

    def _parse_date(self, text: str) -> QDate:
        text = str(text).strip()
        if not text:
            return QDate()
        for fmt in self._PARSE_FORMATS:
            date = QDate.fromString(text, fmt)
            if date.isValid():
                return date
        return QDate()


class _ComboColumnDelegate(QStyledItemDelegate):
    """
    Делегат редактирования для столбцов типа "список" (ComboBox).

    Пользователь может выбрать одно из предложенных значений либо ввести
    собственное значение вручную, так как ComboBox создаётся editable=True.

    Параметры
    ---------
    options:
        Список строковых вариантов, которые будут доступны в выпадающем
        списке.
    """

    def __init__(self, options: Sequence[str], parent=None):
        super().__init__(parent)
        self._options = list(options)

    def createEditor(self, parent, option, index):  # noqa: N802
        editor = QComboBox(parent)
        editor.setEditable(True)
        editor.addItems(self._options)
        return editor

    def setEditorData(self, editor: QComboBox, index):  # noqa: N802
        text = index.model().data(index, Qt.EditRole) or ""
        pos = editor.findText(str(text))
        if pos >= 0:
            editor.setCurrentIndex(pos)
        else:
            editor.setEditText(str(text))

    def setModelData(self, editor: QComboBox, model, index):  # noqa: N802
        model.setData(index, editor.currentText(), Qt.EditRole)


# --------------------------------------------------------------------------- #
#  Основной компонент
# --------------------------------------------------------------------------- #


class UniversalTable(QWidget):
    """
    Универсальный компонент таблицы для отображения и редактирования
    табличных данных, полученных в формате, аналогичном результату
    выполнения запроса через pyodbc (list[tuple]).

    Компонент представляет собой QWidget-обёртку над внутренним
    QTableWidget и предоставляет наружу только собственный публичный API
    (методы и сигналы), не раскрывая внутреннюю модель Qt.

    Сигналы
    -------
    rowChanged(int, object)
        Испускается при смене активной (текущей) строки таблицы.
        Аргументы: индекс новой активной строки, идентификатор записи
        (значение первого столбца этой строки, либо None, если строка
        пуста / недоступна).

    dataChangedSignal(dict)
        Испускается после любого изменения значения в ячейке таблицы.
        Аргумент — словарь вида::

            {
                "row": <int>,
                "column": <int>,
                "old": <str>,
                "new": <str>,
            }

    Параметры конструктора
    -----------------------
    date_columns:
        Список индексов столбцов (0-based, в системе координат исходных
        данных, БЕЗ учёта служебного столбца с кнопкой), которые должны
        редактироваться через календарь.

    combo_columns:
        Словарь {индекс_столбца: [варианты...]} для столбцов-списков.
        Индексы — в той же системе координат, что и date_columns.

    row_button_callback:
        Внешняя функция вида ``callback(record_id: Any) -> None``,
        которая будет вызвана при нажатии кнопки в служебном столбце
        соответствующей строки. В качестве record_id передаётся значение
        первого столбца (столбца с индексом 0) строки, на которой была
        нажата кнопка.

    button_text:
        Текст, отображаемый на кнопке в служебном столбце. По умолчанию
        "Выбрать".

    column_headers:
        Необязательный список заголовков столбцов (без учёта служебного
        столбца кнопки). Если не передан, используются общие заголовки
        вида "Столбец 0", "Столбец 1", ...

    parent:
        Родительский виджет (стандартный параметр QWidget).

    Пример использования
    ---------------------
    >>> table = UniversalTable(
    ...     date_columns=[2],
    ...     combo_columns={3: ["Да", "Нет"]},
    ...     row_button_callback=lambda record_id: print("Выбрана запись", record_id),
    ... )
    >>> table.set_data([
    ...     (1, "Иван", "2024-01-01", "Да"),
    ...     (2, "Петр", "2023-05-12", "Нет"),
    ... ])
    >>> table.rowChanged.connect(lambda row, rec_id: print(row, rec_id))
    >>> table.dataChangedSignal.connect(lambda change: print(change))
    >>> changes = table.get_changes()
    """

    rowChanged = pyqtSignal(int, object)
    dataChangedSignal = pyqtSignal(dict)

    #: Текст кнопки по умолчанию в служебном столбце.
    DEFAULT_BUTTON_TEXT = "Выбрать"

    def __init__(
        self,
        date_columns: Optional[Sequence[int]] = None,
        combo_columns: Optional[Dict[int, Sequence[str]]] = None,
        row_button_callback: Optional[Callable[[Any], None]] = None,
        button_text: str = DEFAULT_BUTTON_TEXT,
        column_headers: Optional[Sequence[str]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self._date_columns: set = set(date_columns or [])
        self._combo_columns: Dict[int, List[str]] = {
            col: list(options) for col, options in (combo_columns or {}).items()
        }
        self._row_button_callback = row_button_callback
        self._button_text = button_text
        self._column_headers = list(column_headers) if column_headers else None

        # Количество "содержательных" столбцов данных (без служебного
        # столбца с кнопкой). Устанавливается при каждом вызове set_data.
        self._data_column_count: int = 0

        # Снимок текущих (актуальных, с учётом правок) значений таблицы.
        # Используется для сравнения при вычислении изменений.
        # Формат: List[List[str]] — [строка][столбец]
        self._current_values: List[List[str]] = []

        # Список зафиксированных изменений.
        self._changes: List[Dict[str, Any]] = []

        # Индекс столбца, зарезервированного под кнопку (None, если кнопки
        # не используются).
        self._button_column_index: Optional[int] = None

        self._build_ui()

    # ------------------------------------------------------------------ #
    #  Построение интерфейса
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        """Создаёт внутренний QTableWidget и размещает его в layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(self)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)  # важно для стабильности кнопок/индексов строк
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)

        self.table.itemChanged.connect(self._on_item_changed)
        self.table.currentCellChanged.connect(self._on_current_cell_changed)

        layout.addWidget(self.table)

    # ------------------------------------------------------------------ #
    #  Публичный API — данные
    # ------------------------------------------------------------------ #

    def set_data(self, rows: List[Tuple[Any, ...]]) -> None:
        """
        Полностью заменяет содержимое таблицы новым набором данных.

        Метод можно вызывать сколько угодно раз подряд — каждый вызов
        полностью очищает предыдущее содержимое таблицы и список
        накопленных изменений, после чего заполняет таблицу заново. Сам
        виджет таблицы при этом НЕ пересоздаётся.

        Параметры
        ---------
        rows:
            Список кортежей с данными, в формате, аналогичном результату
            выполнения запроса через pyodbc, например::

                [
                    (1, "Иван", 25),
                    (2, "Петр", 30),
                ]

            Все кортежи должны иметь одинаковую длину. Пустой список
            допустим — в этом случае таблица будет просто очищена.

        Возвращает
        ----------
        None
        """
        self.table.blockSignals(True)
        try:
            self.table.clear()
            self._changes = []
            self._current_values = []

            if not rows:
                self._data_column_count = 0
                self.table.setRowCount(0)
                self.table.setColumnCount(0)
                self._button_column_index = None
                return

            self._data_column_count = len(rows[0])
            has_button_column = self._row_button_callback is not None
            total_columns = self._data_column_count + (1 if has_button_column else 0)
            self._button_column_index = (
                self._data_column_count if has_button_column else None
            )

            self.table.setRowCount(len(rows))
            self.table.setColumnCount(total_columns)
            self.table.setHorizontalHeaderLabels(self._build_headers(has_button_column))

            for row_index, row_data in enumerate(rows):
                row_values: List[str] = []
                for col_index, value in enumerate(row_data):
                    text_value = "" if value is None else str(value)
                    row_values.append(text_value)

                    item = QTableWidgetItem(text_value)
                    self.table.setItem(row_index, col_index, item)

                    self._apply_delegate_if_needed(col_index)

                self._current_values.append(row_values)

                if has_button_column:
                    self._install_row_button(row_index, row_data[0])
        finally:
            self.table.blockSignals(False)

    def get_changes(self) -> List[Dict[str, Any]]:
        """
        Возвращает список всех изменений, внесённых пользователем с
        момента последней загрузки данных методом set_data() (или с
        момента создания таблицы).

        Возвращает
        ----------
        List[Dict[str, Any]]
            Список словарей вида::

                [
                    {"row": 5, "column": 2, "old": "Иван", "new": "Петр"},
                    ...
                ]

            где "row" и "column" — индексы строки/столбца (0-based, в
            системе координат исходных данных), "old" и "new" — старое и
            новое строковое значение ячейки.
        """
        return list(self._changes)

    def clear_changes(self) -> None:
        """
        Очищает накопленный список изменений без изменения самих данных
        в таблице. Полезно вызывать, например, после успешного
        сохранения изменений в базу данных, чтобы не отправлять их
        повторно.

        Возвращает
        ----------
        None
        """
        self._changes = []

    def get_current_row_id(self) -> Optional[Any]:
        """
        Возвращает идентификатор (значение первого столбца) текущей
        активной строки таблицы, либо None, если ни одна строка не
        выбрана.

        Возвращает
        ----------
        Optional[Any]
        """
        row = self.table.currentRow()
        if row < 0 or row >= len(self._current_values):
            return None
        return self._current_values[row][0] if self._current_values[row] else None

    # ------------------------------------------------------------------ #
    #  Внутренняя обработка событий
    # ------------------------------------------------------------------ #

    def _build_headers(self, has_button_column: bool) -> List[str]:
        """Формирует список заголовков столбцов таблицы."""
        if self._column_headers and len(self._column_headers) == self._data_column_count:
            headers = list(self._column_headers)
        else:
            headers = [f"Столбец {i}" for i in range(self._data_column_count)]

        if has_button_column:
            headers.append("")
        return headers

    def _apply_delegate_if_needed(self, column_index: int) -> None:
        """Назначает специальный делегат редактирования для столбца, если
        он объявлен как столбец даты или столбец-список."""
        if column_index in self._date_columns:
            self.table.setItemDelegateForColumn(
                column_index, _DateColumnDelegate(self.table)
            )
        elif column_index in self._combo_columns:
            self.table.setItemDelegateForColumn(
                column_index,
                _ComboColumnDelegate(self._combo_columns[column_index], self.table),
            )

    def _install_row_button(self, row_index: int, record_id: Any) -> None:
        """Создаёт и устанавливает кнопку в служебном столбце строки."""
        button = QPushButton(self._button_text)
        button.clicked.connect(partial(self._on_row_button_clicked, row_index))
        self.table.setCellWidget(row_index, self._button_column_index, button)

    def _on_row_button_clicked(self, row_index: int) -> None:
        """
        Обработчик нажатия кнопки в строке. Определяет актуальное (с
        учётом возможных правок пользователя) значение первого столбца
        этой строки и передаёт его во внешнюю функцию row_button_callback.
        """
        if self._row_button_callback is None:
            return
        if row_index >= len(self._current_values):
            return
        record_id = self._current_values[row_index][0]
        self._row_button_callback(record_id)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        """
        Обработчик изменения содержимого ячейки. Сравнивает новое
        значение со значением, сохранённым во внутреннем снимке
        (self._current_values), фиксирует изменение и испускает сигнал
        dataChangedSignal.
        """
        row = item.row()
        column = item.column()

        # Игнорируем служебный столбец с кнопкой (там нет QTableWidgetItem
        # с текстовыми данными, но проверка на всякий случай).
        if self._button_column_index is not None and column == self._button_column_index:
            return

        if row >= len(self._current_values) or column >= len(self._current_values[row]):
            return

        old_value = self._current_values[row][column]
        new_value = item.text()

        if old_value == new_value:
            return

        self._current_values[row][column] = new_value

        change = {
            "row": row,
            "column": column,
            "old": old_value,
            "new": new_value,
        }
        self._changes.append(change)
        self.dataChangedSignal.emit(change)

    def _on_current_cell_changed(
        self,
        current_row: int,
        current_column: int,
        previous_row: int,
        previous_column: int,
    ) -> None:
        """
        Обработчик смены текущей активной ячейки таблицы. Если изменилась
        именно строка (а не только столбец в пределах той же строки),
        испускает сигнал rowChanged с индексом новой строки и
        идентификатором записи (значением первого столбца).
        """
        if current_row < 0 or current_row == previous_row:
            return

        record_id: Optional[Any] = None
        if current_row < len(self._current_values) and self._current_values[current_row]:
            record_id = self._current_values[current_row][0]

        self.rowChanged.emit(current_row, record_id)

    # ------------------------------------------------------------------ #
    #  Заготовки методов для будущей работы с базой данных (Access/pyodbc)
    #  На данном этапе не реализованы. Компонент ничего не знает о том,
    #  КАК именно они будут реализованы — реализация должна быть добавлена
    #  снаружи или в подклассе, без изменения логики отображения таблицы.
    # ------------------------------------------------------------------ #

    def load_from_database(self, connection: Any, query: str, params: Optional[Sequence[Any]] = None) -> None:
        """
        [ЗАГЛУШКА] Загружает данные из базы данных Access через pyodbc и
        передаёт их в таблицу через set_data().

        Назначение
        ----------
        В будущем этот метод должен выполнить SQL-запрос через
        соединение pyodbc, получить список кортежей (курсор.fetchall())
        и вызвать self.set_data(rows) с результатом.

        Параметры
        ---------
        connection:
            Открытое соединение pyodbc (pyodbc.Connection), полученное
            снаружи компонента. Компонент не создаёт и не закрывает
            соединения самостоятельно.
        query:
            SQL-запрос SELECT, который необходимо выполнить.
        params:
            Необязательная последовательность параметров для
            параметризованного запроса (аналог cursor.execute(query, params)).

        Возвращает
        ----------
        None
            Метод не возвращает значение — результат передаётся во
            внутреннюю таблицу через set_data().

        Пример будущего использования
        -------------------------------
        >>> table.load_from_database(conn, "SELECT id, name, age FROM Users")

        Примерная реализация после подключения БД
        -------------------------------------------
        1. cursor = connection.cursor()
        2. cursor.execute(query, params or [])
        3. rows = cursor.fetchall()
        4. self.set_data([tuple(row) for row in rows])
        """
        pass

    def save_changes(self, connection: Any, table_name: str, id_column: str = "id") -> None:
        """
        [ЗАГЛУШКА] Сохраняет накопленные изменения (self.get_changes()) в
        базу данных Access через pyodbc с помощью SQL UPDATE-запросов.

        Назначение
        ----------
        В будущем этот метод должен пройтись по списку изменений,
        полученному от get_changes(), сгруппировать их по строкам и
        выполнить соответствующие UPDATE-запросы к таблице БД,
        используя значение идентификатора записи (первый столбец строки)
        в условии WHERE.

        Параметры
        ---------
        connection:
            Открытое соединение pyodbc (pyodbc.Connection).
        table_name:
            Имя таблицы в базе данных Access, в которую нужно записать
            изменения.
        id_column:
            Имя столбца-идентификатора в базе данных, используемого в
            условии WHERE (по умолчанию "id").

        Возвращает
        ----------
        None

        Пример будущего использования
        -------------------------------
        >>> table.save_changes(conn, table_name="Users", id_column="id")

        Примерная реализация после подключения БД
        -------------------------------------------
        1. changes = self.get_changes()
        2. Для каждого изменения определить record_id по self._current_values[row][0]
           (или через отдельный публичный метод получения id строки).
        3. Сформировать и выполнить запрос вида:
           UPDATE {table_name} SET {column_name} = ? WHERE {id_column} = ?
        4. После успешного сохранения вызвать self.clear_changes().
        """
        pass

    def insert_row(self, connection: Any, table_name: str, row_data: Tuple[Any, ...]) -> None:
        """
        [ЗАГЛУШКА] Вставляет новую запись в базу данных Access через
        pyodbc (SQL INSERT), а затем обновляет отображение таблицы.

        Назначение
        ----------
        В будущем этот метод должен выполнить INSERT INTO запрос с
        переданными данными строки, получить сгенерированный БД
        идентификатор (если применимо) и обновить таблицу (например,
        через refresh() или добавление строки в текущий набор данных).

        Параметры
        ---------
        connection:
            Открытое соединение pyodbc (pyodbc.Connection).
        table_name:
            Имя таблицы в базе данных, в которую производится вставка.
        row_data:
            Кортеж значений новой строки, в том же порядке столбцов, что
            используется в таблице (без учёта служебного столбца кнопки).

        Возвращает
        ----------
        None

        Пример будущего использования
        -------------------------------
        >>> table.insert_row(conn, "Users", (None, "Сергей", 40))

        Примерная реализация после подключения БД
        -------------------------------------------
        1. cursor = connection.cursor()
        2. cursor.execute(f"INSERT INTO {table_name} (...) VALUES (...)", row_data)
        3. connection.commit()
        4. self.refresh(connection, table_name)
        """
        pass

    def delete_row(self, connection: Any, table_name: str, record_id: Any, id_column: str = "id") -> None:
        """
        [ЗАГЛУШКА] Удаляет запись из базы данных Access через pyodbc
        (SQL DELETE) и обновляет отображение таблицы.

        Назначение
        ----------
        В будущем этот метод должен выполнить DELETE-запрос по
        идентификатору записи и обновить таблицу, убрав из неё
        соответствующую строку (например, через refresh()).

        Параметры
        ---------
        connection:
            Открытое соединение pyodbc (pyodbc.Connection).
        table_name:
            Имя таблицы в базе данных, из которой производится удаление.
        record_id:
            Значение идентификатора удаляемой записи (значение первого
            столбца соответствующей строки таблицы).
        id_column:
            Имя столбца-идентификатора в базе данных (по умолчанию "id").

        Возвращает
        ----------
        None

        Пример будущего использования
        -------------------------------
        >>> table.delete_row(conn, "Users", record_id=15)

        Примерная реализация после подключения БД
        -------------------------------------------
        1. cursor = connection.cursor()
        2. cursor.execute(f"DELETE FROM {table_name} WHERE {id_column} = ?", record_id)
        3. connection.commit()
        4. self.refresh(connection, table_name)
        """
        pass

    def update_row(
        self,
        connection: Any,
        table_name: str,
        record_id: Any,
        column_values: Dict[str, Any],
        id_column: str = "id",
    ) -> None:
        """
        [ЗАГЛУШКА] Обновляет одну запись в базе данных Access через
        pyodbc (SQL UPDATE) по её идентификатору.

        Назначение
        ----------
        В будущем этот метод должен сформировать и выполнить UPDATE
        запрос, устанавливающий новые значения для указанных столбцов
        конкретной строки. Может использоваться как для точечного
        обновления (например, по сигналу rowChanged), так и внутри
        save_changes() для применения накопленных изменений.

        Параметры
        ---------
        connection:
            Открытое соединение pyodbc (pyodbc.Connection).
        table_name:
            Имя таблицы в базе данных.
        record_id:
            Значение идентификатора обновляемой записи.
        column_values:
            Словарь {имя_столбца_в_БД: новое_значение} с изменёнными
            полями записи.
        id_column:
            Имя столбца-идентификатора в базе данных (по умолчанию "id").

        Возвращает
        ----------
        None

        Пример будущего использования
        -------------------------------
        >>> table.update_row(conn, "Users", record_id=15, column_values={"name": "Иван"})

        Примерная реализация после подключения БД
        -------------------------------------------
        1. cursor = connection.cursor()
        2. Сформировать SET-часть запроса из column_values.
        3. cursor.execute(
        ...     f"UPDATE {table_name} SET ... WHERE {id_column} = ?",
        ...     (*column_values.values(), record_id),
        ... )
        4. connection.commit()
        """
        pass

    def refresh(self, connection: Any, table_name: str, query: Optional[str] = None) -> None:
        """
        [ЗАГЛУШКА] Полностью перезагружает данные таблицы из базы данных
        Access через pyodbc, заменяя текущее содержимое актуальными
        данными и сбрасывая накопленные изменения.

        Назначение
        ----------
        В будущем этот метод должен повторно выполнить SELECT-запрос
        (переданный явно или сформированный по умолчанию по имени
        таблицы) и вызвать self.set_data(rows) с результатом — аналогично
        load_from_database(), но предназначен для использования после
        операций insert/update/delete для актуализации отображения.

        Параметры
        ---------
        connection:
            Открытое соединение pyodbc (pyodbc.Connection).
        table_name:
            Имя таблицы в базе данных, данные которой нужно перечитать.
        query:
            Необязательный явный SQL-запрос SELECT. Если не передан,
            должен быть сформирован запрос вида "SELECT * FROM {table_name}".

        Возвращает
        ----------
        None

        Пример будущего использования
        -------------------------------
        >>> table.refresh(conn, "Users")

        Примерная реализация после подключения БД
        -------------------------------------------
        1. sql = query or f"SELECT * FROM {table_name}"
        2. self.load_from_database(connection, sql)
        """
        pass