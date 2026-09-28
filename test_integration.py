import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database


class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.db_file = "test_tmp.db"
        if os.path.exists(self.db_file):
            os.remove(self.db_file)
        self.db = Database(db_file=self.db_file)

    def tearDown(self):
        self.db.close()
        if os.path.exists(self.db_file):
            os.remove(self.db_file)

    def test_create_insert_select(self):
        self.db.run_sql("CREATE TABLE student(id INT, name VARCHAR, age INT);")
        self.db.run_sql("INSERT INTO student(id,name,age) VALUES (1,'Alice',20);")
        self.db.run_sql("INSERT INTO student(id,name,age) VALUES (2,'Bob',17);")
        res = self.db.run_sql("SELECT id,name FROM student WHERE age > 18;")[0]
        self.assertEqual(res["rows"], [{"id": 1, "name": "Alice"}])

    def test_duplicate_create_table_error(self):
        self.db.run_sql("CREATE TABLE t(id INT);")
        res = self.db.run_sql("CREATE TABLE t(id INT);")[0]
        self.assertIn("error", res)

    def test_insert_type_mismatch(self):
        self.db.run_sql("CREATE TABLE t(id INT, name VARCHAR);")
        res = self.db.run_sql("INSERT INTO t(id,name) VALUES ('a','b');")[0]
        self.assertIn("error", res)

    def test_insert_column_count_mismatch(self):
        self.db.run_sql("CREATE TABLE t(id INT, name VARCHAR);")
        res = self.db.run_sql("INSERT INTO t(id,name) VALUES (1);")[0]
        self.assertIn("error", res)

    def test_delete_and_requery(self):
        self.db.run_sql("CREATE TABLE t(id INT);")
        self.db.run_sql("INSERT INTO t(id) VALUES (1);")
        self.db.run_sql("INSERT INTO t(id) VALUES (2);")
        self.db.run_sql("DELETE FROM t WHERE id = 1;")
        res = self.db.run_sql("SELECT * FROM t;")[0]
        self.assertEqual(res["rows"], [{"id": 2}])

    def test_persistence_across_restart(self):
        self.db.run_sql("CREATE TABLE t(id INT, name VARCHAR);")
        self.db.run_sql("INSERT INTO t(id,name) VALUES (1,'x');")
        self.db.close()

        db2 = Database(db_file=self.db_file)
        res = db2.run_sql("SELECT * FROM t;")[0]
        self.assertEqual(res["rows"], [{"id": 1, "name": "x"}])
        db2.close()
        self.db = Database(db_file=self.db_file)  # 让 tearDown 能正常关闭/清理

    def test_bulk_insert_multi_page(self):
        self.db.run_sql("CREATE TABLE t(id INT, name VARCHAR);")
        for i in range(500):
            self.db.run_sql(f"INSERT INTO t(id,name) VALUES ({i},'user_{i}');")
        res = self.db.run_sql("SELECT * FROM t;")[0]
        self.assertEqual(len(res["rows"]), 500)
        self.assertGreater(len(self.db.table_pages("t")), 1)


if __name__ == "__main__":
    unittest.main()
