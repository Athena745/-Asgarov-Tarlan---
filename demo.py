# -*- coding: utf-8 -*-
"""
综合演示脚本：依次演示
  1) 指导书给出的四条标准测试语句（词法->语法->语义->计划->执行 全流程，verbose 模式）
  2) 六类典型错误场景（缺分号/列名错误/类型不匹配/值个数不一致/字符串未闭合/重复建表）
  3) 条件查询与删除后再查询的正确性
  4) 程序“重启”后的数据持久性验证（重新创建 Database 对象指向同一数据库文件）
  5) 大量数据插入下的页分配、缓存命中率与替换日志（LRU）
运行方式： python demo.py
"""
import os
from database import Database


def hr(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


DB_FILE = "demo.db"
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

# ---------- 1. 标准测试语句（含完整编译流程输出） ----------
hr("1. 标准测试语句 —— 完整编译流程 (Token流 / AST / 语义 / 执行计划)")
db = Database(db_file=DB_FILE, verbose=True)

standard_stmts = [
    "CREATE TABLE student(id INT, name VARCHAR, age INT);",
    "INSERT INTO student(id,name,age) VALUES (1,'Alice',20);",
    "SELECT id,name FROM student WHERE age > 18;",
]
for sql in standard_stmts:
    print(f"\n--- 执行: {sql} ---")
    for res in db.run_sql(sql):
        print("结果:", res)

# ---------- 2. 错误场景 ----------
hr("2. 错误场景演示")
db.verbose = False

error_cases = [
    ("缺少分号 (语法错误)", "SELECT id FROM student"),
    ("列名拼写错误 (语义错误)", "SELECT idd FROM student;"),
    ("类型不匹配 (语义错误)", "INSERT INTO student(id,name,age) VALUES ('x','Bob',20);"),
    ("值个数不一致 (语义错误)", "INSERT INTO student(id,name,age) VALUES (2,'Bob');"),
    ("字符串未闭合 (词法错误)", "INSERT INTO student(id,name,age) VALUES (3,'Bob,20);"),
    ("重复建表 (语义错误)", "CREATE TABLE student(id INT);"),
    ("非法字符 (词法错误)", "SELECT id FROM student WHERE id # 1;"),
]
for desc, sql in error_cases:
    print(f"\n--- {desc}: {sql} ---")
    for res in db.run_sql(sql):
        print("结果:", res)

# ---------- 3. 条件查询 / 删除后再查询 ----------
hr("3. 插入多行数据，验证条件查询与删除")
for i in range(2, 6):
    db.run_sql(f"INSERT INTO student(id,name,age) VALUES ({i},'S{i}',{15 + i});")

print("\n--- SELECT * FROM student WHERE age > 18; ---")
for res in db.run_sql("SELECT * FROM student WHERE age > 18;"):
    print(res)

print("\n--- DELETE FROM student WHERE id = 1; ---")
for res in db.run_sql("DELETE FROM student WHERE id = 1;"):
    print(res)

print("\n--- 删除后再次查询 SELECT * FROM student; ---")
for res in db.run_sql("SELECT * FROM student;"):
    print(res)

db.close()

# ---------- 4. 数据持久性验证（模拟重启） ----------
hr("4. 数据持久性验证：关闭数据库后重新打开（模拟程序重启）")
db2 = Database(db_file=DB_FILE, verbose=False)
print("--- 重新连接后 SELECT * FROM student; ---")
for res in db2.run_sql("SELECT * FROM student;"):
    print(res)
db2.close()

# ---------- 5. 大量数据插入：页分配与缓存统计 ----------
hr("5. 大量数据插入：验证页分配、缓存命中率与 LRU 替换日志")
DB_FILE2 = "demo_bulk.db"
if os.path.exists(DB_FILE2):
    os.remove(DB_FILE2)
db3 = Database(db_file=DB_FILE2, verbose=False, buffer_capacity=3, policy="LRU")
db3.run_sql("CREATE TABLE t(id INT, name VARCHAR);")
N = 600
for i in range(N):
    db3.run_sql(f"INSERT INTO t(id,name) VALUES ({i},'user_{i}');")

pages = db3.table_pages("t")
print(f"插入 {N} 行后，表 t 占用的数据页数量: {len(pages)}  -> 页号: {pages}")
stats = db3.buffer_stats()
print(f"缓存统计 (buffer_capacity=3, policy=LRU): {stats}")
print(f"替换日志共 {len(db3.buffer_log())} 条，节选前 5 条:")
for line in db3.buffer_log()[:5]:
    print(" ", line)

cnt = 0
for _, _, row in db3.engine.scan_table("t"):
    cnt += 1
print(f"SeqScan 校验：实际扫描到 {cnt} 行 (应等于插入行数 {N})")
db3.close()

hr("演示结束")
