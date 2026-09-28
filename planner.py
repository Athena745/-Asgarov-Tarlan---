"""执行计划生成器：将 AST 转换为逻辑执行计划。
计划以嵌套字典表示，可直接 json.dumps 输出（等价于 S-表达式/树形结构）。
算子集合：CreateTable, Insert, Delete, SeqScan, Filter, Project
"""
from sql_compiler.errors import PlanError


def generate_plan(stmt, stmt_type, target_cols=None):
    if stmt_type == "CREATE_TABLE":
        return {
            "op": "CreateTable",
            "table": stmt.table,
            "columns": [{"name": c.name, "type": c.type} for c in stmt.columns],
        }
    if stmt_type == "INSERT":
        return {
            "op": "Insert",
            "table": stmt.table,
            "columns": target_cols,
            "values": stmt.values,
        }
    if stmt_type == "SELECT":
        plan = {"op": "SeqScan", "table": stmt.table}
        if stmt.where:
            plan = {
                "op": "Filter",
                "predicate": [{"column": c.column, "op": c.op, "value": c.value} for c in stmt.where],
                "child": plan,
            }
        return {"op": "Project", "columns": target_cols, "child": plan}
    if stmt_type == "DELETE":
        return {
            "op": "Delete",
            "table": stmt.table,
            "predicate": ([{"column": c.column, "op": c.op, "value": c.value} for c in stmt.where]
                          if stmt.where else []),
        }
    raise PlanError(f"不支持的语句类型: {stmt_type}")
