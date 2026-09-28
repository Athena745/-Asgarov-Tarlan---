"""语义分析器：表/列存在性检查、类型一致性检查、列数/列序检查，并维护 Catalog。"""
from sql_compiler.errors import SemanticError


class SemanticAnalyzer:
    def __init__(self, catalog):
        self.catalog = catalog

    def check_create_table(self, stmt):
        if self.catalog.table_exists(stmt.table):
            raise SemanticError("表已存在", f"表 {stmt.table}", "不能重复创建同名表")
        names = [c.name for c in stmt.columns]
        if len(names) != len(set(names)):
            raise SemanticError("列名重复", f"表 {stmt.table}", "存在重复定义的列名")
        return True

    def check_insert(self, stmt):
        if not self.catalog.table_exists(stmt.table):
            raise SemanticError("表不存在", f"表 {stmt.table}", "INSERT 目标表未定义")
        table = self.catalog.get_table(stmt.table)
        col_names = [c[0] for c in table["columns"]]
        target_cols = stmt.columns if stmt.columns else col_names
        for c in target_cols:
            if c not in col_names:
                raise SemanticError("列不存在", f"表 {stmt.table} 列 {c}", "该列未在表定义中")
        if len(target_cols) != len(stmt.values):
            raise SemanticError(
                "列数不匹配", f"表 {stmt.table}",
                f"目标列数 {len(target_cols)} 与提供的值个数 {len(stmt.values)} 不一致")
        for col, val in zip(target_cols, stmt.values):
            ctype = self.catalog.column_type(stmt.table, col)
            if ctype == "INT" and not isinstance(val, int):
                raise SemanticError("类型不匹配", f"列 {col}", f"期望 INT 类型，实际值为字符串 '{val}'")
            if ctype == "VARCHAR" and not isinstance(val, str):
                raise SemanticError("类型不匹配", f"列 {col}", f"期望 VARCHAR 类型，实际值为数字 {val}")
        return target_cols

    def check_select(self, stmt):
        if not self.catalog.table_exists(stmt.table):
            raise SemanticError("表不存在", f"表 {stmt.table}", "SELECT 来源表未定义")
        table = self.catalog.get_table(stmt.table)
        col_names = [c[0] for c in table["columns"]]
        target_cols = stmt.columns if stmt.columns else col_names
        for c in target_cols:
            if c not in col_names:
                raise SemanticError("列不存在", f"表 {stmt.table} 列 {c}", "该列未在表定义中")
        if stmt.where:
            for cond in stmt.where:
                if cond.column not in col_names:
                    raise SemanticError("列不存在", f"表 {stmt.table} 列 {cond.column}",
                                         "WHERE 条件引用了未定义的列")
        return target_cols

    def check_delete(self, stmt):
        if not self.catalog.table_exists(stmt.table):
            raise SemanticError("表不存在", f"表 {stmt.table}", "DELETE 目标表未定义")
        table = self.catalog.get_table(stmt.table)
        col_names = [c[0] for c in table["columns"]]
        if stmt.where:
            for cond in stmt.where:
                if cond.column not in col_names:
                    raise SemanticError("列不存在", f"表 {stmt.table} 列 {cond.column}",
                                         "WHERE 条件引用了未定义的列")
        return True
