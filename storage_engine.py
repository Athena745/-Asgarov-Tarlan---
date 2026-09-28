"""存储引擎 (Storage Engine)
职责：
  1. 调用底层页式存储 (DiskManager + BufferPool) 完成记录在页面中的组织、存储与访问；
  2. 维护系统目录 (System Catalog)：pg_catalog 本身也作为一张特殊的表，
     通过与用户表完全相同的记录存储机制进行持久化；
     pg_catalog 自身占用的页号列表则记录在磁盘头页中，避免自引用问题。
"""
import json
import struct

from storage.disk_manager import DiskManager, PAGE_SIZE
from storage.buffer_pool import BufferPool
from row import encode_row, decode_row
from catalog import Catalog

PG_CATALOG_COLUMNS = [
    ("table_name", "VARCHAR"),
    ("schema_json", "VARCHAR"),
    ("pages_json", "VARCHAR"),
]
PAGE_HEADER_SIZE = 4  # 每个数据页开头 4 字节记录 free_offset（下一条记录的写入位置）


class StorageEngine:
    def __init__(self, db_file="mydb.db", buffer_capacity=64, policy="LRU"):
        self.disk = DiskManager(db_file)
        self.buf = BufferPool(self.disk, capacity=buffer_capacity, policy=policy)
        self.catalog = Catalog()
        self._bootstrap_catalog()

    # ---------------- 系统目录初始化 / 重建 ----------------
    def _bootstrap_catalog(self):
        cat_pages = self.disk.get_catalog_pages()
        if not cat_pages:
            first = self.disk.allocate_page()
            self._init_page(first)
            self.disk.set_catalog_pages([first])
            return
        # 数据库重启：扫描 pg_catalog 的所有页面，重建内存 Catalog
        latest = {}
        for pid in cat_pages:
            for tombstone, data in self._iter_page_records(pid, PG_CATALOG_COLUMNS):
                if tombstone:
                    latest.pop(data["table_name"], None)
                else:
                    latest[data["table_name"]] = data
        for name, data in latest.items():
            cols = [tuple(c) for c in json.loads(data["schema_json"])]
            pages = json.loads(data["pages_json"])
            self.catalog.add_table(name, cols, pages)

    def _init_page(self, page_id):
        buf = bytearray(PAGE_SIZE)
        struct.pack_into(">I", buf, 0, PAGE_HEADER_SIZE)
        self.buf.write_page(page_id, bytes(buf))

    def _iter_page_records(self, page_id, columns):
        data = self.buf.get_page(page_id)
        (free_off,) = struct.unpack_from(">I", data, 0)
        offset = PAGE_HEADER_SIZE
        while offset < free_off:
            result = decode_row(columns, data, offset)
            if result is None:
                break
            tombstone, row, next_off = result
            yield tombstone, row
            offset = next_off

    # ---------------- 记录写入（页分配 / 追加） ----------------
    def _append_record(self, pages: list, columns, row: dict):
        """把记录追加到 pages 的最后一页；空间不足则分配新页。返回是否新增了页。"""
        record = encode_row(columns, row)
        grew = False
        if not pages:
            pid = self.disk.allocate_page()
            self._init_page(pid)
            pages.append(pid)
            grew = True
        pid = pages[-1]
        data = self.buf.get_page(pid)
        (free_off,) = struct.unpack_from(">I", data, 0)
        if free_off + len(record) > PAGE_SIZE:
            pid = self.disk.allocate_page()
            self._init_page(pid)
            pages.append(pid)
            grew = True
            data = self.buf.get_page(pid)
            (free_off,) = struct.unpack_from(">I", data, 0)
        data[free_off:free_off + len(record)] = record
        struct.pack_into(">I", data, 0, free_off + len(record))
        self.buf.write_page(pid, bytes(data))
        return grew

    def _catalog_upsert(self, table_name, columns, pages):
        """向 pg_catalog 追加一条该表的最新快照记录（重建时以最后一条为准）。"""
        cat_pages = self.disk.get_catalog_pages()
        row = {
            "table_name": table_name,
            "schema_json": json.dumps(columns),
            "pages_json": json.dumps(pages),
        }
        grew = self._append_record(cat_pages, PG_CATALOG_COLUMNS, row)
        if grew:
            self.disk.set_catalog_pages(cat_pages)

    # ---------------- 对外接口 ----------------
    def create_table(self, table_name, columns):
        pages = []
        self.catalog.add_table(table_name, columns, pages)
        self._catalog_upsert(table_name, columns, pages)

    def insert_row(self, table_name, row: dict):
        info = self.catalog.get_table(table_name)
        columns = info["columns"]
        pages = info["pages"]
        grew = self._append_record(pages, columns, row)
        if grew:
            self._catalog_upsert(table_name, columns, pages)

    def scan_table(self, table_name):
        """生成器：产出 (page_id, offset, row_dict)，自动跳过已被逻辑删除的记录。"""
        info = self.catalog.get_table(table_name)
        columns = info["columns"]
        for pid in info["pages"]:
            data = self.buf.get_page(pid)
            (free_off,) = struct.unpack_from(">I", data, 0)
            offset = PAGE_HEADER_SIZE
            while offset < free_off:
                result = decode_row(columns, data, offset)
                if result is None:
                    break
                tombstone, row, next_off = result
                if not tombstone:
                    yield pid, offset, row
                offset = next_off

    def delete_record(self, page_id, offset):
        """将指定记录标记为已删除（逻辑删除：置墓碑字节为 1）。"""
        data = self.buf.get_page(page_id)
        data[offset] = 1
        self.buf.write_page(page_id, bytes(data))

    def close(self):
        self.buf.flush_all()
        self.disk.close()
