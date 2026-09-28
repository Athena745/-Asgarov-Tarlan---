"""SQL 编译器相关的异常类型定义"""


class SqlCompilerError(Exception):
    """所有编译期错误的基类"""
    pass


class LexError(SqlCompilerError):
    def __init__(self, message, line, col):
        self.line = line
        self.col = col
        super().__init__(f"[词法错误] {message} (行:{line}, 列:{col})")


class ParseError(SqlCompilerError):
    def __init__(self, message, line, col, expected=None):
        self.line = line
        self.col = col
        self.expected = expected
        msg = f"[语法错误] {message} (行:{line}, 列:{col})"
        if expected:
            msg += f"，期望符号: {expected}"
        super().__init__(msg)


class SemanticError(SqlCompilerError):
    def __init__(self, err_type, position, reason):
        self.err_type = err_type
        self.position = position
        self.reason = reason
        super().__init__(f"[语义错误] 类型:{err_type}, 位置:{position}, 原因:{reason}")


class PlanError(SqlCompilerError):
    def __init__(self, message):
        super().__init__(f"[执行计划错误] {message}")
