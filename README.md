# 简化数据库系统

本项目按照《大型平台软件设计实习》指导书的要求，分三步构建了一个简化的数据库系统：

1. **SQL 编译器**（`sql_compiler/`）：词法分析 → 语法分析（递归下降，生成 AST）→ 语义分析（维护 Catalog，做存在性/类型/列数检查）→ 执行计划生成（`planner.py`）。
2. **页式存储系统**（`storage/`）：固定 4KB 页的分配/释放/读写（`disk_manager.py`），以及支持 LRU / FIFO 替换策略、命中率统计、替换日志的缓存层（`buffer_pool.py`）。
3. **数据库系统**（`storage_engine.py` + `executor.py` + `database.py`）：将执行计划映射为 CreateTable / Insert / Delete / SeqScan / Filter / Project 等算子，系统目录 `pg_catalog` 本身也作为一张表通过存储引擎持久化，支持重启后数据不丢失。

## 目录结构

```
sql_compiler/       词法分析器 lexer.py、AST 定义 ast_nodes.py、语法分析器 parser.py、错误类型 errors.py
storage/             disk_manager.py（页式存储）、buffer_pool.py（页缓存/替换策略）
catalog.py           内存 Catalog
semantic.py          语义分析器
planner.py           执行计划生成器
row.py                记录的序列化/反序列化
storage_engine.py    存储引擎（表-页映射、系统目录持久化）
executor.py          执行引擎（算子实现）
database.py          Database 类，整合编译器与执行/存储引擎
main.py              命令行入口（交互式 REPL / 批处理文件）
demo.py              一键演示脚本（覆盖全部功能点与错误场景，用作报告的运行结果依据）
tests/                单元测试与示例 SQL 文件
```

## 运行环境

仅依赖 Python 标准库（`struct`、`json`、`os`、`collections`、`dataclasses`），Python 3.8+ 即可运行，无需安装第三方包。

## 使用方法

```bash
# 交互模式
python main.py

# 批处理执行 SQL 文件
python main.py --file tests/sample_correct.sql

# 附带输出 Token 流 / AST / 执行计划
python main.py --file tests/sample_correct.sql --verbose

# 指定缓存替换策略 (LRU 或 FIFO)
python main.py --policy FIFO

# 一键运行完整演示（推荐先看这个）
python demo.py
```

数据库文件默认写在 `mydb.db`（可用 `--db` 参数自定义路径），程序退出前会自动持久化，重新运行程序即可看到之前创建的表和数据依然存在。

## 运行测试

```bash
python -m unittest discover -s tests -v
```

## 支持的 SQL 子集

- `CREATE TABLE t(col TYPE, ...)`，TYPE 为 `INT` 或 `VARCHAR`
- `INSERT INTO t(col,...) VALUES (v,...)`
- `SELECT col,... | * FROM t [WHERE cond (AND cond)*]`
- `DELETE FROM t [WHERE cond (AND cond)*]`
- 比较运算符：`= > < >= <= <>`
- 语句以 `;` 结束，支持一次输入多条语句；支持 `-- ` 单行注释

## 设计要点

- **页结构**：每页 4096 字节，页内前 4 字节保存 `free_offset`，之后依次追加变长记录 `[tombstone(1B)][length(2B)][payload]`。
- **系统目录**：`pg_catalog` 使用与用户表完全相同的记录存储机制，仅有它自身当前占用的页号列表保存在磁盘头页（页 0）中，避免自引用问题；数据库启动时通过扫描 `pg_catalog` 页面重建内存 Catalog。
- **缓存策略**：`BufferPool` 采用写穿透（write-through），写操作立即落盘并更新缓存，因此 `flush_page` 语义上总是已同步；读操作按 LRU/FIFO 统计命中率与替换日志。
- **删除**：采用逻辑删除（墓碑标记），`SeqScan` 自动跳过被标记的记录。

## 已知的简化与限制

- WHERE 子句仅支持形如 `列 运算符 常量`（可用 `AND` 连接多个条件），不支持 `OR`、括号嵌套、列与列比较。
- 未实现 `UPDATE`、`JOIN`、`ORDER BY`、`GROUP BY` 及查询优化（谓词下推等）等可选扩展项。
- `VARCHAR` 未做定长约束，按实际字符串长度编码（2 字节长度前缀）。
- 缓存为写穿透模式，牺牲了部分“脏页延迟写回”的性能收益，换取实现简单和数据安全。
