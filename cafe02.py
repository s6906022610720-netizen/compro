# cafe_file_io.py
# Python 3.10+ | Standard Library only
# Binary File I/O project adapted from the uploaded café application.
#
# Files:
#   menu.dat       -> menu master data
#   customers.dat  -> customer data
#   orders.dat     -> order-item records
#   report.txt     -> generated text report
#
# Every binary record has a fixed length and is packed/unpacked with struct.

from __future__ import annotations

import struct
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

MENU_FILE = BASE_DIR / "menu.dat"
CUSTOMERS_FILE = BASE_DIR / "customers.dat"
ORDERS_FILE = BASE_DIR / "orders.dat"
REPORT_FILE = BASE_DIR / "report.txt"

# Explicit little-endian, fixed-size records.
MENU_STRUCT = struct.Struct("<i30s40s80sd c".replace(" ", ""))
CUSTOMER_STRUCT = struct.Struct("<i40s20sc")
ORDER_STRUCT = struct.Struct("<iiiidd12s20s24s80s80s16sc")

SUGAR_OPTS = ["หวานปกติ", "หวานน้อย 50%", "หวานน้อย 25%", "ไม่หวาน"]
ICE_OPTS = ["น้ำแข็งปกติ", "น้ำแข็งน้อย", "ไม่ใส่น้ำแข็ง"]
STATUSES = ["รอดำเนินการ", "กำลังทำ", "เสร็จแล้ว"]
NEXT_STATUS = {"รอดำเนินการ": "กำลังทำ", "กำลังทำ": "เสร็จแล้ว"}

# This MENU is taken from the uploaded café source and used only to seed menu.dat.
MENU_SOURCE = [{'id': 1,
  'cat': 'กาแฟ',
  'name': 'เอสเปรสโซ',
  'desc': 'เข้มข้น หอมกลิ่นคั่วเข้ม',
  'styles': {'ร้อน': 60, 'เย็น': 60},
  'image': 'เอส.jpg',
  'bg': '#EFE3CC',
  'sugar': True,
  'toppings': [{'name': 'ไข่มุก', 'price': 10},
               {'name': 'วิปครีมสด', 'price': 15},
               {'name': 'เยลลี่ลิ้นจี่', 'price': 10},
               {'name': 'ชอตกาแฟเพิ่ม', 'price': 20}]},
 {'id': 2,
  'cat': 'กาแฟ',
  'name': 'ลาเต้',
  'desc': 'นมสตีมเนียนนุ่ม หวานมันกำลังดี',
  'styles': {'ร้อน': 65, 'เย็น': 70, 'ปั่น': 75},
  'image': 'ลาเต้.jpg',
  'bg': '#EFE3CC',
  'sugar': True,
  'toppings': [{'name': 'ไข่มุก', 'price': 10},
               {'name': 'วิปครีมสด', 'price': 15},
               {'name': 'เยลลี่ลิ้นจี่', 'price': 10},
               {'name': 'ชอตกาแฟเพิ่ม', 'price': 20}]},
 {'id': 3,
  'cat': 'กาแฟ',
  'name': 'อเมริกาโน่',
  'desc': 'บางเบา ดื่มง่าย เข้มสดชื่น',
  'styles': {'ร้อน': 55, 'เย็น': 60},
  'image': 'โน่ร้อน.jpg',
  'bg': '#EFE3CC',
  'sugar': True,
  'toppings': [{'name': 'ไข่มุก', 'price': 10},
               {'name': 'วิปครีมสด', 'price': 15},
               {'name': 'เยลลี่ลิ้นจี่', 'price': 10},
               {'name': 'ชอตกาแฟเพิ่ม', 'price': 20}]},
 {'id': 17,
  'cat': 'กาแฟ',
  'name': 'คาปูชิโน่',
  'desc': 'คาปูชิโน่แก้วโปรด ฟองนมฟูโอบใจ',
  'styles': {'ร้อน': 55, 'เย็น': 60},
  'image': 'คาปู.jpg',
  'bg': '#EFE3CC',
  'sugar': True,
  'toppings': [{'name': 'ไข่มุก', 'price': 10},
               {'name': 'วิปครีมสด', 'price': 15},
               {'name': 'เยลลี่ลิ้นจี่', 'price': 10},
               {'name': 'ชอตกาแฟเพิ่ม', 'price': 20}]},
 {'id': 21,
  'cat': 'กาแฟ',
  'name': 'มัคคิอาโต้',
  'desc': 'หอมคาราเมล ละมุนใจทุกเลเยอร์',
  'styles': {'ร้อน': 55, 'เย็น': 60},
  'image': 'มิคคิอาโต้.jpg',
  'bg': '#EFE3CC',
  'sugar': True,
  'toppings': [{'name': 'ไข่มุก', 'price': 10},
               {'name': 'วิปครีมสด', 'price': 15},
               {'name': 'เยลลี่ลิ้นจี่', 'price': 10},
               {'name': 'ชอตกาแฟเพิ่ม', 'price': 20}]},
 {'id': 4,
  'cat': 'เครื่องดื่ม',
  'name': 'ชาไทย',
  'desc': 'หอมกลิ่นใบชา หวานมัน',
  'styles': {'ร้อน': 55, 'เย็น': 60, 'ปั่น': 65},
  'image': 'ชาไทยเย็น.jpg',
  'bg': '#F3D9B8',
  'sugar': True,
  'toppings': [{'name': 'ไข่มุก', 'price': 10},
               {'name': 'วิปครีมสด', 'price': 15},
               {'name': 'เยลลี่ลิ้นจี่', 'price': 10},
               {'name': 'ชอตกาแฟเพิ่ม', 'price': 20}]},
 {'id': 5,
  'cat': 'เครื่องดื่ม',
  'name': 'ชามะนาว',
  'desc': 'เปรี้ยวสดชื่น',
  'styles': {'เย็น': 55, 'ปั่น': 60},
  'image': 'ชามะนาว.jpg',
  'bg': '#F3D9B8',
  'sugar': True,
  'toppings': [{'name': 'ไข่มุก', 'price': 10},
               {'name': 'วิปครีมสด', 'price': 15},
               {'name': 'เยลลี่ลิ้นจี่', 'price': 10},
               {'name': 'ชอตกาแฟเพิ่ม', 'price': 20}]},
 {'id': 6,
  'cat': 'เครื่องดื่ม',
  'name': 'มัทฉะลาเต้',
  'desc': 'ชาเขียวญี่ปุ่นแท้',
  'styles': {'ร้อน': 70, 'เย็น': 75, 'ปั่น': 80},
  'image': 'มัจฉะ.jpg',
  'bg': '#DCE7C8',
  'sugar': True,
  'toppings': [{'name': 'ไข่มุก', 'price': 10},
               {'name': 'วิปครีมสด', 'price': 15},
               {'name': 'เยลลี่ลิ้นจี่', 'price': 10},
               {'name': 'ชอตกาแฟเพิ่ม', 'price': 20}]},
 {'id': 18,
  'cat': 'เครื่องดื่ม',
  'name': 'ชาไต้หวัน',
  'desc': 'ชาหอมตะโกน หวานน้อยแต่นัวมาก ดื่มแล้วสดชื่นสุดๆ',
  'styles': {'ร้อน': 70, 'เย็น': 75, 'ปั่น': 80},
  'image': 'ใต้หวัน.jpg',
  'bg': '#DCE7C8',
  'sugar': True,
  'toppings': [{'name': 'ไข่มุก', 'price': 10},
               {'name': 'วิปครีมสด', 'price': 15},
               {'name': 'เยลลี่ลิ้นจี่', 'price': 10},
               {'name': 'ชอตกาแฟเพิ่ม', 'price': 20}]},
 {'id': 19,
  'cat': 'เครื่องดื่ม',
  'name': 'โกโก้',
  'desc': 'เข้มข้นสะใจ โกโก้แท้ๆ',
  'styles': {'ร้อน': 70, 'เย็น': 75, 'ปั่น': 80},
  'image': 'โกโก้.jpg',
  'bg': '#DCE7C8',
  'sugar': True,
  'toppings': [{'name': 'ไข่มุก', 'price': 10},
               {'name': 'วิปครีมสด', 'price': 15},
               {'name': 'เยลลี่ลิ้นจี่', 'price': 10},
               {'name': 'ชอตกาแฟเพิ่ม', 'price': 20}]},
 {'id': 20,
  'cat': 'เครื่องดื่ม',
  'name': 'นมเย็น',
  'desc': 'นมเย็นสีชมพูหวานกรุบ หอมมันนัวๆ ดื่มแล้วสดชื่นนน',
  'styles': {'ร้อน': 50, 'เย็น': 55, 'ปั่น': 60},
  'image': 'นมเย็น.jpg',
  'bg': '#DCE7C8',
  'sugar': True,
  'toppings': [{'name': 'ไข่มุก', 'price': 10},
               {'name': 'วิปครีมสด', 'price': 15},
               {'name': 'เยลลี่ลิ้นจี่', 'price': 10},
               {'name': 'ชอตกาแฟเพิ่ม', 'price': 20}]},
 {'id': 7,
  'cat': 'เบเกอรี่',
  'name': 'ครัวซองต์เนย',
  'desc': 'อบใหม่ทุกเช้า กรอบนอกนุ่มใน',
  'price': 55,
  'image': 'ครัวซอง.jpg',
  'bg': '#F1DCB8',
  'sugar': False,
  'toppings': [{'name': 'ไอศกรีมสกู๊ป', 'price': 25},
               {'name': 'ซอสช็อกโกแลต', 'price': 10},
               {'name': 'วิปครีมสด', 'price': 15}]},
 {'id': 8,
  'cat': 'เบเกอรี่',
  'name': 'บานอฟฟี่พาย',
  'desc': 'กล้วย คาราเมล ครีมสด',
  'price': 85,
  'image': 'บานอฟฟี่.jpg',
  'bg': '#F1DCB8',
  'sugar': False,
  'toppings': [{'name': 'ไอศกรีมสกู๊ป', 'price': 25},
               {'name': 'ซอสช็อกโกแลต', 'price': 10},
               {'name': 'วิปครีมสด', 'price': 15}]},
 {'id': 9,
  'cat': 'เบเกอรี่',
  'name': 'บราวนี่ช็อกโกแลต',
  'desc': 'เข้มข้น หนึบหนับ',
  'price': 65,
  'image': 'บราวนี่.jpg',
  'bg': '#E4CBB4',
  'sugar': False,
  'toppings': [{'name': 'ไอศกรีมสกู๊ป', 'price': 25},
               {'name': 'ซอสช็อกโกแลต', 'price': 10},
               {'name': 'วิปครีมสด', 'price': 15}]},
 {'id': 10,
  'cat': 'เบเกอรี่',
  'name': 'ทีรามิสุ',
  'desc': 'หอมกาแฟมาก',
  'price': 60,
  'image': 'Tiramisu.jpg',
  'bg': '#E4CBB4',
  'sugar': False,
  'toppings': [{'name': 'ไอศกรีมสกู๊ป', 'price': 25},
               {'name': 'ซอสช็อกโกแลต', 'price': 10},
               {'name': 'วิปครีมสด', 'price': 15}]},
 {'id': 11,
  'cat': 'เบเกอรี่',
  'name': 'โทสต์',
  'desc': 'ขนมปังกรอบหวาน ไอติมน่าอีส',
  'price': 120,
  'image': 'toast.jpg',
  'bg': '#E4CBB4',
  'sugar': False,
  'toppings': [{'name': 'ไอศกรีมสกู๊ป', 'price': 25},
               {'name': 'ซอสช็อกโกแลต', 'price': 10},
               {'name': 'วิปครีมสด', 'price': 15}]},
 {'id': 13,
  'cat': 'เบเกอรี่',
  'name': 'วอฟเฟิล',
  'desc': 'อร่อยจัด ต้องลองนะ',
  'price': 20,
  'image': 'waffles.jpg',
  'bg': '#E4CBB4',
  'sugar': False,
  'toppings': [{'name': 'ไอศกรีมสกู๊ป', 'price': 25},
               {'name': 'ซอสช็อกโกแลต', 'price': 10},
               {'name': 'วิปครีมสด', 'price': 15}]},
 {'id': 12,
  'cat': 'เบเกอรี่',
  'name': 'เค้กมะพร้าว',
  'desc': 'หอมอร่อย มะพร้าวเน้นๆ',
  'price': 45,
  'image': 'เค้กมะพร้าว.jpg',
  'bg': '#E4CBB4',
  'sugar': False,
  'toppings': [{'name': 'ไอศกรีมสกู๊ป', 'price': 25},
               {'name': 'ซอสช็อกโกแลต', 'price': 10},
               {'name': 'วิปครีมสด', 'price': 15}]},
 {'id': 14,
  'cat': 'เบเกอรี่',
  'name': 'เค้กสตอเบอรี่',
  'desc': 'เปรี้ยวหวานลงตัว สตอเบอรี่แน่นๆ',
  'price': 45,
  'image': 'เค้กสตอ.jpg',
  'bg': '#E4CBB4',
  'sugar': False,
  'toppings': [{'name': 'ไอศกรีมสกู๊ป', 'price': 25},
               {'name': 'ซอสช็อกโกแลต', 'price': 10},
               {'name': 'วิปครีมสด', 'price': 15}]},
 {'id': 15,
  'cat': 'เบเกอรี่',
  'name': 'เค้กส้ม',
  'desc': 'เค้กส้มฉ่ำว้าว ได้กลิ่นส้มแท้ๆ หอมสดชื่น',
  'price': 45,
  'image': 'เค้กส้ม.jpg',
  'bg': '#E4CBB4',
  'sugar': False,
  'toppings': [{'name': 'ไอศกรีมสกู๊ป', 'price': 25},
               {'name': 'ซอสช็อกโกแลต', 'price': 10},
               {'name': 'วิปครีมสด', 'price': 15}]},
 {'id': 16,
  'cat': 'เบเกอรี่',
  'name': 'เค้กหน้าไหม้',
  'desc': 'เติมเต็มบ่ายวันหยุดด้วยเค้กหน้าไหม้โฮมเมด',
  'price': 45,
  'image': 'ชีสเค้ดหน้าไหม้.jpg',
  'bg': '#E4CBB4',
  'sugar': False,
  'toppings': [{'name': 'ไอศกรีมสกู๊ป', 'price': 25},
               {'name': 'ซอสช็อกโกแลต', 'price': 10},
               {'name': 'วิปครีมสด', 'price': 15}]}]


# ---------------------------------------------------------------------------
# Fixed-length string helpers
# ---------------------------------------------------------------------------

def encode_fixed(value: str, size: int) -> bytes:
    """Encode UTF-8 and fit into exactly size bytes without cutting a character."""
    text = "" if value is None else str(value)
    raw = text.encode("utf-8")
    if len(raw) <= size:
        return raw.ljust(size, b"\x00")

    out = bytearray()
    for ch in text:
        b = ch.encode("utf-8")
        if len(out) + len(b) > size:
            break
        out.extend(b)
    return bytes(out).ljust(size, b"\x00")


def decode_fixed(raw: bytes) -> str:
    return raw.split(b"\x00", 1)[0].decode("utf-8", errors="replace").strip()


def pack_active(active: bool) -> bytes:
    return b"1" if active else b"0"


def active_from(raw: bytes) -> bool:
    return raw == b"1"


# ---------------------------------------------------------------------------
# File setup / low-level I/O
# ---------------------------------------------------------------------------

def initialize_files() -> None:
    for path in (MENU_FILE, CUSTOMERS_FILE, ORDERS_FILE):
        if not path.exists():
            path.touch()

    # Seed menu.dat from the uploaded project's MENU list.
    if MENU_FILE.stat().st_size == 0:
        with MENU_FILE.open("ab") as f:
            for item in MENU_SOURCE:
                if "styles" in item:
                    prices = item["styles"].values()
                    price = float(min(prices))
                else:
                    price = float(item["price"])

                f.write(MENU_STRUCT.pack(
                    int(item["id"]),
                    encode_fixed(item["cat"], 30),
                    encode_fixed(item["name"], 40),
                    encode_fixed(item["desc"], 80),
                    price,
                    pack_active(True),
                ))


def read_record(path: Path, st: struct.Struct, index: int):
    with path.open("rb") as f:
        f.seek(index * st.size)
        raw = f.read(st.size)
    if len(raw) != st.size:
        raise ValueError(f"Corrupted record in {path.name} at index {index}")
    return st.unpack(raw)


def record_count(path: Path, st: struct.Struct) -> int:
    size = path.stat().st_size
    if size % st.size != 0:
        raise ValueError(
            f"{path.name} is corrupted: size {size} is not a multiple of {st.size}"
        )
    return size // st.size


def iter_records(path: Path, st: struct.Struct):
    count = record_count(path, st)
    with path.open("rb") as f:
        for index in range(count):
            raw = f.read(st.size)
            if len(raw) != st.size:
                raise ValueError(f"Corrupted record in {path.name} at index {index}")
            yield index, st.unpack(raw)


def append_record(path: Path, st: struct.Struct, values) -> int:
    with path.open("ab") as f:
        index = f.tell() // st.size
        f.write(st.pack(*values))
    return index


def update_record(path: Path, st: struct.Struct, index: int, values) -> None:
    with path.open("r+b") as f:
        f.seek(index * st.size)
        if len(f.read(st.size)) != st.size:
            raise ValueError("Record index does not exist.")
        f.seek(index * st.size)
        f.write(st.pack(*values))


def validate_all_files() -> None:
    print("\n--- File Integrity Check ---")
    for path, st in (
        (MENU_FILE, MENU_STRUCT),
        (CUSTOMERS_FILE, CUSTOMER_STRUCT),
        (ORDERS_FILE, ORDER_STRUCT),
    ):
        try:
            n = record_count(path, st)
            print(f"{path.name}: {n} records × {st.size} bytes = {path.stat().st_size} bytes")
        except ValueError as e:
            print(e)


# ---------------------------------------------------------------------------
# Menu records
# ---------------------------------------------------------------------------

def menu_from_record(rec):
    menu_id, cat, name, desc, price, active = rec
    return {
        "id": menu_id,
        "cat": decode_fixed(cat),
        "name": decode_fixed(name),
        "desc": decode_fixed(desc),
        "price": price,
        "active": active_from(active),
    }


def pack_menu(item):
    return (
        int(item["id"]),
        encode_fixed(item["cat"], 30),
        encode_fixed(item["name"], 40),
        encode_fixed(item["desc"], 80),
        float(item["price"]),
        pack_active(item["active"]),
    )


def all_menus(active_only=True):
    result = []
    for idx, rec in iter_records(MENU_FILE, MENU_STRUCT):
        item = menu_from_record(rec)
        item["_index"] = idx
        if not active_only or item["active"]:
            result.append(item)
    return result


def find_menu(menu_id):
    for idx, rec in iter_records(MENU_FILE, MENU_STRUCT):
        item = menu_from_record(rec)
        if item["active"] and item["id"] == menu_id:
            item["_index"] = idx
            return item
    return None


# ---------------------------------------------------------------------------
# Customer records
# ---------------------------------------------------------------------------

def customer_from_record(rec):
    customer_id, name, phone, active = rec
    return {
        "id": customer_id,
        "name": decode_fixed(name),
        "phone": decode_fixed(phone),
        "active": active_from(active),
    }


def pack_customer(c):
    return (
        int(c["id"]),
        encode_fixed(c["name"], 40),
        encode_fixed(c["phone"], 20),
        pack_active(c["active"]),
    )


def all_customers(active_only=True):
    result = []
    for idx, rec in iter_records(CUSTOMERS_FILE, CUSTOMER_STRUCT):
        c = customer_from_record(rec)
        c["_index"] = idx
        if not active_only or c["active"]:
            result.append(c)
    return result


def find_customer(customer_id):
    for idx, rec in iter_records(CUSTOMERS_FILE, CUSTOMER_STRUCT):
        c = customer_from_record(rec)
        if c["active"] and c["id"] == customer_id:
            c["_index"] = idx
            return c
    return None


# ---------------------------------------------------------------------------
# Order-item records
# One physical record = one item inside an order.
# Multiple records may share the same order_id.
# ---------------------------------------------------------------------------

def order_from_record(rec):
    (
        order_id, customer_id, menu_id, qty, unit_price, line_total,
        status, fulfil, pay, note, options, order_time, active
    ) = rec
    return {
        "id": order_id,
        "customer_id": customer_id,
        "menu_id": menu_id,
        "qty": qty,
        "unit_price": unit_price,
        "line_total": line_total,
        "status": decode_fixed(status),
        "fulfil": decode_fixed(fulfil),
        "pay": decode_fixed(pay),
        "note": decode_fixed(note),
        "options": decode_fixed(options),
        "time": decode_fixed(order_time),
        "active": active_from(active),
    }


def pack_order(o):
    return (
        int(o["id"]),
        int(o["customer_id"]),
        int(o["menu_id"]),
        int(o["qty"]),
        float(o["unit_price"]),
        float(o["line_total"]),
        encode_fixed(o["status"], 12),
        encode_fixed(o["fulfil"], 20),
        encode_fixed(o["pay"], 24),
        encode_fixed(o["note"], 80),
        encode_fixed(o["options"], 80),
        encode_fixed(o["time"], 16),
        pack_active(o["active"]),
    )


def all_order_rows(active_only=True):
    result = []
    for idx, rec in iter_records(ORDERS_FILE, ORDER_STRUCT):
        o = order_from_record(rec)
        o["_index"] = idx
        if not active_only or o["active"]:
            result.append(o)
    return result


def next_order_id():
    ids = [o["id"] for o in all_order_rows(active_only=False)]
    return max(ids, default=1000) + 1


def order_ids():
    return sorted({o["id"] for o in all_order_rows()})


def get_order(order_id):
    rows = [o for o in all_order_rows() if o["id"] == order_id]
    return rows


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def ask_int(prompt, minimum=None, maximum=None):
    while True:
        value = input(prompt).strip()
        try:
            n = int(value)
            if minimum is not None and n < minimum:
                raise ValueError
            if maximum is not None and n > maximum:
                raise ValueError
            return n
        except ValueError:
            rule = []
            if minimum is not None:
                rule.append(f">= {minimum}")
            if maximum is not None:
                rule.append(f"<= {maximum}")
            suffix = f" ({' and '.join(rule)})" if rule else ""
            print(f"กรุณากรอกจำนวนเต็มที่ถูกต้อง{suffix}")


def ask_float(prompt, minimum=None):
    while True:
        value = input(prompt).strip()
        try:
            x = float(value)
            if minimum is not None and x < minimum:
                raise ValueError
            return x
        except ValueError:
            print("กรุณากรอกตัวเลขที่ถูกต้อง")


def ask_nonempty(prompt):
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("ห้ามเว้นว่าง")


def choose(prompt, options):
    print(prompt)
    for i, value in enumerate(options, 1):
        print(f"{i}. {value}")
    while True:
        n = ask_int("เลือก: ", 1, len(options))
        return options[n - 1]


def yes_no(prompt):
    while True:
        x = input(f"{prompt} (y/n): ").strip().lower()
        if x in ("y", "n"):
            return x == "y"


# ---------------------------------------------------------------------------
# Add
# ---------------------------------------------------------------------------

def add_menu():
    print("\n=== Add Menu Item ===")
    menu_id = ask_int("Menu ID: ", 1)
    if find_menu(menu_id):
        print("ID นี้มีอยู่แล้ว")
        return

    cat = ask_nonempty("หมวดหมู่: ")
    name = ask_nonempty("ชื่อเมนู: ")
    desc = input("รายละเอียด: ").strip()
    price = ask_float("ราคาเริ่มต้น: ", 0)

    item = {
        "id": menu_id, "cat": cat, "name": name,
        "desc": desc, "price": price, "active": True
    }
    append_record(MENU_FILE, MENU_STRUCT, pack_menu(item))
    print("เพิ่มเมนูเรียบร้อย")


def add_customer():
    print("\n=== Add Customer ===")
    customer_id = ask_int("Customer ID: ", 1)
    if find_customer(customer_id):
        print("ID นี้มีอยู่แล้ว")
        return
    name = ask_nonempty("ชื่อลูกค้า: ")
    phone = input("เบอร์โทร: ").strip()

    c = {"id": customer_id, "name": name, "phone": phone, "active": True}
    append_record(CUSTOMERS_FILE, CUSTOMER_STRUCT, pack_customer(c))
    print("เพิ่มลูกค้าเรียบร้อย")


def select_menu():
    menus = all_menus()
    if not menus:
        print("ยังไม่มีเมนู")
        return None
    for m in menus:
        print(f'{m["id"]:>3} | {m["name"]:<25} | {m["cat"]:<12} | ฿{m["price"]:.2f}')
    menu_id = ask_int("Menu ID: ")
    m = find_menu(menu_id)
    if not m:
        print("ไม่พบเมนู")
    return m


def select_customer():
    customers = all_customers()
    if not customers:
        print("ยังไม่มีลูกค้า")
        return None
    for c in customers:
        print(f'{c["id"]:>4} | {c["name"]:<30} | {c["phone"]}')
    customer_id = ask_int("Customer ID: ")
    c = find_customer(customer_id)
    if not c:
        print("ไม่พบลูกค้า")
    return c


def add_order():
    print("\n=== Add Order ===")
    customer = select_customer()
    if not customer:
        return

    order_id = next_order_id()
    print(f"Order ID ใหม่: {order_id}")

    while True:
        menu = select_menu()
        if not menu:
            return

        qty = ask_int("จำนวน: ", 1)
        style = input("รูปแบบ (ร้อน/เย็น/ปั่น หรือเว้นว่าง): ").strip()
        sugar = input("ความหวาน (หรือเว้นว่าง): ").strip()
        ice = input("น้ำแข็ง (หรือเว้นว่าง): ").strip()
        toppings = input("ท็อปปิ้ง (คั่นด้วย , หรือเว้นว่าง): ").strip()

        options = []
        for x in (style, sugar, ice):
            if x:
                options.append(x)
        if toppings:
            options.append("เพิ่ม: " + toppings)
        options_text = " · ".join(options)

        extra = 0.0
        if toppings:
            # Read topping prices from the source menu definition.
            src = next((x for x in MENU_SOURCE if x["id"] == menu["id"]), None)
            if src:
                valid = {t["name"]: t["price"] for t in src.get("toppings", [])}
                for t in toppings.split(","):
                    t = t.strip()
                    if t in valid:
                        extra += float(valid[t])

        unit_price = menu["price"] + extra
        line_total = unit_price * qty

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        order = {
            "id": order_id,
            "customer_id": customer["id"],
            "menu_id": menu["id"],
            "qty": qty,
            "unit_price": unit_price,
            "line_total": line_total,
            "status": STATUSES[0],
            "fulfil": choose("รับสินค้าแบบไหน", ["รับที่ร้าน", "เดลิเวอรี่"]),
            "pay": choose("ช่องทางชำระเงิน", ["เงินสดหน้าร้าน", "พร้อมเพย์ / โอนเงิน", "บัตรเครดิต/เดบิต"]),
            "note": input("หมายเหตุ: ").strip(),
            "options": options_text,
            "time": now,
            "active": True,
        }
        append_record(ORDERS_FILE, ORDER_STRUCT, pack_order(order))
        print(f"เพิ่มรายการใน Order #{order_id} แล้ว ยอดรายการ = ฿{line_total:.2f}")

        if not yes_no("เพิ่มรายการสินค้าในออเดอร์เดียวกันอีกไหม"):
            break

    print(f"สร้าง Order #{order_id} เรียบร้อย")


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

def update_menu():
    m = select_menu()
    if not m:
        return
    print("กด Enter เพื่อคงค่าเดิม")
    cat = input(f'หมวดหมู่ [{m["cat"]}]: ').strip() or m["cat"]
    name = input(f'ชื่อ [{m["name"]}]: ').strip() or m["name"]
    desc = input(f'รายละเอียด [{m["desc"]}]: ').strip() or m["desc"]
    raw = input(f'ราคา [{m["price"]}]: ').strip()
    price = float(raw) if raw else m["price"]

    m.update(cat=cat, name=name, desc=desc, price=price)
    update_record(MENU_FILE, MENU_STRUCT, m["_index"], pack_menu(m))
    print("แก้ไขเมนูเรียบร้อย")


def update_customer():
    c = select_customer()
    if not c:
        return
    print("กด Enter เพื่อคงค่าเดิม")
    name = input(f'ชื่อ [{c["name"]}]: ').strip() or c["name"]
    phone = input(f'เบอร์ [{c["phone"]}]: ').strip() or c["phone"]
    c.update(name=name, phone=phone)
    update_record(CUSTOMERS_FILE, CUSTOMER_STRUCT, c["_index"], pack_customer(c))
    print("แก้ไขข้อมูลลูกค้าเรียบร้อย")


def update_order():
    ids = order_ids()
    if not ids:
        print("ยังไม่มีออเดอร์")
        return
    print("Order IDs:", ", ".join(map(str, ids)))
    order_id = ask_int("Order ID: ")
    rows = get_order(order_id)
    if not rows:
        print("ไม่พบออเดอร์")
        return

    current = rows[0]
    print(f'สถานะปัจจุบัน: {current["status"]}')
    status = choose("เลือกสถานะใหม่", STATUSES)

    for row in rows:
        row["status"] = status
        update_record(ORDERS_FILE, ORDER_STRUCT, row["_index"], pack_order(row))
    print("อัปเดตสถานะออเดอร์เรียบร้อย")


# ---------------------------------------------------------------------------
# Delete (logical delete)
# ---------------------------------------------------------------------------

def delete_menu():
    m = select_menu()
    if not m:
        return
    refs = [o for o in all_order_rows() if o["menu_id"] == m["id"]]
    if refs:
        print("ไม่สามารถลบเมนูนี้ได้ เพราะมีประวัติการสั่งซื้ออ้างอิงอยู่")
        return
    if yes_no(f'ลบ "{m["name"]}" หรือไม่'):
        m["active"] = False
        update_record(MENU_FILE, MENU_STRUCT, m["_index"], pack_menu(m))
        print("ลบเมนูแบบ logical delete แล้ว")


def delete_customer():
    c = select_customer()
    if not c:
        return
    refs = [o for o in all_order_rows() if o["customer_id"] == c["id"]]
    if refs:
        print("ไม่สามารถลบลูกค้าได้ เพราะมีประวัติการสั่งซื้ออ้างอิงอยู่")
        return
    if yes_no(f'ลบ "{c["name"]}" หรือไม่'):
        c["active"] = False
        update_record(CUSTOMERS_FILE, CUSTOMER_STRUCT, c["_index"], pack_customer(c))
        print("ลบลูกค้าแบบ logical delete แล้ว")


def delete_order():
    ids = order_ids()
    if not ids:
        print("ยังไม่มีออเดอร์")
        return
    print("Order IDs:", ", ".join(map(str, ids)))
    order_id = ask_int("Order ID: ")
    rows = get_order(order_id)
    if not rows:
        print("ไม่พบออเดอร์")
        return
    if yes_no(f"ลบ Order #{order_id} หรือไม่"):
        for row in rows:
            row["active"] = False
            update_record(ORDERS_FILE, ORDER_STRUCT, row["_index"], pack_order(row))
        print("ลบออเดอร์แบบ logical delete แล้ว")


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------

def show_single_menu():
    m = select_menu()
    if m:
        print(m)


def show_single_customer():
    c = select_customer()
    if c:
        print(c)


def show_single_order():
    order_id = ask_int("Order ID: ")
    rows = get_order(order_id)
    if not rows:
        print("ไม่พบออเดอร์")
        return
    show_order_rows(rows)


def show_order_rows(rows):
    customer = find_customer(rows[0]["customer_id"])
    customer_name = customer["name"] if customer else "Unknown"
    print(f'\nOrder #{rows[0]["id"]} | ลูกค้า: {customer_name}')
    print(f'สถานะ: {rows[0]["status"]} | เวลา: {rows[0]["time"]}')
    print(f'รับสินค้า: {rows[0]["fulfil"]} | ชำระเงิน: {rows[0]["pay"]}')
    print("-" * 80)
    total = 0
    for r in rows:
        m = find_menu(r["menu_id"])
        name = m["name"] if m else f'Menu {r["menu_id"]}'
        print(
            f'{name:<25} x{r["qty"]:<3} '
            f'฿{r["unit_price"]:>7.2f} = ฿{r["line_total"]:>8.2f}'
        )
        if r["options"]:
            print(f'  ตัวเลือก: {r["options"]}')
        total += r["line_total"]
    print("-" * 80)
    print(f"รวม: ฿{total:.2f}")
    if rows[0]["note"]:
        print("หมายเหตุ:", rows[0]["note"])


def view_all():
    print("\n=== All Active Records ===")
    print(f"Menus: {len(all_menus())}")
    for m in all_menus():
        print(f'  M{m["id"]}: {m["name"]} - ฿{m["price"]:.2f}')

    print(f"\nCustomers: {len(all_customers())}")
    for c in all_customers():
        print(f'  C{c["id"]}: {c["name"]} - {c["phone"]}')

    ids = order_ids()
    print(f"\nOrders: {len(ids)}")
    for oid in ids:
        show_order_rows(get_order(oid))


def filter_records():
    print("\n1. ค้นหาเมนูตามชื่อ/หมวดหมู่")
    print("2. ค้นหาลูกค้าตามชื่อ/เบอร์")
    print("3. ค้นหาออเดอร์ตามสถานะ")
    choice = ask_int("เลือก: ", 1, 3)

    if choice == 1:
        q = input("คำค้น: ").strip().lower()
        rows = [m for m in all_menus()
                if q in m["name"].lower() or q in m["cat"].lower()]
        for m in rows:
            print(f'{m["id"]}: {m["name"]} | {m["cat"]} | ฿{m["price"]:.2f}')

    elif choice == 2:
        q = input("คำค้น: ").strip().lower()
        rows = [c for c in all_customers()
                if q in c["name"].lower() or q in c["phone"].lower()]
        for c in rows:
            print(f'{c["id"]}: {c["name"]} | {c["phone"]}')

    else:
        status = choose("สถานะ", STATUSES)
        ids = sorted({r["id"] for r in all_order_rows() if r["status"] == status})
        for oid in ids:
            show_order_rows(get_order(oid))


def statistics():
    menus = all_menus()
    customers = all_customers()
    rows = all_order_rows()
    ids = sorted({r["id"] for r in rows})
    sales = sum(r["line_total"] for r in rows)
    completed_sales = sum(r["line_total"] for r in rows if r["status"] == "เสร็จแล้ว")
    pending = sum(1 for oid in ids if get_order(oid)[0]["status"] != "เสร็จแล้ว")

    item_qty = {}
    for r in rows:
        item_qty[r["menu_id"]] = item_qty.get(r["menu_id"], 0) + r["qty"]
    top = sorted(item_qty.items(), key=lambda x: x[1], reverse=True)[:5]

    print("\n=== Statistics ===")
    print("จำนวนเมนู:", len(menus))
    print("จำนวนลูกค้า:", len(customers))
    print("จำนวนออเดอร์:", len(ids))
    print(f"ยอดขายรวม: ฿{sales:.2f}")
    print(f"ยอดขายออเดอร์เสร็จแล้ว: ฿{completed_sales:.2f}")
    print("ออเดอร์ที่ยังไม่เสร็จ:", pending)
    print("\nTop 5 เมนูตามจำนวนชิ้น:")
    for menu_id, qty in top:
        m = find_menu(menu_id)
        print(f"  {m['name'] if m else menu_id}: {qty} ชิ้น")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def generate_report():
    menus = all_menus()
    customers = all_customers()
    rows = all_order_rows()
    ids = sorted({r["id"] for r in rows})

    sales = sum(r["line_total"] for r in rows)
    completed_sales = sum(r["line_total"] for r in rows if r["status"] == "เสร็จแล้ว")

    item_qty = {}
    item_sales = {}
    for r in rows:
        item_qty[r["menu_id"]] = item_qty.get(r["menu_id"], 0) + r["qty"]
        item_sales[r["menu_id"]] = item_sales.get(r["menu_id"], 0) + r["line_total"]

    top = sorted(item_qty.items(), key=lambda x: x[1], reverse=True)[:10]

    lines = []
    lines.append("CAFE MANAGEMENT SYSTEM REPORT")
    lines.append("=" * 60)
    lines.append("Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("")
    lines.append("SUMMARY")
    lines.append(f"Menu records : {len(menus)}")
    lines.append(f"Customers    : {len(customers)}")
    lines.append(f"Orders       : {len(ids)}")
    lines.append(f"Sales        : {sales:.2f} THB")
    lines.append(f"Completed    : {completed_sales:.2f} THB")
    lines.append("")
    lines.append("TOP MENU ITEMS")
    lines.append("-" * 60)

    for menu_id, qty in top:
        m = find_menu(menu_id)
        name = m["name"] if m else f"Menu {menu_id}"
        lines.append(
            f"{name:<30} qty={qty:<5} sales={item_sales[menu_id]:.2f}"
        )

    lines.append("")
    lines.append("ORDERS")
    lines.append("-" * 60)
    for oid in ids:
        rows_for_order = get_order(oid)
        c = find_customer(rows_for_order[0]["customer_id"])
        cname = c["name"] if c else "Unknown"
        total = sum(r["line_total"] for r in rows_for_order)
        lines.append(
            f"Order #{oid} | {cname} | "
            f"{rows_for_order[0]['status']} | {total:.2f} THB"
        )

    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nสร้างรายงานแล้ว: {REPORT_FILE}")


# ---------------------------------------------------------------------------
# Menus
# ---------------------------------------------------------------------------

def add_menu():
    while True:
        print("\n=== Add ===")
        print("1. Add Menu")
        print("2. Add Customer")
        print("3. Add Order")
        print("4. Back")
        c = ask_int("เลือก: ", 1, 4)
        if c == 1:
            add_menu()
        elif c == 2:
            add_customer()
        elif c == 3:
            add_order()
        else:
            return


def update_menu_menu():
    while True:
        print("\n=== Update ===")
        print("1. Update Menu")
        print("2. Update Customer")
        print("3. Update Order Status")
        print("4. Back")
        c = ask_int("เลือก: ", 1, 4)
        if c == 1:
            update_menu()
        elif c == 2:
            update_customer()
        elif c == 3:
            update_order()
        else:
            return


def delete_menu_menu():
    while True:
        print("\n=== Delete ===")
        print("1. Delete Menu")
        print("2. Delete Customer")
        print("3. Delete Order")
        print("4. Back")
        c = ask_int("เลือก: ", 1, 4)
        if c == 1:
            delete_menu()
        elif c == 2:
            delete_customer()
        elif c == 3:
            delete_order()
        else:
            return


def view_menu():
    while True:
        print("\n=== View ===")
        print("1. View Single Menu")
        print("2. View Single Customer")
        print("3. View Single Order")
        print("4. View All")
        print("5. Filter/Search")
        print("6. Statistics")
        print("7. File Integrity Check")
        print("8. Back")
        c = ask_int("เลือก: ", 1, 8)

        if c == 1:
            show_single_menu()
        elif c == 2:
            show_single_customer()
        elif c == 3:
            show_single_order()
        elif c == 4:
            view_all()
        elif c == 5:
            filter_records()
        elif c == 6:
            statistics()
        elif c == 7:
            validate_all_files()
        else:
            return


def main():
    initialize_files()
    print("=" * 60)
    print("       CAFE MANAGEMENT SYSTEM - FILE I/O")
    print("=" * 60)
    print(f"Menu record size    : {MENU_STRUCT.size} bytes")
    print(f"Customer record size : {CUSTOMER_STRUCT.size} bytes")
    print(f"Order record size    : {ORDER_STRUCT.size} bytes")

    while True:
        print("\n" + "=" * 60)
        print("1. Add")
        print("2. Update")
        print("3. Delete")
        print("4. View")
        print("5. Generate Report")
        print("6. Exit")
        print("=" * 60)

        choice = ask_int("เลือกเมนู: ", 1, 6)

        if choice == 1:
            add_menu()
        elif choice == 2:
            update_menu_menu()
        elif choice == 3:
            delete_menu_menu()
        elif choice == 4:
            view_menu()
        elif choice == 5:
            generate_report()
        else:
            print("จบการทำงาน")
            break


if __name__ == "__main__":
    main()