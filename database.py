"""数据库系统总入口：整合 SQL 编译器（词法/语法/语义/计划生成）与执行/存储引擎。"""
import json

from sql_compiler.lexer import Lexer
from sql_compiler.parser import Parser
from sql_compiler.errors import SqlCompilerError
from sql_compiler import ast_nodes as N
from semantic import SemanticAnalyzer
import planner
from storage_engine import StorageEngine
from executor import Executor

STMT_TYPE_MAP = {
    N.CreateTableStmt: "CREATE_TABLE",
    N.InsertStmt: "INSERT",
    N.SelectStmt: "SELECT",
    N.DeleteStmt: "DELETE",
}


class Database:
    def __init__(self, db_file="mydb.db", verbose=False, buffer_capacity=64, policy="LRU"):
        self.engine = StorageEngine(db_file, buffer_capacity=buffer_capacity, policy=policy)
        self.semantic = SemanticAnalyzer(self.engine.catalog)
        self.executor = Executor(self.engine)
        self.verbose = verbose

    def run_sql(self, sql_text: str):
        """执行一段可能包含多条语句的 SQL 文本，返回每条语句的结果/错误列表。"""
        try:
            tokens = Lexer(sql_text).tokenize()
        except SqlCompilerError as e:
            return [{"error": str(e)}]
        if self.verbose:
            print("== Token 流 ==")
            for t in tokens:
                print(" ", t)
        try:
            stmts = Parser(tokens).parse_program()
        except SqlCompilerError as e:
            return [{"error": str(e)}]
        return [self._run_one(stmt) for stmt in stmts]

    def _run_one(self, stmt):
        stmt_type = STMT_TYPE_MAP[type(stmt)]
        if self.verbose:
            print("== AST ==")
            print(" ", stmt)
        try:
            target_cols = None
            if stmt_type == "CREATE_TABLE":
                self.semantic.check_create_table(stmt)
            elif stmt_type == "INSERT":
                target_cols = self.semantic.check_insert(stmt)
            elif stmt_type == "SELECT":
                target_cols = self.semantic.check_select(stmt)
            elif stmt_type == "DELETE":
                self.semantic.check_delete(stmt)
            if self.verbose:
                print("== 语义检查通过 ==")
            plan = planner.generate_plan(stmt, stmt_type, target_cols)
            if self.verbose:
                print("== 执行计划 ==")
                print(" ", json.dumps(plan, ensure_ascii=False, indent=2))
            return self.executor.execute(plan)
        except SqlCompilerError as e:
            return {"error": str(e)}

    def close(self):
        self.engine.close()

    def buffer_stats(self):
        return self.engine.buf.stats()

    def buffer_log(self):
        return self.engine.buf.log

    def table_pages(self, table_name):
        info = self.engine.catalog.get_table(table_name)
        return list(info["pages"]) if info else []
