"""命令行入口：交互式 REPL，或批量执行 SQL 文件。

用法：
    python main.py                          # 交互模式
    python main.py --file demo.sql          # 批处理执行
    python main.py --file demo.sql --verbose  # 同时输出 Token 流/AST/执行计划
    python main.py --policy FIFO            # 指定缓存替换策略 (LRU/FIFO)
"""
import argparse

from database import Database


def format_result(res):
    if "error" in res:
        return "✗ " + res["error"]
    if "rows" in res:
        rows = res["rows"]
        if not rows:
            return "(空结果集)"
        headers = list(rows[0].keys())
        lines = [" | ".join(headers)]
        for r in rows:
            lines.append(" | ".join(str(r[h]) for h in headers))
        lines.append(f"共 {len(rows)} 行")
        return "\n".join(lines)
    return "✓ " + res.get("message", "OK")


def run_statements(db, text):
    for stmt_sql in [s.strip() for s in text.split(";") if s.strip()]:
        for res in db.run_sql(stmt_sql + ";"):
            print(format_result(res))


def main():
    ap = argparse.ArgumentParser(description="简化数据库系统 (SQL 编译器 + 页式存储 + 执行引擎)")
    ap.add_argument("--db", default="mydb.db", help="数据库文件路径")
    ap.add_argument("--file", help="批量执行的 SQL 文件路径")
    ap.add_argument("--verbose", action="store_true", help="输出 Token 流 / AST / 执行计划")
    ap.add_argument("--policy", default="LRU", choices=["LRU", "FIFO"], help="缓存页替换策略")
    args = ap.parse_args()

    db = Database(db_file=args.db, verbose=args.verbose, policy=args.policy)
    try:
        if args.file:
            with open(args.file, "r", encoding="utf-8") as f:
                run_statements(db, f.read())
        else:
            print("简化数据库系统 (输入 SQL 语句，以分号结尾；输入 exit 退出)")
            buf = ""
            while True:
                try:
                    line = input("db> ")
                except EOFError:
                    break
                if line.strip().lower() == "exit":
                    break
                buf += line + " "
                if ";" in buf:
                    parts = buf.split(";")
                    buf = parts[-1]
                    for part in parts[:-1]:
                        if part.strip():
                            for res in db.run_sql(part.strip() + ";"):
                                print(format_result(res))
        stats = db.buffer_stats()
        print(f"\n[缓存统计] 命中 {stats['hits']} 次, 未命中 {stats['misses']} 次, "
              f"命中率 {stats['hit_rate']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
