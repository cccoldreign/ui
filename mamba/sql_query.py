"""Изменяемая структура SQL-запроса: части запроса, фильтры, сортировка."""
import re

PARTS = ("select", "from", "join", "where", "group_by", "having", "order_by")

# код фильтра: (шаблон SQL, преобразование значения)
OPS = {
    "contains": ("{c} LIKE ?", lambda v: f"%{v}%"),
    "starts":   ("{c} LIKE ?", lambda v: f"{v}%"),
    "eq":  ("{c} = ?",  None),
    "ne":  ("{c} <> ?", None),
    "gt":  ("{c} > ?",  None),
    "ge":  ("{c} >= ?", None),
    "lt":  ("{c} < ?",  None),
    "le":  ("{c} <= ?", None),
    "null":    ("{c} IS NULL", None),
    "notnull": ("{c} IS NOT NULL", None),
}

# какие фильтры предлагать для типа колонки (тип задаётся в JSON: "types")
FILTER_MENU = {
    "string": [("contains", "Содержит…"), ("starts", "Начинается с…"),
               ("eq", "Равно…"), ("ne", "Не равно…")],
    "number": [("eq", "Равно…"), ("ne", "Не равно…"), ("gt", "Больше…"),
               ("ge", "Больше или равно…"), ("lt", "Меньше…"), ("le", "Меньше или равно…")],
    "date":   [("eq", "Дата равна…"), ("ge", "С даты…"), ("le", "По дату (включительно)…")],
}
for _items in FILTER_MENU.values():
    _items += [("null", "Пусто"), ("notnull", "Не пусто")]


def _q(name):
    return "[" + name.replace("]", "]]") + "]"


def _and(base, extra):
    items = ([f"({base})"] if base else []) + list(extra)
    return " AND ".join(items)


def _parse_select(select):
    """Сопоставляет имя колонки результата и выражение из SELECT (для WHERE/HAVING/ORDER BY)."""
    items, depth, cur = [], 0, ""
    for ch in select:
        depth += (ch == "(") - (ch == ")")
        if ch == "," and depth == 0:
            items.append(cur)
            cur = ""
        else:
            cur += ch
    items.append(cur)

    aliases = {}
    for item in (i.strip() for i in items):
        m = re.match(r"^(.+?)\s+AS\s+\[?(\w+)\]?$", item, re.I | re.S)
        if m:
            aliases[m.group(2)] = m.group(1).strip()
        elif re.match(r"^[\w.\[\]]+$", item):
            aliases[re.sub(r"^.*\.", "", item).strip("[]")] = item
    return aliases


class SqlQuery:
    def __init__(self, cfg):
        self.cfg = cfg
        self.types = list(cfg.get("types", []))
        self.columns = []                       # заполняет модель после первой загрузки
        self.base = (cfg.get("query") or "").strip().rstrip(";")
        self.parts = {k: (cfg.get(k) or "").strip() for k in PARTS}
        self.where_params = []
        self.filters = []                       # [(колонка, код_фильтра, значение)]
        self.sort = None                        # (колонка, "ASC"/"DESC")
        self._dirty = False
        self._aliases = {} if self.base else _parse_select(self.parts["select"])

    # --- изменение структуры ---

    def reset(self):
        """Вернуть запрос к состоянию из JSON."""
        columns = self.columns
        self.__init__(self.cfg)
        self.columns = columns

    def add_where(self, sql, params=()):
        """Дописывает условие в параметр where (через AND). Значения - через '?' и params."""
        w = self.parts["where"]
        self.parts["where"] = f"({w}) AND ({sql})" if w else f"({sql})"
        self.where_params += list(params)
        self._dirty = True

    def type_of(self, column):
        i = self.columns.index(column)
        return self.types[i] if i < len(self.types) else "string"

    def add_filter(self, column, op, value=None):
        if op not in OPS:
            raise ValueError(f"Неизвестный фильтр: {op}")
        self.type_of(column)                    # проверка, что колонка существует
        self.filters.append((column, op, value))
        self._dirty = True

    def set_sort(self, column, direction="ASC"):
        direction = direction.upper()
        if direction not in ("ASC", "DESC"):
            raise ValueError("direction: ASC или DESC")
        self.type_of(column)
        self.sort = (column, direction)
        self._dirty = True

    # --- сборка SQL ---

    def _expr(self, column):
        return self._aliases.get(column) or _q(column)

    def _conditions(self, expr_of):
        sqls, params = [], []
        for column, op, value in self.filters:
            expr = expr_of(column)
            if self.type_of(column) == "date":
                expr = f"CAST({expr} AS date)"
            template, convert = OPS[op]
            sqls.append("(" + template.format(c=expr) + ")")
            if "?" in template:
                params.append(convert(value) if convert else value)
        return sqls, params

    def build(self):
        """(sql, params) без пагинации."""
        p = self.parts

        if self.base:
            # готовый запрос: пока ничего не менялось - выполняем как есть,
            # иначе оборачиваем (тогда внутри не должно быть ORDER BY - он задаётся ключом order_by)
            if not (self._dirty or p["where"] or p["order_by"]):
                return self.base, []
            conds, fparams = self._conditions(_q)
            sql = f"SELECT * FROM ({self.base}) AS _q"
            where = _and(p["where"], conds)
            if where:
                sql += " WHERE " + where
            order = f"{_q(self.sort[0])} {self.sort[1]}" if self.sort else p["order_by"]
            if order:
                sql += " ORDER BY " + order
            return sql, self.where_params + fparams

        grouped = bool(p["group_by"])
        conds, fparams = self._conditions(self._expr)   # фильтры колонок: HAVING при GROUP BY, иначе WHERE
        sql = ["SELECT " + (p["select"] or "*"), "FROM " + p["from"]]
        if p["join"]:
            sql.append(p["join"])
        where = _and(p["where"], [] if grouped else conds)
        if where:
            sql.append("WHERE " + where)
        if grouped:
            sql.append("GROUP BY " + p["group_by"])
        having = _and(p["having"], conds if grouped else [])
        if having:
            sql.append("HAVING " + having)
        order = f"{self._expr(self.sort[0])} {self.sort[1]}" if self.sort else p["order_by"]
        if order:
            sql.append("ORDER BY " + order)
        return " ".join(sql), self.where_params + fparams

    def page_sql(self, offset, size):
        """(sql, params) одной страницы (SQL Server: OFFSET ... FETCH)."""
        template = self.cfg.get("page_query")
        if template and not self._dirty:        # свой шаблон работает, пока нет фильтров/сортировки
            return template.replace("{offset}", str(offset)).replace("{limit}", str(size)), []
        sql, params = self.build()
        if "order by" not in sql.lower():
            sql += " ORDER BY (SELECT NULL)"
        return f"{sql} OFFSET {offset} ROWS FETCH NEXT {size} ROWS ONLY", params

    def export_sql(self):
        """(sql, params) для выгрузки всего результата с учётом фильтров и сортировки."""
        if not self._dirty and self.cfg.get("export_query"):
            return self.cfg["export_query"].strip().rstrip(";"), []
        return self.build()
