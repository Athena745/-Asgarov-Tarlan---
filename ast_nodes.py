"""抽象语法树 (AST) 节点定义"""
from dataclasses import dataclass
from typing import List, Optional, Any


@dataclass
class ColumnDef:
    name: str
    type: str  # INT / VARCHAR


@dataclass
class CreateTableStmt:
    table: str
    columns: List[ColumnDef]


@dataclass
class InsertStmt:
    table: str
    columns: List[str]   # 若语句未显式给出列名，则为空列表
    values: List[Any]


@dataclass
class Condition:
    column: str
    op: str
    value: Any


@dataclass
class SelectStmt:
    table: str
    columns: List[str]                 # 空列表代表 SELECT *
    where: Optional[List[Condition]] = None   # 条件之间为 AND 关系


@dataclass
class DeleteStmt:
    table: str
    where: Optional[List[Condition]] = None
