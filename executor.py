"""执行引擎 (Execution Engine)：解释执行由计划生成器产生的逻辑执行计划。
实现算子：CreateTable, Insert, Delete, SeqScan, Filter, Project
"""


def _match(row, predicate):
    for cond in predicate:
        col, op, val = cond["column"], cond["op"], cond["value"]
        actual = row[col]
        if op == "=":
            ok = actual == val
        elif op == ">":
            ok = actual > val
        elif op == "<":
            ok = actual < val
        elif op == ">=":
            ok = actual >= val
        elif op == "<=":
            ok = actual <= val
        elif op == "<>":
            ok = actual != val
        else:
            ok = False
        if not ok:
            return False
    return True


class Executor:
    def __init__(self, engine):
        self.engine = engine

    def execute(self, plan):
        op = plan["op"]
        if op == "CreateTable":
            cols = [(c["name"], c["type"]) for c in plan["columns"]]
            self.engine.create_table(plan["table"], cols)
            return {"message": f"表 {plan['table']} 创建成功"}
        if op == "Insert":
            row = dict(zip(plan["columns"], plan["values"]))
            self.engine.insert_row(plan["table"], row)
            return {"message": "插入 1 行"}
        if op == "Delete":
            count = 0
            for pid, offset, row in list(self.engine.scan_table(plan["table"])):
                if _match(row, plan["predicate"]):
                    self.engine.delete_record(pid, offset)
                    count += 1
            return {"message": f"删除 {count} 行"}
        if op == "Project":
            rows = self._execute_child(plan["child"])
            cols = plan["columns"]
            return {"rows": [{c: r[c] for c in cols} for r in rows]}
        raise ValueError(f"未知算子: {op}")

    def _execute_child(self, plan):
        op = plan["op"]
        if op == "SeqScan":
            return [row for _, _, row in self.engine.scan_table(plan["table"])]
        if op == "Filter":
            rows = self._execute_child(plan["child"])
            return [r for r in rows if _match(r, plan["predicate"])]
        raise ValueError(f"未知算子: {op}")
