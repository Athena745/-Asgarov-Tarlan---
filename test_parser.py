import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sql_compiler.lexer import Lexer
from sql_compiler.parser import Parser
from sql_compiler.errors import ParseError
from sql_compiler import ast_nodes as N


def parse(sql):
    return Parser(Lexer(sql).tokenize()).parse_program()


class TestParser(unittest.TestCase):
    def test_create_table(self):
        stmts = parse("CREATE TABLE student(id INT, name VARCHAR, age INT);")
        self.assertEqual(len(stmts), 1)
        stmt = stmts[0]
        self.assertIsInstance(stmt, N.CreateTableStmt)
        self.assertEqual(stmt.table, "student")
        self.assertEqual([c.name for c in stmt.columns], ["id", "name", "age"])

    def test_insert(self):
        stmt = parse("INSERT INTO student(id,name,age) VALUES (1,'Alice',20);")[0]
        self.assertIsInstance(stmt, N.InsertStmt)
        self.assertEqual(stmt.values, [1, "Alice", 20])

    def test_select_with_where(self):
        stmt = parse("SELECT id,name FROM student WHERE age > 18;")[0]
        self.assertIsInstance(stmt, N.SelectStmt)
        self.assertEqual(stmt.columns, ["id", "name"])
        self.assertEqual(stmt.where[0].op, ">")

    def test_select_star(self):
        stmt = parse("SELECT * FROM student;")[0]
        self.assertEqual(stmt.columns, [])

    def test_delete(self):
        stmt = parse("DELETE FROM student WHERE id = 1;")[0]
        self.assertIsInstance(stmt, N.DeleteStmt)
        self.assertEqual(stmt.where[0].value, 1)

    def test_multiple_statements(self):
        stmts = parse("CREATE TABLE t(id INT); SELECT * FROM t;")
        self.assertEqual(len(stmts), 2)

    def test_missing_semicolon_raises(self):
        with self.assertRaises(ParseError):
            parse("SELECT id FROM student")

    def test_missing_expected_token(self):
        with self.assertRaises(ParseError):
            parse("CREATE TABLE student(id INT age INT);")


if __name__ == "__main__":
    unittest.main()
