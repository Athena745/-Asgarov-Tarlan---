"""SQL 语法分析器（递归下降法）
支持语句：CREATE TABLE / INSERT INTO / SELECT / DELETE
支持多条语句，以 ';' 分隔。
"""
from typing import List

from .lexer import Token
from .ast_nodes import ColumnDef, CreateTableStmt, InsertStmt, SelectStmt, DeleteStmt, Condition
from .errors import ParseError


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def _cur(self) -> Token:
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        t = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return t

    def _expect(self, ttype, lexeme=None):
        t = self._cur()
        if t.type != ttype or (lexeme is not None and t.lexeme != lexeme):
            expected = lexeme if lexeme else ttype
            got = t.lexeme if t.type != "EOF" else "<EOF>"
            raise ParseError(f"遇到 '{got}'", t.line, t.col, expected)
        return self._advance()

    def parse_program(self):
        stmts = []
        while self._cur().type != "EOF":
            stmts.append(self.parse_statement())
            self._expect("DELIMITER", ";")
        return stmts

    def parse_statement(self):
        t = self._cur()
        if t.type == "KEYWORD" and t.lexeme == "CREATE":
            return self.parse_create_table()
        if t.type == "KEYWORD" and t.lexeme == "INSERT":
            return self.parse_insert()
        if t.type == "KEYWORD" and t.lexeme == "SELECT":
            return self.parse_select()
        if t.type == "KEYWORD" and t.lexeme == "DELETE":
            return self.parse_delete()
        raise ParseError(f"未知语句起始符号 '{t.lexeme}'", t.line, t.col,
                          "CREATE/INSERT/SELECT/DELETE")

    # CREATE TABLE t (col type, col type, ...)
    def parse_create_table(self):
        self._expect("KEYWORD", "CREATE")
        self._expect("KEYWORD", "TABLE")
        name = self._expect("IDENTIFIER").lexeme
        self._expect("DELIMITER", "(")
        cols = [self._parse_column_def()]
        while self._cur().lexeme == ",":
            self._advance()
            cols.append(self._parse_column_def())
        self._expect("DELIMITER", ")")
        return CreateTableStmt(table=name, columns=cols)

    def _parse_column_def(self):
        cname = self._expect("IDENTIFIER").lexeme
        ctype_tok = self._cur()
        if ctype_tok.lexeme not in ("INT", "VARCHAR"):
            raise ParseError(f"未知列类型 '{ctype_tok.lexeme}'", ctype_tok.line, ctype_tok.col,
                              "INT 或 VARCHAR")
        self._advance()
        return ColumnDef(name=cname, type=ctype_tok.lexeme)

    # INSERT INTO t (c1,c2) VALUES (v1,v2)
    def parse_insert(self):
        self._expect("KEYWORD", "INSERT")
        self._expect("KEYWORD", "INTO")
        table = self._expect("IDENTIFIER").lexeme
        cols = []
        if self._cur().lexeme == "(":
            self._advance()
            cols.append(self._expect("IDENTIFIER").lexeme)
            while self._cur().lexeme == ",":
                self._advance()
                cols.append(self._expect("IDENTIFIER").lexeme)
            self._expect("DELIMITER", ")")
        self._expect("KEYWORD", "VALUES")
        self._expect("DELIMITER", "(")
        values = [self._parse_literal()]
        while self._cur().lexeme == ",":
            self._advance()
            values.append(self._parse_literal())
        self._expect("DELIMITER", ")")
        return InsertStmt(table=table, columns=cols, values=values)

    def _parse_literal(self):
        t = self._cur()
        if t.type == "CONST_INT":
            self._advance()
            return int(t.lexeme)
        if t.type == "CONST_STR":
            self._advance()
            return t.lexeme
        raise ParseError(f"遇到 '{t.lexeme}'", t.line, t.col, "常量 (数字或字符串)")

    # SELECT c1,c2 | * FROM t [WHERE cond (AND cond)*]
    def parse_select(self):
        self._expect("KEYWORD", "SELECT")
        cols = []
        if self._cur().lexeme == "*":
            self._advance()
        else:
            cols.append(self._expect("IDENTIFIER").lexeme)
            while self._cur().lexeme == ",":
                self._advance()
                cols.append(self._expect("IDENTIFIER").lexeme)
        self._expect("KEYWORD", "FROM")
        table = self._expect("IDENTIFIER").lexeme
        where = None
        if self._cur().type == "KEYWORD" and self._cur().lexeme == "WHERE":
            where = self._parse_where()
        return SelectStmt(table=table, columns=cols, where=where)

    def parse_delete(self):
        self._expect("KEYWORD", "DELETE")
        self._expect("KEYWORD", "FROM")
        table = self._expect("IDENTIFIER").lexeme
        where = None
        if self._cur().type == "KEYWORD" and self._cur().lexeme == "WHERE":
            where = self._parse_where()
        return DeleteStmt(table=table, where=where)

    def _parse_where(self):
        self._expect("KEYWORD", "WHERE")
        conds = [self._parse_condition()]
        while self._cur().type == "KEYWORD" and self._cur().lexeme == "AND":
            self._advance()
            conds.append(self._parse_condition())
        return conds

    def _parse_condition(self):
        col = self._expect("IDENTIFIER").lexeme
        op_tok = self._cur()
        if op_tok.type != "OPERATOR":
            raise ParseError(f"遇到 '{op_tok.lexeme}'", op_tok.line, op_tok.col,
                              "比较运算符 (=,>,<,>=,<=,<>)")
        self._advance()
        val = self._parse_literal()
        return Condition(column=col, op=op_tok.lexeme, value=val)
