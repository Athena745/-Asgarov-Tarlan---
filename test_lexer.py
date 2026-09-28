import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sql_compiler.lexer import Lexer
from sql_compiler.errors import LexError


class TestLexer(unittest.TestCase):
    def test_keywords_and_identifiers(self):
        tokens = Lexer("SELECT id FROM student;").tokenize()
        types = [t.type for t in tokens]
        self.assertEqual(types, ["KEYWORD", "IDENTIFIER", "KEYWORD", "IDENTIFIER",
                                  "DELIMITER", "EOF"])

    def test_constants(self):
        tokens = Lexer("VALUES (1,'Alice',20)").tokenize()
        lexemes = [t.lexeme for t in tokens if t.type in ("CONST_INT", "CONST_STR")]
        self.assertEqual(lexemes, ["1", "Alice", "20"])

    def test_operators(self):
        tokens = Lexer("age >= 18 AND age <> 0").tokenize()
        ops = [t.lexeme for t in tokens if t.type == "OPERATOR"]
        self.assertEqual(ops, [">=", "<>"])

    def test_illegal_char(self):
        with self.assertRaises(LexError):
            Lexer("SELECT id FROM t WHERE id # 1;").tokenize()

    def test_unclosed_string(self):
        with self.assertRaises(LexError):
            Lexer("INSERT INTO t VALUES ('abc);").tokenize()

    def test_line_col_tracking(self):
        tokens = Lexer("SELECT id\nFROM student;").tokenize()
        from_tok = [t for t in tokens if t.lexeme == "FROM"][0]
        self.assertEqual(from_tok.line, 2)


if __name__ == "__main__":
    unittest.main()
