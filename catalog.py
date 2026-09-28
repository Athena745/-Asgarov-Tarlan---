"""内存中的模式目录 (Catalog)。
与持久化的 pg_catalog 表保持同步：数据库启动时从磁盘重建，
每次 CREATE TABLE / 表增长新页时同步写回。
"""


class Catalog:
    def __init__(self):
        # name -> {"columns": [(col_name, col_type), ...], "pages": [page_id, ...]}
        self.tables = {}

    def table_exists(self, name):
        return name in self.tables

    def add_table(self, name, columns, pages):
        self.tables[name] = {"columns": list(columns), "pages": pages}

    def get_table(self, name):
        return self.tables.get(name)

    def column_exists(self, table, col):
        t = self.tables.get(table)
        if not t:
            return False
        return any(c[0] == col for c in t["columns"])

    def column_type(self, table, col):
        t = self.tables.get(table)
        if not t:
            return None
        for c in t["columns"]:
            if c[0] == col:
                return c[1]
        return None
