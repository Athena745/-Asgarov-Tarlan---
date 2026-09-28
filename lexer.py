"""
SQL 词法分析器 (Lexer)
将 SQL 源文本切分为 Token 流。每个 Token 包含：
  - 种别码 (KEYWORD / IDENTIFIER / CONST_INT / CONST_STR / OPERATOR / DELIMITER / EOF)
  - 词素值 (源代码中的具体字符串)
  - 行号、列号 (便于错误定位)
"""
from dataclasses import dataclass
from typing import List

from .errors import LexError

KEYWORDS = {
    "SELECT", "FROM", "WHERE", "CREATE", "TABLE", "INSERT", "INTO",
    "VALUES", "DELETE", "INT", "VARCHAR", "AND", "OR",
}

# 多字符运算符必须排在其前缀单字符运算符之前，保证最长匹配
OPERATORS = ["<>", ">=", "<=", "=", ">", "<", "+", "-", "*", "/"]
DELIMITERS = "(),;."


@dataclass
class Token:
    type: str
    lexeme: str
    line: int
    col: int

    def __repr__(self):
        return f"[{self.type}, {self.lexeme!r}, {self.line}, {self.col}]"


class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.col = 1
        self.length = len(text)

    def _peek(self, offset=0):
        p = self.pos + offset
        return self.text[p] if p < self.length else ""

    def _advance(self):
        ch = self.text[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def tokenize(self) -> List[Token]:
        tokens = []
        while self.pos < self.length:
            ch = self._peek()
            if ch in " \t\r\n":
                self._advance()
                continue
            if ch == "-" and self._peek(1) == "-":  # 单行注释 -- ...
                while self.pos < self.length and self._peek() != "\n":
                    self._advance()
                continue
            start_line, start_col = self.line, self.col
            if ch.isalpha() or ch == "_":
                tokens.append(self._read_identifier(start_line, start_col))
            elif ch.isdigit():
                tokens.append(self._read_number(start_line, start_col))
            elif ch == "'":
                tokens.append(self._read_string(start_line, start_col))
            elif ch in DELIMITERS:
                self._advance()
                tokens.append(Token("DELIMITER", ch, start_line, start_col))
            else:
                op = self._match_operator()
                if op:
                    tokens.append(Token("OPERATOR", op, start_line, start_col))
                else:
                    bad = self._advance()
                    raise LexError(f"非法字符 '{bad}'", start_line, start_col)
        tokens.append(Token("EOF", "", self.line, self.col))
        return tokens

    def _match_operator(self):
        for op in OPERATORS:
            if self.text[self.pos:self.pos + len(op)] == op:
                for _ in op:
                    self._advance()
                return op
        return None

    def _read_identifier(self, line, col):
        s = self.pos
        while self.pos < self.length and (self._peek().isalnum() or self._peek() == "_"):
            self._advance()
        word = self.text[s:self.pos]
        if word.upper() in KEYWORDS:
            return Token("KEYWORD", word.upper(), line, col)
        return Token("IDENTIFIER", word, line, col)

    def _read_number(self, line, col):
        s = self.pos
        while self.pos < self.length and self._peek().isdigit():
            self._advance()
        return Token("CONST_INT", self.text[s:self.pos], line, col)

    def _read_string(self, line, col):
        self._advance()  # 跳过起始单引号
        s = self.pos
        while self.pos < self.length and self._peek() != "'":
            self._advance()
        if self.pos >= self.length:
            raise LexError("字符串未闭合", line, col)
        value = self.text[s:self.pos]
        self._advance()  # 跳过结束单引号
        return Token("CONST_STR", value, line, col)
