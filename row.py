"""记录 (Row) 与页内字节序列之间的序列化 / 反序列化。

记录物理格式: [tombstone:1B][length:2B][payload...]
  - tombstone: 0 表示有效记录，1 表示已删除（逻辑删除标记）
  - length:    payload 的字节长度
  - payload:   按表 schema 顺序依次编码各列：
        INT     -> 4 字节大端有符号整数
        VARCHAR -> 2 字节长度前缀 + UTF-8 编码字节
"""
import struct


def encode_row(columns, row: dict) -> bytes:
    payload = bytearray()
    for name, ctype in columns:
        val = row[name]
        if ctype == "INT":
            payload += struct.pack(">i", int(val))
        else:  # VARCHAR
            b = str(val).encode("utf-8")
            payload += struct.pack(">H", len(b)) + b
    length = len(payload)
    return struct.pack(">BH", 0, length) + bytes(payload)


def decode_row(columns, data: bytes, offset: int):
    """从 data[offset:] 处解析一条记录。
    返回 (tombstone, row_dict, next_offset)；若数据不足以构成一条记录则返回 None。
    """
    if offset + 3 > len(data):
        return None
    tombstone, length = struct.unpack_from(">BH", data, offset)
    start = offset + 3
    if start + length > len(data):
        return None
    row = {}
    p = start
    for name, ctype in columns:
        if ctype == "INT":
            row[name] = struct.unpack_from(">i", data, p)[0]
            p += 4
        else:
            (slen,) = struct.unpack_from(">H", data, p)
            p += 2
            row[name] = data[p:p + slen].decode("utf-8")
            p += slen
    return tombstone, row, start + length
