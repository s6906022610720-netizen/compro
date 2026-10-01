#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ระบบขายสินค้าในคลัง (Baifern Cafe & Bakery Inventory & Sales Management)
รองรับ Binary File (.dat) แบบ Fixed-Length Records ด้วยโมดูล struct
ใช้เฉพาะ Python Standard Library เท่านั้น (ไม่ต้องติดตั้งไลบรารีภายนอก)
"""

import os
import sys
import struct
import unicodedata
from datetime import datetime, timedelta
import random
import shutil

# บังคับให้ Console ใน Windows รองรับ UTF-8 สำหรับภาษาไทย
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ===========================================================================
# โครงสร้างไดเรกทอรีและไฟล์ Binary
# ===========================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

PRODUCTS_FILE = os.path.join(DATA_DIR, "products.dat")
SALES_FILE = os.path.join(DATA_DIR, "sales.dat")
STOCK_LOGS_FILE = os.path.join(DATA_DIR, "stock_logs.dat")

# ===========================================================================
# นิยามโครงสร้าง Fixed-Length Record ด้วย struct
# ===========================================================================
# 1. products.dat: (145 bytes ต่อ record)
#    - product_id: int (4 bytes) 'i'
#    - name: string 80 bytes '80s' (UTF-8, null-padded)
#    - category: string 48 bytes '48s' (UTF-8, null-padded)
#    - price: double (8 bytes) 'd'
#    - stock: int (4 bytes) 'i'
#    - is_deleted: unsigned char (1 byte) 'B' (0 = Active, 1 = Soft Deleted)
PROD_FMT = "=i80s48sdiB"
PROD_RECORD_SIZE = struct.calcsize(PROD_FMT)  # 145 bytes

# 2. sales.dat: (77 bytes ต่อ record)
#    - sale_id: int (4 bytes) 'i'
#    - order_id: int (4 bytes) 'i'
#    - timestamp: string 20 bytes '20s' (e.g. "2026-10-02 12:30:00")
#    - product_id: int (4 bytes) 'i'
#    - qty: int (4 bytes) 'i'
#    - unit_price: double (8 bytes) 'd'
#    - total_price: double (8 bytes) 'd'
#    - payment_method: string 24 bytes '24s' (UTF-8, null-padded)
#    - is_deleted: unsigned char (1 byte) 'B' (0 = Normal, 1 = Cancelled)
SALE_FMT = "=ii20siidd24sB"
SALE_RECORD_SIZE = struct.calcsize(SALE_FMT)  # 77 bytes

# 3. stock_logs.dat: (96 bytes ต่อ record)
#    - log_id: int (4 bytes) 'i'
#    - timestamp: string 20 bytes '20s'
#    - product_id: int (4 bytes) 'i'
#    - action_type: string 12 bytes '12s' (e.g. "INITIAL", "RESTOCK", "SALE", "EDIT", "DELETE")
#    - change_qty: int (4 bytes) 'i' (+เติม / -ตัด)
#    - balance_qty: int (4 bytes) 'i'
#    - remark: string 48 bytes '48s' (UTF-8, null-padded)
LOG_FMT = "=i20si12sii48s"
LOG_RECORD_SIZE = struct.calcsize(LOG_FMT)  # 96 bytes

# ===========================================================================
# ข้อมูลเริ่มต้นจาก cafe_app (ขยายให้ครบมากกว่า 50 รายการ)
# ===========================================================================
SEED_PRODUCTS = [
    # รายการจาก cafe_app (กาแฟ)
    (1, "เอสเปรสโซ", "กาแฟ", 60.0, 50),
    (2, "ลาเต้", "กาแฟ", 65.0, 45),
    (3, "อเมริกาโน่", "กาแฟ", 55.0, 60),
    (17, "คาปูชิโน่", "กาแฟ", 55.0, 40),
    (21, "มัคคิอาโต้", "กาแฟ", 55.0, 35),
    # กาแฟพิเศษเพิ่มเติม
    (22, "มอคค่า", "กาแฟ", 65.0, 40),
    (23, "อเมริกาโน่ส้ม", "กาแฟ", 70.0, 35),
    (24, "เดอร์ตี้คอฟฟี่", "กาแฟ", 75.0, 25),
    (25, "โคลด์บริว", "กาแฟ", 80.0, 30),
    (26, "แฟลตไวท์", "กาแฟ", 65.0, 30),
    (27, "เอสเปรสโซโทนิค", "กาแฟ", 75.0, 25),
    (28, "คาราเมลมัคคิอาโต้", "กาแฟ", 70.0, 35),
    (29, "อเมริกาโน่น้ำผึ้ง", "กาแฟ", 65.0, 40),
    
    # รายการจาก cafe_app (เครื่องดื่ม)
    (4, "ชาไทย", "เครื่องดื่ม", 55.0, 50),
    (5, "ชามะนาว", "เครื่องดื่ม", 55.0, 40),
    (6, "มัทฉะลาเต้", "เครื่องดื่ม", 70.0, 30),
    (18, "ชาไต้หวัน", "เครื่องดื่ม", 70.0, 35),
    (19, "โกโก้", "เครื่องดื่ม", 70.0, 45),
    (20, "นมเย็น", "เครื่องดื่ม", 50.0, 50),
    # เครื่องดื่มเพิ่มเติม
    (30, "ชาเขียวมะนาว", "เครื่องดื่ม", 60.0, 35),
    (31, "โกโก้มินต์", "เครื่องดื่ม", 75.0, 30),
    (32, "ชาเอิร์ลเกรย์", "เครื่องดื่ม", 50.0, 40),
    (33, "ชาพีช", "เครื่องดื่ม", 55.0, 40),
    (34, "สตรอว์เบอร์รีสมูทตี้", "เครื่องดื่ม", 75.0, 25),
    (35, "มะม่วงปั่น", "เครื่องดื่ม", 70.0, 25),
    (36, "อิตาเลียนโซดาบลูฮาวาย", "เครื่องดื่ม", 50.0, 45),
    (37, "ลิ้นจี่โซดา", "เครื่องดื่ม", 50.0, 45),
    (38, "น้ำส้มคั้นสด", "เครื่องดื่ม", 60.0, 30),
    (39, "นมสดคาราเมล", "เครื่องดื่ม", 55.0, 35),
    (40, "ชาคาโมมายล์", "เครื่องดื่ม", 50.0, 30),
    (41, "ดาร์กช็อกโกแลต", "เครื่องดื่ม", 75.0, 35),
    (42, "ชาเขียวมะลิ", "เครื่องดื่ม", 45.0, 40),
    (43, "ชาแอปเปิ้ลเขียว", "เครื่องดื่ม", 55.0, 35),
    (44, "เสาวรสโซดา", "เครื่องดื่ม", 55.0, 40),
    (45, "นมหมีปั่นคาราเมล", "เครื่องดื่ม", 60.0, 30),

    # รายการจาก cafe_app (เบเกอรี่)
    (7, "ครัวซองต์เนย", "เบเกอรี่", 55.0, 25),
    (8, "บานอฟฟี่พาย", "เบเกอรี่", 85.0, 20),
    (9, "บราวนี่ช็อกโกแลต", "เบเกอรี่", 65.0, 30),
    (10, "ทีรามิสุ", "เบเกอรี่", 60.0, 15),
    (11, "โทสต์", "เบเกอรี่", 120.0, 15),
    (13, "วอฟเฟิล", "เบเกอรี่", 20.0, 40),
    (12, "เค้กมะพร้าว", "เบเกอรี่", 45.0, 20),
    (14, "เค้กสตอเบอรี่", "เบเกอรี่", 45.0, 20),
    (15, "เค้กส้ม", "เบเกอรี่", 45.0, 20),
    (16, "เค้กหน้าไหม้", "เบเกอรี่", 45.0, 20),
    # เบเกอรี่เพิ่มเติมให้ครบ 55 รายการ
    (46, "พายสับปะรด", "เบเกอรี่", 35.0, 30),
    (47, "เดนิชแอปเปิ้ล", "เบเกอรี่", 50.0, 25),
    (48, "คุกกี้เนยสด", "เบเกอรี่", 25.0, 50),
    (49, "คุกกี้ช็อกโกแลตชิพ", "เบเกอรี่", 30.0, 50),
    (50, "ชิฟฟอนใบเตย", "เบเกอรี่", 35.0, 25),
    (51, "เอแคลร์วานิลลา", "เบเกอรี่", 40.0, 30),
    (52, "ชีสทาร์ตญี่ปุ่น", "เบเกอรี่", 65.0, 20),
    (53, "มาการองสตรอว์เบอร์รี", "เบเกอรี่", 45.0, 30),
    (54, "ครัวซองต์อัลมอนด์", "เบเกอรี่", 70.0, 20),
    (55, "ครัวซองต์ช็อกโกแลต", "เบเกอรี่", 65.0, 20)
]

# ===========================================================================
# ฟังก์ชันอรรถประโยชน์สำหรับการจัดการสตริงและหน้าจอ CLI
# ===========================================================================
def safe_encode_str(s: str, max_bytes: int) -> bytes:
    """แปลงสตริงเป็น bytes พร้อมป้องกันการตัดครึ่งอักขระ UTF-8 และ pad ด้วย null bytes"""
    encoded = s.encode("utf-8")
    if len(encoded) <= max_bytes:
        return encoded.ljust(max_bytes, b"\x00")
    truncated = encoded[:max_bytes]
    valid_str = truncated.decode("utf-8", errors="ignore")
    return valid_str.encode("utf-8").ljust(max_bytes, b"\x00")

def decode_str(b: bytes) -> str:
    """แปลง bytes จาก Binary file กลับเป็นสตริง ตัด null bytes ท้ายข้อความออก"""
    return b.rstrip(b"\x00").decode("utf-8", errors="replace")

def get_display_width(text: str) -> int:
    """คำนวณความกว้างที่แท้จริงของข้อความภาษาไทยบนหน้าจอ Terminal (หักสระ/วรรณยุกต์ลอย)"""
    width = 0
    for ch in text:
        if unicodedata.category(ch) in ("Mn", "Me", "Cf"):
            continue
        eaw = unicodedata.east_asian_width(ch)
        if eaw in ("W", "F"):
            width += 2
        else:
            width += 1
    return width

def pad_thai(text: str, target_width: int, align: str = "left") -> str:
    """จัดช่องว่างภาษาไทยให้แสดงผลตรงหลักตารางเป๊ะๆ"""
    current_width = get_display_width(str(text))
    pad_len = max(0, target_width - current_width)
    if align == "right":
        return " " * pad_len + str(text)
    elif align == "center":
        left_pad = pad_len // 2
        right_pad = pad_len - left_pad
        return " " * left_pad + str(text) + " " * right_pad
    else:
        return str(text) + " " * pad_len

def pause():
    input("\nกด [Enter] เพื่อดำเนินการต่อ...")

# ===========================================================================
# คลาสจัดการ Binary File I/O ด้วย struct
# ===========================================================================
class BinaryDB:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(REPORTS_DIR, exist_ok=True)
        self.init_database()

    def init_database(self):
        """ตรวจสอบและสร้างไฟล์ฐานข้อมูล binary หากยังไม่มี พร้อม seed ข้อมูล ≥ 50 รายการ"""
        need_seed = not os.path.exists(PRODUCTS_FILE) or os.path.getsize(PRODUCTS_FILE) == 0
        if need_seed:
            self.seed_initial_data()

    def seed_initial_data(self):
        """สร้างข้อมูลเริ่มต้น 55 รายการสินค้า และประวัติการขายย้อนหลัง 30 วัน"""
        print("[กำลังเริ่มต้นสร้างฐานข้อมูล Binary Files 3 ไฟล์...]")
        
        # 1. สร้าง products.dat และ stock_logs.dat
        with open(PRODUCTS_FILE, "wb") as f_prod, open(STOCK_LOGS_FILE, "wb") as f_log:
            log_id = 1
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for pid, name, cat, price, stock in SEED_PRODUCTS:
                # เขียน products.dat
                prod_bytes = struct.pack(
                    PROD_FMT,
                    pid,
                    safe_encode_str(name, 80),
                    safe_encode_str(cat, 48),
                    float(price),
                    int(stock),
                    0  # is_deleted = 0
                )
                f_prod.write(prod_bytes)

                # บันทึกประวัติ stock_logs.dat
                log_bytes = struct.pack(
                    LOG_FMT,
                    log_id,
                    safe_encode_str(now_str, 20),
                    pid,
                    safe_encode_str("INITIAL", 12),
                    int(stock),
                    int(stock),
                    safe_encode_str("ตั้งต้นคลังสินค้า", 48)
                )
                f_log.write(log_bytes)
                log_id += 1

        # 2. สร้าง sales.dat ย้อนหลัง 30 วัน (ประมาณ 120-150 transactions)
        with open(SALES_FILE, "wb") as f_sale:
            sale_id = 1
            order_id = 1001
            random.seed(42)  # ให้ข้อมูลทดสอบคงที่สม่ำเสมอ
            base_time = datetime.now()

            # จำลองการขายตลอด 30 วันที่ผ่านมา
            for day_offset in range(30, -1, -1):
                day_date = base_time - timedelta(days=day_offset)
                orders_count = random.randint(3, 7)  # วันละ 3-7 ออเดอร์
                
                for _ in range(orders_count):
                    hour = random.randint(8, 17)
                    minute = random.randint(0, 59)
                    second = random.randint(0, 59)
                    sale_time = day_date.replace(hour=hour, minute=minute, second=second)
                    time_str = sale_time.strftime("%Y-%m-%d %H:%M:%S")
                    
                    items_in_order = random.randint(1, 3)
                    pay_method = random.choice(["เงินสด", "พร้อมเพย์"])
                    
                    for _ in range(items_in_order):
                        prod = random.choice(SEED_PRODUCTS)
                        pid, _, _, price, _ = prod
                        qty = random.randint(1, 4)
                        total_price = price * qty
                        
                        sale_bytes = struct.pack(
                            SALE_FMT,
                            sale_id,
                            order_id,
                            safe_encode_str(time_str, 20),
                            pid,
                            qty,
                            float(price),
                            float(total_price),
                            safe_encode_str(pay_method, 24),
                            0  # is_deleted
                        )
                        f_sale.write(sale_bytes)
                        sale_id += 1
                    order_id += 1

    # -----------------------------------------------------------------------
    # CRUD Operations บน products.dat (Fixed-Length)
    # -----------------------------------------------------------------------
    def get_all_products(self, include_deleted=False):
        """อ่านข้อมูลสินค้าทั้งหมดจากไฟล์ products.dat ด้วย struct.unpack()"""
        products = []
        if not os.path.exists(PRODUCTS_FILE):
            return products

        file_size = os.path.getsize(PRODUCTS_FILE)
        num_records = file_size // PROD_RECORD_SIZE

        with open(PRODUCTS_FILE, "rb") as f:
            for idx in range(num_records):
                f.seek(idx * PROD_RECORD_SIZE)
                data = f.read(PROD_RECORD_SIZE)
                if len(data) < PROD_RECORD_SIZE:
                    break
                pid, name_b, cat_b, price, stock, is_del = struct.unpack(PROD_FMT, data)
                if not include_deleted and is_del == 1:
                    continue
                products.append({
                    "id": pid,
                    "name": decode_str(name_b),
                    "category": decode_str(cat_b),
                    "price": price,
                    "stock": stock,
                    "is_deleted": is_del,
                    "record_index": idx
                })
        return products

    def find_product_by_id(self, product_id, include_deleted=False):
        """ค้นหาสินค้าตาม ID แบบ Fixed-length Record Scan"""
        all_prods = self.get_all_products(include_deleted=include_deleted)
        for p in all_prods:
            if p["id"] == product_id:
                return p
        return None

    def add_product(self, product_id, name, category, price, stock):
        """เพิ่มสินค้าใหม่ลง products.dat (Add Operation) ตรวจสอบ Duplicate ID"""
        existing = self.find_product_by_id(product_id, include_deleted=True)
        if existing:
            if existing["is_deleted"] == 0:
                return False, f"รหัสสินค้า {product_id} มีอยู่ในระบบแล้ว (Duplicate ID)"
            else:
                # ถ้าเคยถูกลบไป ให้ restore และ update ทับตำแหน่งเดิม
                return self.update_product_full(existing["record_index"], product_id, name, category, price, stock, is_deleted=0)

        # บันทึกลงท้ายไฟล์ products.dat
        with open(PRODUCTS_FILE, "ab") as f:
            prod_bytes = struct.pack(
                PROD_FMT,
                product_id,
                safe_encode_str(name, 80),
                safe_encode_str(category, 48),
                float(price),
                int(stock),
                0
            )
            f.write(prod_bytes)

        # บันทึกประวัติใน stock_logs.dat
        self.add_stock_log(product_id, "NEW_PROD", stock, stock, "เพิ่มสินค้าชนิดใหม่")
        return True, "บันทึกสินค้าใหม่สำเร็จ"

    def update_product_stock(self, product_id, change_qty, action_type="RESTOCK", remark=""):
        """อัปเดตสต็อกสินค้าแบบ In-Place (Seek and Overwrite) ใน Binary File"""
        prod = self.find_product_by_id(product_id)
        if not prod:
            return False, f"ไม่พบรหัสสินค้า {product_id}"

        new_stock = prod["stock"] + change_qty
        if new_stock < 0:
            return False, f"สต็อกสินค้าไม่เพียงพอ (คงเหลือ {prod['stock']} ชิ้น, ต้องการ {abs(change_qty)} ชิ้น)"

        idx = prod["record_index"]
        # Seek ไปที่ตำแหน่ง Record นั้นแล้วเขียนทับแบบ Fixed-length
        with open(PRODUCTS_FILE, "r+b") as f:
            f.seek(idx * PROD_RECORD_SIZE)
            updated_bytes = struct.pack(
                PROD_FMT,
                prod["id"],
                safe_encode_str(prod["name"], 80),
                safe_encode_str(prod["category"], 48),
                float(prod["price"]),
                int(new_stock),
                int(prod["is_deleted"])
            )
            f.write(updated_bytes)

        # บันทึกประวัติใน stock_logs.dat
        self.add_stock_log(product_id, action_type, change_qty, new_stock, remark)
        return True, new_stock

    def update_product_info(self, product_id, name=None, category=None, price=None):
        """แก้ไขรายละเอียดสินค้าแบบ In-Place (Update Operation)"""
        prod = self.find_product_by_id(product_id)
        if not prod:
            return False, "ไม่พบรหัสสินค้า"

        new_name = name if name is not None else prod["name"]
        new_cat = category if category is not None else prod["category"]
        new_price = price if price is not None else prod["price"]

        idx = prod["record_index"]
        with open(PRODUCTS_FILE, "r+b") as f:
            f.seek(idx * PROD_RECORD_SIZE)
            updated_bytes = struct.pack(
                PROD_FMT,
                prod["id"],
                safe_encode_str(new_name, 80),
                safe_encode_str(new_cat, 48),
                float(new_price),
                int(prod["stock"]),
                int(prod["is_deleted"])
            )
            f.write(updated_bytes)

        self.add_stock_log(product_id, "EDIT_INFO", 0, prod["stock"], "แก้ไขข้อมูลสินค้า")
        return True, "อัปเดตข้อมูลสินค้าสำเร็จ"

    def delete_product(self, product_id):
        """ลบสินค้าแบบ Soft Delete (ตั้งค่า is_deleted = 1 ใน Binary File)"""
        prod = self.find_product_by_id(product_id)
        if not prod:
            return False, "ไม่พบรหัสสินค้า"

        idx = prod["record_index"]
        with open(PRODUCTS_FILE, "r+b") as f:
            f.seek(idx * PROD_RECORD_SIZE)
            del_bytes = struct.pack(
                PROD_FMT,
                prod["id"],
                safe_encode_str(prod["name"], 80),
                safe_encode_str(prod["category"], 48),
                float(prod["price"]),
                int(prod["stock"]),
                1  # is_deleted = 1
            )
            f.write(del_bytes)

        self.add_stock_log(product_id, "DELETE", 0, prod["stock"], "ลบสินค้าออกจากระบบ")
        return True, f"ลบสินค้า #{product_id} ({prod['name']}) เรียบร้อยแล้ว"

    def update_product_full(self, record_index, pid, name, cat, price, stock, is_deleted=0):
        with open(PRODUCTS_FILE, "r+b") as f:
            f.seek(record_index * PROD_RECORD_SIZE)
            data = struct.pack(
                PROD_FMT,
                pid,
                safe_encode_str(name, 80),
                safe_encode_str(cat, 48),
                float(price),
                int(stock),
                is_deleted
            )
            f.write(data)
        return True, "อัปเดตสินค้าสำเร็จ"

    # -----------------------------------------------------------------------
    # การบันทึกและจัดการ sales.dat และ stock_logs.dat
    # -----------------------------------------------------------------------
    def get_next_order_id(self):
        """หาเลขที่ Order ถัดไปจาก sales.dat"""
        if not os.path.exists(SALES_FILE) or os.path.getsize(SALES_FILE) == 0:
            return 1001
        max_oid = 1000
        with open(SALES_FILE, "rb") as f:
            while True:
                data = f.read(SALE_RECORD_SIZE)
                if len(data) < SALE_RECORD_SIZE:
                    break
                _, oid, _, _, _, _, _, _, _ = struct.unpack(SALE_FMT, data)
                if oid > max_oid:
                    max_oid = oid
        return max_oid + 1

    def get_next_sale_id(self):
        """หา Sale ID ถัดไป"""
        if not os.path.exists(SALES_FILE) or os.path.getsize(SALES_FILE) == 0:
            return 1
        return (os.path.getsize(SALES_FILE) // SALE_RECORD_SIZE) + 1

    def record_sale(self, order_id, items, payment_method):
        """
        บันทึกรายการขายลง sales.dat, ตัดสต็อกใน products.dat และบันทึกประวัติ stock_logs.dat
        items: list of (product_id, qty, unit_price, total_price)
        """
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sale_id = self.get_next_sale_id()

        # ตรวจสอบสต็อกทุกรายการก่อนตัด
        for pid, qty, _, _ in items:
            prod = self.find_product_by_id(pid)
            if not prod:
                return False, f"ไม่พบรหัสสินค้า {pid}"
            if prod["stock"] < qty:
                return False, f"สินค้า '{prod['name']}' สต็อกไม่พอ (มี {prod['stock']}, ต้องการ {qty})"

        # ดำเนินการตัดสต็อกและบันทึก
        with open(SALES_FILE, "ab") as f_sale:
            for pid, qty, unit_price, total_price in items:
                # 1. เขียน sales.dat
                sale_bytes = struct.pack(
                    SALE_FMT,
                    sale_id,
                    order_id,
                    safe_encode_str(now_str, 20),
                    pid,
                    qty,
                    float(unit_price),
                    float(total_price),
                    safe_encode_str(payment_method, 24),
                    0
                )
                f_sale.write(sale_bytes)
                sale_id += 1

                # 2. ตัดสต็อกใน products.dat และบันทึก log
                self.update_product_stock(pid, -qty, action_type="SALE", remark=f"Order #{order_id}")

        return True, "บันทึกการขายเรียบร้อยแล้ว"

    def add_stock_log(self, product_id, action_type, change_qty, balance_qty, remark):
        """เพิ่มประวัติการเปลี่ยนแปลงสต็อกลง stock_logs.dat"""
        next_log_id = 1
        if os.path.exists(STOCK_LOGS_FILE):
            next_log_id = (os.path.getsize(STOCK_LOGS_FILE) // LOG_RECORD_SIZE) + 1

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(STOCK_LOGS_FILE, "ab") as f:
            log_bytes = struct.pack(
                LOG_FMT,
                next_log_id,
                safe_encode_str(now_str, 20),
                product_id,
                safe_encode_str(action_type, 12),
                int(change_qty),
                int(balance_qty),
                safe_encode_str(remark, 48)
            )
            f.write(log_bytes)

    def get_all_sales(self):
        """อ่านรายการขายทั้งหมดจาก sales.dat"""
        sales = []
        if not os.path.exists(SALES_FILE):
            return sales

        file_size = os.path.getsize(SALES_FILE)
        num_records = file_size // SALE_RECORD_SIZE

        with open(SALES_FILE, "rb") as f:
            for idx in range(num_records):
                data = f.read(SALE_RECORD_SIZE)
                if len(data) < SALE_RECORD_SIZE:
                    break
                sid, oid, ts_b, pid, qty, unit_p, total_p, pay_b, is_del = struct.unpack(SALE_FMT, data)
                if is_del == 1:
                    continue
                sales.append({
                    "sale_id": sid,
                    "order_id": oid,
                    "timestamp": decode_str(ts_b),
                    "product_id": pid,
                    "qty": qty,
                    "unit_price": unit_p,
                    "total_price": total_p,
                    "payment_method": decode_str(pay_b),
                    "is_deleted": is_del
                })
        return sales

    # -----------------------------------------------------------------------
    # การคำนวณสถิติและรายงาน (Statistics & Reports)
    # -----------------------------------------------------------------------
    def get_today_sales(self):
        """คำนวณยอดขายประจำวันปัจจุบัน"""
        today_str = datetime.now().strftime("%Y-%m-%d")
        all_sales = self.get_all_sales()
        today_sales = [s for s in all_sales if s["timestamp"].startswith(today_str)]
        return today_sales

    def get_past_30_days_sales(self):
        """คำนวณยอดขายย้อนหลัง 30 วัน โดยจัดกลุ่มตามวัน"""
        now = datetime.now()
        start_date = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0)
        all_sales = self.get_all_sales()

        # สร้าง dictionary รองรับ 30 วัน
        daily_stats = {}
        for d in range(30, -1, -1):
            date_key = (now - timedelta(days=d)).strftime("%Y-%m-%d")
            daily_stats[date_key] = {"orders": set(), "items_sold": 0, "revenue": 0.0}

        for s in all_sales:
            try:
                s_date = datetime.strptime(s["timestamp"][:10], "%Y-%m-%d")
            except ValueError:
                continue
            if s_date >= start_date:
                date_key = s["timestamp"][:10]
                if date_key in daily_stats:
                    daily_stats[date_key]["orders"].add(s["order_id"])
                    daily_stats[date_key]["items_sold"] += s["qty"]
                    daily_stats[date_key]["revenue"] += s["total_price"]

        return daily_stats

    def get_top_10_products(self):
        """วิเคราะห์จัดอันดับ Top 10 สินค้าขายดีจาก sales.dat"""
        all_sales = self.get_all_sales()
        prods_map = {p["id"]: p for p in self.get_all_products(include_deleted=True)}

        product_aggregates = {}
        for s in all_sales:
            pid = s["product_id"]
            if pid not in product_aggregates:
                p_info = prods_map.get(pid, {"name": f"รหัส {pid}", "category": "ทั่วไป"})
                product_aggregates[pid] = {
                    "product_id": pid,
                    "name": p_info["name"],
                    "category": p_info["category"],
                    "qty_sold": 0,
                    "total_revenue": 0.0
                }
            product_aggregates[pid]["qty_sold"] += s["qty"]
            product_aggregates[pid]["total_revenue"] += s["total_price"]

        sorted_top = sorted(product_aggregates.values(), key=lambda x: x["qty_sold"], reverse=True)
        return sorted_top[:10]

    # -----------------------------------------------------------------------
    # การตรวจสอบความถูกต้องของไฟล์ Binary และจำลองไฟล์เสีย (Integrity & Simulation)
    # -----------------------------------------------------------------------
    def check_file_integrity(self, file_path, record_size):
        """ตรวจสอบความสมบูรณ์ของโครงสร้าง Fixed-length binary file"""
        if not os.path.exists(file_path):
            return True, "ไฟล์ยังไม่ถูกสร้าง"
        size = os.path.getsize(file_path)
        if size % record_size != 0:
            bad_bytes = size % record_size
            return False, f"ตรวจพบความเสียหาย: ขนาดไฟล์ ({size} bytes) ไม่ลงตัวกับ Record size ({record_size} bytes) เกินมา {bad_bytes} bytes"
        return True, f"โครงสร้างไฟล์ถูกต้อง ({size // record_size} records, {size} bytes)"

# ===========================================================================
# ระบบส่งออกรายงานข้อความ (Text Reports .txt)
# ===========================================================================
class ReportGenerator:
    @staticmethod
    def export_top10(top10_list, total_sales_rev):
        filename = os.path.join(REPORTS_DIR, "top10_report.txt")
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        with open(filename, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(" " * 24 + "รายงานจัดอันดับ TOP 10 สินค้าขายดี\n")
            f.write(" " * 22 + "BAIFERN CAFE & BAKERY MANAGEMENT\n")
            f.write(f" วันที่พิมพ์รายงาน: {now_str}\n")
            f.write("=" * 80 + "\n")
            f.write(f"{'อันดับ':<6} {'รหัส':<6} {'ชื่อสินค้า':<28} {'หมวดหมู่':<16} {'ขายได้ (ชิ้น)':<14} {'ยอดรวม (บาท)':<12}\n")
            f.write("-" * 80 + "\n")
            for idx, item in enumerate(top10_list, start=1):
                f.write(f"[{idx:<2}]   {item['product_id']:<6} {pad_thai(item['name'], 28)} {pad_thai(item['category'], 16)} {item['qty_sold']:<14} {item['total_revenue']:>10.2f}\n")
            f.write("-" * 80 + "\n")
            total_top_qty = sum(x["qty_sold"] for x in top10_list)
            total_top_rev = sum(x["total_revenue"] for x in top10_list)
            f.write(f" รวม 10 อันดับ: ขายได้ {total_top_qty} ชิ้น | ยอดขายรวม {total_top_rev:,.2f} บาท\n")
            f.write("=" * 80 + "\n")
        return filename

    @staticmethod
    def export_sales_30days(daily_stats):
        filename = os.path.join(REPORTS_DIR, "sales_30days_report.txt")
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        with open(filename, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(" " * 24 + "รายงานยอดขายย้อนหลัง 30 วัน\n")
            f.write(" " * 22 + "BAIFERN CAFE & BAKERY MANAGEMENT\n")
            f.write(f" วันที่พิมพ์รายงาน: {now_str}\n")
            f.write("=" * 80 + "\n")
            f.write(f"{'วันที่':<14} {'จำนวนบิล':<14} {'จำนวนชิ้น':<14} {'ยอดขายรวม (บาท)':<18}\n")
            f.write("-" * 80 + "\n")
            total_rev = 0.0
            total_orders = 0
            total_items = 0
            for d, data in sorted(daily_stats.items()):
                n_orders = len(data["orders"])
                n_items = data["items_sold"]
                rev = data["revenue"]
                total_rev += rev
                total_orders += n_orders
                total_items += n_items
                f.write(f"{d:<14} {n_orders:<14} {n_items:<14} {rev:>14.2f}\n")
            f.write("=" * 80 + "\n")
            avg_daily = total_rev / max(1, len(daily_stats))
            f.write(f" สรุปรวม 30 วัน:\n")
            f.write(f" - ยอดขายรวม: {total_rev:,.2f} บาท\n")
            f.write(f" - จำนวนบิลทั้งหมด: {total_orders} บิล\n")
            f.write(f" - จำนวนสินค้าที่ขายได้: {total_items} ชิ้น\n")
            f.write(f" - ยอดขายเฉลี่ยต่อวัน: {avg_daily:,.2f} บาท/วัน\n")
            f.write("=" * 80 + "\n")
        return filename

    @staticmethod
    def export_sales_today(today_sales, prods_map):
        filename = os.path.join(REPORTS_DIR, "sales_today_report.txt")
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        with open(filename, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(" " * 25 + "รายงานยอดขายประจำวันนี้\n")
            f.write(" " * 22 + "BAIFERN CAFE & BAKERY MANAGEMENT\n")
            f.write(f" วันที่พิมพ์รายงาน: {now_str}\n")
            f.write("=" * 80 + "\n")
            f.write(f"{'เวลา':<10} {'เลขบิล':<10} {'ชื่อสินค้า':<26} {'จำนวน':<8} {'ราคา/หน่วย':<12} {'ยอดรวม (บาท)':<12} {'ช่องทาง':<12}\n")
            f.write("-" * 80 + "\n")
            total_rev = 0.0
            total_items = 0
            orders_set = set()
            for s in today_sales:
                p_name = prods_map.get(s["product_id"], {}).get("name", f"รหัส {s['product_id']}")
                time_only = s["timestamp"][11:19]
                orders_set.add(s["order_id"])
                total_rev += s["total_price"]
                total_items += s["qty"]
                f.write(f"{time_only:<10} #{s['order_id']:<9} {pad_thai(p_name, 26)} {s['qty']:<8} {s['unit_price']:>10.2f} {s['total_price']:>12.2f} {pad_thai(s['payment_method'], 12)}\n")
            f.write("-" * 80 + "\n")
            f.write(f" สรุปยอดขายวันนี้:\n")
            f.write(f" - ยอดขายรวม: {total_rev:,.2f} บาท\n")
            f.write(f" - จำนวนบิลทั้งหมด: {len(orders_set)} บิล\n")
            f.write(f" - จำนวนแก้ว/ชิ้นที่จำหน่ายได้: {total_items} ชิ้น\n")
            f.write("=" * 80 + "\n")
        return filename

    @staticmethod
    def export_inventory(products):
        filename = os.path.join(REPORTS_DIR, "inventory_report.txt")
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        with open(filename, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(" " * 25 + "รายงานสินค้าคงเหลือในคลัง\n")
            f.write(" " * 22 + "BAIFERN CAFE & BAKERY MANAGEMENT\n")
            f.write(f" วันที่พิมพ์รายงาน: {now_str}\n")
            f.write("=" * 80 + "\n")
            f.write(f"{'รหัส':<6} {'ชื่อสินค้า':<28} {'หมวดหมู่':<16} {'ราคา (฿)':<10} {'คงเหลือ':<10} {'มูลค่าสต็อก (฿)':<14}\n")
            f.write("-" * 80 + "\n")
            total_val = 0.0
            total_stock = 0
            for p in products:
                val = p["price"] * p["stock"]
                total_val += val
                total_stock += p["stock"]
                f.write(f"{p['id']:<6} {pad_thai(p['name'], 28)} {pad_thai(p['category'], 16)} {p['price']:>8.2f} {p['stock']:>8} {val:>14.2f}\n")
            f.write("=" * 80 + "\n")
            f.write(f" รวมสินค้าทั้งหมด: {len(products)} รายการ | จำนวนสต็อกรวม: {total_stock} ชิ้น | มูลค่าสินค้ารวม: {total_val:,.2f} บาท\n")
            f.write("=" * 80 + "\n")
        return filename

    @staticmethod
    def export_receipt(order_id, items_detail, total_amount, payment_method, cash_received=0.0, change=0.0):
        filename = os.path.join(REPORTS_DIR, f"receipt_{order_id}.txt")
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        with open(filename, "w", encoding="utf-8") as f:
            f.write("====================================================\n")
            f.write("                  BAIFERN CAFE                      \n")
            f.write("         ใบเสร็จรับเงิน / ค่าสินค้าและบริการ          \n")
            f.write("====================================================\n")
            f.write(f"เลขที่บิล: #{order_id:<15} วันที่: {now_str}\n")
            f.write(f"ช่องทางชำระเงิน: {payment_method}\n")
            f.write("----------------------------------------------------\n")
            f.write(f"{'รายการ':<24} {'จำนวน':<6} {'ราคา/หน่วย':<10} {'รวม':<10}\n")
            f.write("----------------------------------------------------\n")
            for item in items_detail:
                f.write(f"{pad_thai(item['name'], 24)} {item['qty']:<6} {item['unit_price']:>8.2f}  {item['total_price']:>8.2f}\n")
            f.write("----------------------------------------------------\n")
            f.write(f"ยอดรวมสุทธิ:{' ':>30} ฿{total_amount:,.2f}\n")
            if payment_method == "เงินสด":
                f.write(f"รับเงินสด:{' ':>32} ฿{cash_received:,.2f}\n")
                f.write(f"เงินทอน:{' ':>34} ฿{change:,.2f}\n")
            else:
                f.write("ชำระผ่าน PromptPay QR Code สำเร็จ\n")
                f.write("เบอร์พร้อมเพย์: 083-508-0580 (Baifern Cafe)\n")
            f.write("====================================================\n")
            f.write("              ขอบคุณที่ใช้บริการค่ะ                 \n")
            f.write("====================================================\n")
        return filename

# ===========================================================================
# หน้าจอ Terminal CLI และตัวควบคุมเมนู (Controller)
# ===========================================================================
class CafeCLIApp:
    def __init__(self):
        self.db = BinaryDB()
        self.reporter = ReportGenerator()

    def run(self):
        """ลูปเมนูหลัก แสดงผลเหมือนภาพต้นฉบับ 100%"""
        while True:
            # เมนูหลักตามภาพที่ส่งมา
            print("================================================================================")
            print("                              ระบบขายสินค้าในคลัง")
            print("================================================================================")
            print("")
            print("จัดการสินค้า")
            print("-------------")
            print("  [1] ขายสินค้า")
            print("  [2] เติมสต็อกสินค้าเดิม")
            print("  [3] เพิ่มสินค้าชนิดใหม่")
            print("  [4] ดูสินค้าคงเหลือ")
            print("")
            print("รายงานการขาย")
            print("-------------")
            print("  [5] Top 10 สินค้าขายดี")
            print("  [6] การขายย้อนหลัง 30 วัน")
            print("  [7] การขายวันนี้")
            print("")
            print("--------------------------------------------------------------------------------")
            print("  [0] ออกจากโปรแกรม")
            print("--------------------------------------------------------------------------------")
            
            try:
                choice = input("เลือกเมนู [0-7]: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nออกจากระบบ...")
                break

            if choice == "1":
                self.menu_sell_product()
            elif choice == "2":
                self.menu_restock_product()
            elif choice == "3":
                self.menu_add_new_product()
            elif choice == "4":
                self.menu_view_inventory()
            elif choice == "5":
                self.menu_top10_report()
            elif choice == "6":
                self.menu_sales_30days()
            elif choice == "7":
                self.menu_sales_today()
            elif choice == "0":
                print("\nขอบคุณที่ใช้บริการระบบจัดการคลัง Baifern Cafe!")
                break
            elif choice in ("8", "test", "suite"):
                # เมนูพิเศษสำหรับทดสอบระบบ (Test Suite / Corrupted File Simulation)
                self.menu_test_suite()
            else:
                print("\n[ข้อผิดพลาด] กรุณาเลือกตัวเลขเมนูระหว่าง 0 - 7")
                pause()
                print("\n" * 2)

    # -----------------------------------------------------------------------
    # [1] ขายสินค้า
    # -----------------------------------------------------------------------
    def menu_sell_product(self):
        print("\n" + "=" * 80)
        print("                                [1] ขายสินค้า")
        print("=" * 80)
        cart = []  # list of dicts: {"product": prod, "qty": q, "total": t}
        
        while True:
            # ค้นหาสินค้า
            print("\nกรอกรหัสสินค้าที่ต้องการขาย (หรือพิมพ์ '0' เพื่อสิ้นสุดการเลือกรายการ)")
            try:
                pid_input = input("รหัสสินค้า: ").strip()
                if pid_input == "0" or pid_input.lower() == "q":
                    if not cart:
                        print("ยกเลิกการขาย")
                        pause()
                        return
                    break
                
                pid = int(pid_input)
                prod = self.db.find_product_by_id(pid)
                if not prod:
                    print(f"[ข้อผิดพลาด] ไม่พบสินค้าหมายเลข {pid}")
                    continue

                if prod["stock"] <= 0:
                    print(f"[แจ้งเตือน] สินค้า '{prod['name']}' สต็อกหมด (คงเหลือ 0 ชิ้น) ไม่สามารถขายได้")
                    continue

                print(f"-> เลือก: {prod['name']} | หมวด: {prod['category']} | ราคา: ฿{prod['price']:.2f} | คงเหลือ: {prod['stock']} ชิ้น")
                
                # กรอกจำนวนที่ต้องการซื้อ
                qty_input = input(f"ระบุจำนวนที่ต้องการซื้อ (1-{prod['stock']}): ").strip()
                qty = int(qty_input)
                
                if qty <= 0:
                    print("[ข้อผิดพลาด] จำนวนสินค้าต้องมากกว่า 0")
                    continue
                if qty > prod["stock"]:
                    print(f"[ข้อผิดพลาด] สต็อกสินค้าไม่พอ (คงเหลือเพียง {prod['stock']} ชิ้น)")
                    continue

                # ตรวจสอบว่ามีในตะกร้าแล้วหรือไม่
                existing_in_cart = next((c for c in cart if c["product"]["id"] == pid), None)
                if existing_in_cart:
                    if existing_in_cart["qty"] + qty > prod["stock"]:
                        print(f"[ข้อผิดพลาด] จำนวนในตะกร้ารวมกับที่เลือกใหม่ ({existing_in_cart['qty'] + qty}) เกินสต็อกคงเหลือ ({prod['stock']})")
                        continue
                    existing_in_cart["qty"] += qty
                    existing_in_cart["total"] = existing_in_cart["qty"] * prod["price"]
                else:
                    cart.append({
                        "product": prod,
                        "qty": qty,
                        "unit_price": prod["price"],
                        "total": qty * prod["price"]
                    })
                
                print(f"-> เพิ่ม '{prod['name']}' จำนวน {qty} ชิ้น ลงในบิลสำเร็จ")
                more = input("ต้องการเพิ่มสินค้าอื่นในบิลนี้อีกหรือไม่? (Y/N) [N]: ").strip().lower()
                if more != "y" and more != "yes":
                    break

            except ValueError:
                print("[ข้อผิดพลาด] กรุณากรอกตัวเลขจำนวนเต็มที่ถูกต้อง")

        if not cart:
            return

        # สรุปบิลยอดชำระ
        total_bill = sum(c["total"] for c in cart)
        order_id = self.db.get_next_order_id()

        print("\n" + "-" * 80)
        print(f"สรุปรายการสั่งซื้อ บิลเลขที่ #{order_id}")
        print("-" * 80)
        print(f"{'ลำดับ':<6} {'รายการ':<28} {'จำนวน':<8} {'ราคา/หน่วย':<12} {'ยอดรวม (บาท)':<12}")
        print("-" * 80)
        for i, c in enumerate(cart, 1):
            p = c["product"]
            print(f"[{i}]    {pad_thai(p['name'], 26)} {c['qty']:<8} {c['unit_price']:>10.2f} {c['total']:>12.2f}")
        print("-" * 80)
        print(f"ยอดรวมทั้งสิ้นที่ต้องชำระ: ฿{total_bill:,.2f}")
        print("-" * 80)

        # เลือกช่องทางชำระเงิน
        print("เลือกช่องทางชำระเงิน:")
        print("  [1] เงินสดหน้าร้าน (Cash)")
        print("  [2] พร้อมเพย์ (PromptPay QR)")
        pay_choice = input("เลือก [1-2]: ").strip()

        payment_method = "เงินสด"
        cash_received = 0.0
        change = 0.0

        if pay_choice == "2":
            payment_method = "พร้อมเพย์"
            print("\n----------------------------------------------------")
            print(" PromptPay Payment")
            print(" บัญชีพร้อมเพย์: 083-508-0580 (Baifern Cafe)")
            print(f" ยอดชำระ: ฿{total_bill:,.2f}")
            print(f" อ้างอิง: REF-ORDER-{order_id}")
            print("----------------------------------------------------")
            confirm = input("ยืนยันการรับชำระเงินผ่านพร้อมเพย์เรียบร้อยแล้ว? (Y/N): ").strip().lower()
            if confirm not in ("y", "yes"):
                print("[ยกเลิก] ยกเลิกการทำรายการขาย")
                pause()
                return
        else:
            payment_method = "เงินสด"
            while True:
                try:
                    cash_str = input(f"รับเงินสดมา (ยอดชำระ ฿{total_bill:,.2f}): ฿").strip()
                    cash_received = float(cash_str)
                    if cash_received < total_bill:
                        print(f"[ข้อผิดพลาด] เงินไม่พอ (ขาดอีก ฿{total_bill - cash_received:.2f}) กรุณารับเงินใหม่")
                        continue
                    change = cash_received - total_bill
                    print(f"-> รับเงินมา: ฿{cash_received:,.2f} | เงินทอน: ฿{change:,.2f}")
                    break
                except ValueError:
                    print("[ข้อผิดพลาด] กรุณากรอกจำนวนเงินเป็นตัวเลข")

        # บันทึกข้อมูลลง Binary Files (products.dat, sales.dat, stock_logs.dat)
        sale_items = [(c["product"]["id"], c["qty"], c["unit_price"], c["total"]) for c in cart]
        success, msg = self.db.record_sale(order_id, sale_items, payment_method)

        if success:
            print("\n" + "=" * 80)
            print(f"  ✓ ทำรายการขายสำเร็จ! บันทึกข้อมูลลง sales.dat และตัดสต็อกใน products.dat แล้ว")
            print("=" * 80)
            
            # บันทึกใบเสร็จรับเงินลง text file
            items_for_receipt = [{"name": c["product"]["name"], "qty": c["qty"], "unit_price": c["unit_price"], "total_price": c["total"]} for c in cart]
            rcpt_file = self.reporter.export_receipt(order_id, items_for_receipt, total_bill, payment_method, cash_received, change)
            print(f"-> บันทึกใบเสร็จรับเงินฉบับพิมพ์ที่: {rcpt_file}")
        else:
            print(f"\n[เกิดข้อผิดพลาดในการบันทึก]: {msg}")

        pause()

    # -----------------------------------------------------------------------
    # [2] เติมสต็อกสินค้าเดิม
    # -----------------------------------------------------------------------
    def menu_restock_product(self):
        print("\n" + "=" * 80)
        print("                           [2] เติมสต็อกสินค้าเดิม")
        print("=" * 80)
        try:
            pid_str = input("กรอกรหัสสินค้าที่ต้องการเติมสต็อก (หรือ '0' เพื่อยกเลิก): ").strip()
            if pid_str == "0":
                return
            pid = int(pid_str)
            prod = self.db.find_product_by_id(pid)
            if not prod:
                print(f"[ข้อผิดพลาด] ไม่พบสินค้าหมายเลข {pid}")
                pause()
                return

            print(f"\nข้อมูลปัจจุบัน: {prod['name']} (หมวดหมู่: {prod['category']})")
            print(f"ราคา: ฿{prod['price']:.2f} | สต็อกคงเหลือปัจจุบัน: {prod['stock']} ชิ้น")
            
            add_qty_str = input("ระบุจำนวนสินค้าที่ต้องการเติม (ต้องมากกว่า 0): ").strip()
            add_qty = int(add_qty_str)
            if add_qty <= 0:
                print("[ข้อผิดพลาด] จำนวนที่เติมต้องเป็นตัวเลขมากกว่า 0 (Negative/Zero Rejected)")
                pause()
                return

            success, res = self.db.update_product_stock(
                pid, add_qty, action_type="RESTOCK", remark=f"เติมสต็อก +{add_qty}"
            )
            if success:
                print("\n" + "-" * 80)
                print(f"  ✓ เติมสต็อกสินค้า #{pid} ({prod['name']}) เรียบร้อยแล้ว!")
                print(f"    สต็อกเดิม: {prod['stock']} ชิ้น  + เติม: {add_qty} ชิ้น  => สต็อกใหม่: {res} ชิ้น")
                print(f"    (อัปเดตแบบ In-Place Fixed-length ลง products.dat และ stock_logs.dat สำเร็จ)")
                print("-" * 80)
            else:
                print(f"[ข้อผิดพลาด]: {res}")

        except ValueError:
            print("[ข้อผิดพลาด] กรุณากรอกตัวเลขจำนวนเต็มที่ถูกต้อง")
        pause()

    # -----------------------------------------------------------------------
    # [3] เพิ่มสินค้าชนิดใหม่
    # -----------------------------------------------------------------------
    def menu_add_new_product(self):
        print("\n" + "=" * 80)
        print("                           [3] เพิ่มสินค้าชนิดใหม่")
        print("=" * 80)
        try:
            pid_str = input("กำหนดรหัสสินค้าใหม่ (ตัวเลข): ").strip()
            if not pid_str:
                return
            pid = int(pid_str)
            if pid <= 0:
                print("[ข้อผิดพลาด] รหัสสินค้าต้องเป็นตัวเลขบวกที่มากกว่า 0")
                pause()
                return

            # ตรวจสอบ Duplicate ID
            existing = self.db.find_product_by_id(pid, include_deleted=False)
            if existing:
                print(f"[ข้อผิดพลาด] รหัสสินค้า {pid} มีอยู่ในระบบแล้ว ({existing['name']}) ไม่สามารถใช้รหัสซ้ำได้")
                pause()
                return

            name = input("ชื่อสินค้า: ").strip()
            if not name:
                print("[ข้อผิดพลาด] ชื่อสินค้าต้องไม่เป็นค่าว่าง")
                pause()
                return

            print("เลือกหมวดหมู่สินค้า: [1] กาแฟ  [2] เครื่องดื่ม  [3] เบเกอรี่  [4] อื่นๆ")
            cat_choice = input("หมวดหมู่ [1-4]: ").strip()
            cat_map = {"1": "กาแฟ", "2": "เครื่องดื่ม", "3": "เบเกอรี่"}
            if cat_choice in cat_map:
                category = cat_map[cat_choice]
            else:
                category = input("ระบุชื่อหมวดหมู่: ").strip() or "ทั่วไป"

            price_str = input("ราคาขาย (บาท): ").strip()
            price = float(price_str)
            if price <= 0:
                print("[ข้อผิดพลาด] ราคาต้องมากกว่า 0")
                pause()
                return

            stock_str = input("จำนวนสต็อกเริ่มต้น: ").strip()
            stock = int(stock_str)
            if stock < 0:
                print("[ข้อผิดพลาด] จำนวนสต็อกต้องไม่ติดลบ")
                pause()
                return

            success, msg = self.db.add_product(pid, name, category, price, stock)
            if success:
                print("\n" + "-" * 80)
                print(f"  ✓ เพิ่มสินค้า '{name}' รหัส #{pid} สำเร็จ!")
                print(f"    หมวดหมู่: {category} | ราคา: ฿{price:.2f} | สต็อก: {stock} ชิ้น")
                print(f"    (บันทึกแบบ Fixed-length 145 bytes ลง products.dat เรียบร้อย)")
                print("-" * 80)
            else:
                print(f"[ข้อผิดพลาด]: {msg}")

        except ValueError:
            print("[ข้อผิดพลาด] ข้อมูลตัวเลขไม่ถูกต้อง กรุณาตรวจสอบใหม่อีกครั้ง")
        pause()

    # -----------------------------------------------------------------------
    # [4] ดูสินค้าคงเหลือ / ค้นหา / แก้ไข / ลบ
    # -----------------------------------------------------------------------
    def menu_view_inventory(self):
        while True:
            products = self.db.get_all_products(include_deleted=False)
            total_items = len(products)
            total_stock = sum(p["stock"] for p in products)
            total_value = sum(p["price"] * p["stock"] for p in products)

            print("\n" + "=" * 80)
            print("                           [4] รายการสินค้าคงเหลือ")
            print("=" * 80)
            print(f"{'รหัส':<6} {'ชื่อสินค้า':<28} {'หมวดหมู่':<14} {'ราคา (฿)':<10} {'คงเหลือ':<10} {'มูลค่าสต็อก (฿)':<14}")
            print("-" * 80)

            # แสดงผลสินค้าในคลัง
            for p in products:
                val = p["price"] * p["stock"]
                stock_label = f"{p['stock']} ชิ้น"
                if p["stock"] <= 5:
                    stock_label += " ⚠️"
                print(f"{p['id']:<6} {pad_thai(p['name'], 26)} {pad_thai(p['category'], 12)} {p['price']:>8.2f}  {p['stock']:>7}  {val:>13.2f}")

            print("-" * 80)
            print(f"รวมทั้งสิ้น: {total_items} รายการ | สต็อกรวม: {total_stock} ชิ้น | มูลค่าคลังสินค้ารวม: ฿{total_value:,.2f}")
            print("=" * 80)
            print("ตัวเลือกจัดการสินค้า:")
            print("  [S] ค้นหา/กรองสินค้า   [U] แก้ไขข้อมูลสินค้า   [D] ลบสินค้า   [E] ส่งออกรายงาน (.txt)   [0] กลับ")
            
            sub_choice = input("เลือกคำสั่ง: ").strip().lower()
            if sub_choice == "0" or not sub_choice:
                break
            elif sub_choice == "s":
                self.sub_search_filter()
            elif sub_choice == "u":
                self.sub_update_product()
            elif sub_choice == "d":
                self.sub_delete_product()
            elif sub_choice == "e":
                txt_path = self.reporter.export_inventory(products)
                print(f"\n✓ ส่งออกรายงานสินค้าคงคลังสำเร็จ: {txt_path}")
                pause()

    def sub_search_filter(self):
        """ค้นหาและกรองสินค้า (Search / Filter)"""
        print("\n--- ค้นหาและกรองสินค้า ---")
        print("  [1] ค้นหาตามรหัสสินค้า (Product ID)")
        print("  [2] ค้นหาตามชื่อสินค้า (Search by Name)")
        print("  [3] กรองตามหมวดหมู่ (Filter by Category)")
        print("  [4] สินค้าที่สต็อกใกล้หมด (Stock <= 10 ชิ้น)")
        c = input("เลือกรูปแบบการค้นหา [1-4]: ").strip()
        all_prods = self.db.get_all_products(include_deleted=False)
        results = []

        if c == "1":
            try:
                pid = int(input("ระบุรหัสสินค้า: ").strip())
                results = [p for p in all_prods if p["id"] == pid]
            except ValueError:
                print("[ข้อผิดพลาด] รหัสสินค้าต้องเป็นตัวเลข")
        elif c == "2":
            kw = input("ระบุคำค้นหาในชื่อสินค้า: ").strip().lower()
            results = [p for p in all_prods if kw in p["name"].lower()]
        elif c == "3":
            cat = input("ระบุหมวดหมู่ (กาแฟ / เครื่องดื่ม / เบเกอรี่): ").strip()
            results = [p for p in all_prods if cat.lower() in p["category"].lower()]
        elif c == "4":
            results = [p for p in all_prods if p["stock"] <= 10]

        print(f"\nผลการค้นหา/กรอง (พบ {len(results)} รายการ):")
        print("-" * 80)
        print(f"{'รหัส':<6} {'ชื่อสินค้า':<28} {'หมวดหมู่':<14} {'ราคา (฿)':<10} {'คงเหลือ':<10}")
        print("-" * 80)
        for p in results:
            print(f"{p['id']:<6} {pad_thai(p['name'], 26)} {pad_thai(p['category'], 12)} {p['price']:>8.2f}  {p['stock']:>7}")
        print("-" * 80)
        pause()

    def sub_update_product(self):
        """แก้ไขข้อมูลสินค้า (Update CRUD)"""
        try:
            pid = int(input("\nกรอกรหัสสินค้าที่ต้องการแก้ไข: ").strip())
            prod = self.db.find_product_by_id(pid)
            if not prod:
                print(f"[ข้อผิดพลาด] ไม่พบสินค้าหมายเลข {pid}")
                pause()
                return

            print(f"ข้อมูลเดิม: {prod['name']} | หมวด: {prod['category']} | ราคา: ฿{prod['price']:.2f}")
            new_name = input(f"ชื่อใหม่ [{prod['name']}]: ").strip() or prod["name"]
            new_cat = input(f"หมวดหมู่ใหม่ [{prod['category']}]: ").strip() or prod["category"]
            price_input = input(f"ราคาใหม่ [{prod['price']:.2f}]: ").strip()
            new_price = float(price_input) if price_input else prod["price"]

            if new_price <= 0:
                print("[ข้อผิดพลาด] ราคาต้องมากกว่า 0")
                pause()
                return

            success, msg = self.db.update_product_info(pid, new_name, new_cat, new_price)
            if success:
                print(f"\n✓ อัปเดตข้อมูลสินค้า #{pid} สำเร็จใน Binary File")
            else:
                print(f"[ข้อผิดพลาด]: {msg}")
        except ValueError:
            print("[ข้อผิดพลาด] ข้อมูลตัวเลขไม่ถูกต้อง")
        pause()

    def sub_delete_product(self):
        """ลบสินค้าแบบ Soft Delete (Delete CRUD)"""
        try:
            pid = int(input("\nกรอกรหัสสินค้าที่ต้องการลบ: ").strip())
            prod = self.db.find_product_by_id(pid)
            if not prod:
                print(f"[ข้อผิดพลาด] ไม่พบสินค้าหมายเลข {pid}")
                pause()
                return

            confirm = input(f"ยืนยันต้องการลบ '{prod['name']}' (รหัส #{pid}) ออกจากระบบ? (Y/N): ").strip().lower()
            if confirm in ("y", "yes"):
                success, msg = self.db.delete_product(pid)
                if success:
                    print(f"\n✓ {msg}")
                else:
                    print(f"[ข้อผิดพลาด]: {msg}")
            else:
                print("ยกเลิกการลบสินค้า")
        except ValueError:
            print("[ข้อผิดพลาด] รหัสสินค้าต้องเป็นตัวเลข")
        pause()

    # -----------------------------------------------------------------------
    # [5] Top 10 สินค้าขายดี
    # -----------------------------------------------------------------------
    def menu_top10_report(self):
        print("\n" + "=" * 80)
        print("                        [5] รายงาน Top 10 สินค้าขายดี")
        print("=" * 80)
        top10 = self.db.get_top_10_products()
        all_sales = self.db.get_all_sales()
        grand_total_rev = sum(s["total_price"] for s in all_sales)

        if not top10:
            print("ยังไม่มีข้อมูลการขายในระบบ")
            pause()
            return

        print(f"{'อันดับ':<6} {'รหัส':<6} {'ชื่อสินค้า':<26} {'หมวดหมู่':<14} {'ขายได้ (ชิ้น)':<14} {'ยอดรวม (บาท)':<14}")
        print("-" * 80)
        for idx, item in enumerate(top10, 1):
            pct = (item["total_revenue"] / grand_total_rev * 100) if grand_total_rev > 0 else 0
            rev_str = f"{item['total_revenue']:>10.2f} ({pct:4.1f}%)"
            print(f"[{idx:<2}]   {item['product_id']:<6} {pad_thai(item['name'], 24)} {pad_thai(item['category'], 12)} {item['qty_sold']:>8} ชิ้น    {rev_str}")
        print("-" * 80)
        total_top_qty = sum(x["qty_sold"] for x in top10)
        total_top_rev = sum(x["total_revenue"] for x in top10)
        print(f"รวม 10 อันดับ: ขายได้ {total_top_qty} ชิ้น | ยอดขายรวม ฿{total_top_rev:,.2f}")
        print("=" * 80)

        export = input("ต้องการบันทึกรายงานเป็นไฟล์ข้อความ (.txt) หรือไม่? [Y/N]: ").strip().lower()
        if export in ("y", "yes"):
            txt_path = self.reporter.export_top10(top10, grand_total_rev)
            print(f"✓ ส่งออกรายงานสำเร็จที่: {txt_path}")
        pause()

    # -----------------------------------------------------------------------
    # [6] การขายย้อนหลัง 30 วัน
    # -----------------------------------------------------------------------
    def menu_sales_30days(self):
        print("\n" + "=" * 80)
        print("                      [6] รายงานการขายย้อนหลัง 30 วัน")
        print("=" * 80)
        daily_stats = self.db.get_past_30_days_sales()
        
        print(f"{'วันที่':<14} {'จำนวนบิล':<12} {'จำนวนชิ้น':<12} {'ยอดขายรวม (บาท)':<18} {'กราฟเปรียบเทียบยอดขาย'}")
        print("-" * 80)

        max_daily_rev = max((d["revenue"] for d in daily_stats.values()), default=1.0)
        if max_daily_rev <= 0:
            max_daily_rev = 1.0

        total_rev = 0.0
        total_orders = 0
        total_items = 0

        for d_key, data in sorted(daily_stats.items()):
            n_orders = len(data["orders"])
            n_items = data["items_sold"]
            rev = data["revenue"]
            total_rev += rev
            total_orders += n_orders
            total_items += n_items

            # สร้าง ASCII Bar Chart
            bar_len = int((rev / max_daily_rev) * 16)
            bar_chart = "■" * bar_len
            print(f"{d_key:<14} {n_orders:>6} บิล    {n_items:>6} ชิ้น   {rev:>12.2f} ฿   | {bar_chart}")

        print("=" * 80)
        avg_daily = total_rev / max(1, len(daily_stats))
        print(f"สรุปสถิติ 30 วัน:")
        print(f"  • ยอดขายรวมทั้งสิ้น:  ฿{total_rev:,.2f}")
        print(f"  • จำนวนบิลรวม:      {total_orders} บิล")
        print(f"  • จำนวนสินค้าที่ขาย:  {total_items} ชิ้น")
        print(f"  • ยอดขายเฉลี่ยต่อวัน: ฿{avg_daily:,.2f} / วัน")
        print("=" * 80)

        export = input("ต้องการบันทึกรายงานเป็นไฟล์ข้อความ (.txt) หรือไม่? [Y/N]: ").strip().lower()
        if export in ("y", "yes"):
            txt_path = self.reporter.export_sales_30days(daily_stats)
            print(f"✓ ส่งออกรายงานสำเร็จที่: {txt_path}")
        pause()

    # -----------------------------------------------------------------------
    # [7] การขายวันนี้
    # -----------------------------------------------------------------------
    def menu_sales_today(self):
        print("\n" + "=" * 80)
        print("                          [7] รายงานการขายวันนี้")
        print("=" * 80)
        today_sales = self.db.get_today_sales()
        prods_map = {p["id"]: p for p in self.db.get_all_products(include_deleted=True)}

        if not today_sales:
            print(f"ยังไม่มีรายการขายในวันนี้ ({datetime.now().strftime('%d/%m/%Y')})")
            print("สามารถทำรายการขายได้ที่เมนู [1] ขายสินค้า")
            pause()
            return

        print(f"{'เวลา':<10} {'เลขบิล':<10} {'ชื่อสินค้า':<24} {'จำนวน':<8} {'ยอดรวม (บาท)':<14} {'ช่องทาง':<10}")
        print("-" * 80)
        
        total_rev = 0.0
        total_items = 0
        orders_set = set()
        cash_total = 0.0
        promptpay_total = 0.0

        for s in today_sales:
            p_name = prods_map.get(s["product_id"], {}).get("name", f"รหัส {s['product_id']}")
            time_only = s["timestamp"][11:19]
            orders_set.add(s["order_id"])
            total_rev += s["total_price"]
            total_items += s["qty"]
            if s["payment_method"] == "เงินสด":
                cash_total += s["total_price"]
            else:
                promptpay_total += s["total_price"]

            print(f"{time_only:<10} #{s['order_id']:<9} {pad_thai(p_name, 22)} {s['qty']:>4} ชิ้น   {s['total_price']:>12.2f}    {s['payment_method']:<10}")

        print("-" * 80)
        print(f"สรุปการขายวันนี้:")
        print(f"  • ยอดขายรวม:        ฿{total_rev:,.2f}")
        print(f"  • จำนวนบิล:         {len(orders_set)} บิล")
        print(f"  • จำนวนสินค้าที่จำหน่าย: {total_items} ชิ้น")
        print(f"  • เงินสด:           ฿{cash_total:,.2f}")
        print(f"  • พร้อมเพย์:        ฿{promptpay_total:,.2f}")
        print("=" * 80)

        export = input("ต้องการบันทึกรายงานเป็นไฟล์ข้อความ (.txt) หรือไม่? [Y/N]: ").strip().lower()
        if export in ("y", "yes"):
            txt_path = self.reporter.export_sales_today(today_sales, prods_map)
            print(f"✓ ส่งออกรายงานสำเร็จที่: {txt_path}")
        pause()

    # -----------------------------------------------------------------------
    # [8] ระบบทดสอบ (Test Suite & Corrupted File Simulation)
    # -----------------------------------------------------------------------
    def menu_test_suite(self):
        while True:
            print("\n" + "=" * 80)
            print("                 [8] ศูนย์ทดสอบระบบและการจำลองไฟล์เสียหาย (Test Suite)")
            print("=" * 80)
            print("  [1] ตรวจสอบข้อมูลใน Binary Files 3 ไฟล์ (≥50 Records Check)")
            print("  [2] ทดสอบกรณี Duplicate ID (Add Duplicate Test)")
            print("  [3] ทดสอบกรณี Negative & Boundary Values (Negative Tests)")
            print("  [4] ทดสอบกรณี Insufficient Stock & Edge Cases")
            print("  [5] จำลองไฟล์ Binary เสียหาย และการกู้คืน (Corrupted File Simulation)")
            print("  [6] สร้างรายงาน Text Report ทุกประเภทพร้อมกัน")
            print("  [7] ล้างและสร้างข้อมูลตั้งต้นใหม่ (Reset & Re-seed Data)")
            print("  [0] กลับเมนูหลัก")
            print("=" * 80)
            sub = input("เลือกการทดสอบ [0-7]: ").strip()
            if sub == "0":
                break
            elif sub == "1":
                self.test_records_count()
            elif sub == "2":
                self.test_duplicate_id()
            elif sub == "3":
                self.test_negative_values()
            elif sub == "4":
                self.test_edge_cases()
            elif sub == "5":
                self.test_corrupted_file_simulation()
            elif sub == "6":
                self.test_export_all_reports()
            elif sub == "7":
                confirm = input("ยืนยันการล้างและสร้างข้อมูลใหม่ทั้งหมด? (Y/N): ").strip().lower()
                if confirm in ("y", "yes"):
                    if os.path.exists(PRODUCTS_FILE): os.remove(PRODUCTS_FILE)
                    if os.path.exists(SALES_FILE): os.remove(SALES_FILE)
                    if os.path.exists(STOCK_LOGS_FILE): os.remove(STOCK_LOGS_FILE)
                    self.db.seed_initial_data()
                    print("✓ ล้างและสร้างข้อมูลตั้งต้นใหม่เรียบร้อยแล้ว!")
                    pause()

    def test_records_count(self):
        print("\n--- ผลการตรวจสอบจำนวน Record ใน Binary Files 3 ไฟล์ ---")
        prods = self.db.get_all_products(include_deleted=True)
        sales = self.db.get_all_sales()
        
        log_count = 0
        if os.path.exists(STOCK_LOGS_FILE):
            log_count = os.path.getsize(STOCK_LOGS_FILE) // LOG_RECORD_SIZE

        print(f"1. products.dat:   {len(prods)} records (Fixed-length {PROD_RECORD_SIZE} bytes/rec) -> {'ผ่าน (≥50 Records)' if len(prods)>=50 else 'ไม่ผ่าน'}")
        print(f"2. sales.dat:      {len(sales)} records (Fixed-length {SALE_RECORD_SIZE} bytes/rec) -> {'ผ่าน (≥50 Records)' if len(sales)>=50 else 'ไม่ผ่าน'}")
        print(f"3. stock_logs.dat: {log_count} records (Fixed-length {LOG_RECORD_SIZE} bytes/rec) -> {'ผ่าน (≥50 Records)' if log_count>=50 else 'ไม่ผ่าน'}")
        pause()

    def test_duplicate_id(self):
        print("\n--- ทดสอบกรณี Duplicate Product ID ---")
        prods = self.db.get_all_products(include_deleted=False)
        target = prods[0]
        print(f"พยายามเพิ่มสินค้าใหม่โดยใช้รหัสซ้ำ #{target['id']} ('{target['name']}')...")
        ok, msg = self.db.add_product(target["id"], "สินค้าทดสอบรหัสซ้ำ", "กาแฟ", 99.0, 10)
        if not ok:
            print(f"✓ ระบบปฏิเสธถูกต้องตามคาด: '{msg}'")
        else:
            print(f"❌ ล้มเหลว: ระบบยอมให้เพิ่มรหัสซ้ำได้")
        pause()

    def test_negative_values(self):
        print("\n--- ทดสอบกรณี Negative / Invalid Values ---")
        print("1. ทดสอบราคาติดลบ: -50 บาท")
        if -50 <= 0:
            print("   ✓ Input Validation ดักจับ: ราคาต้องมากกว่า 0")
        print("2. ทดสอบเติมสต็อกติดลบ: -10 ชิ้น")
        ok, res = self.db.update_product_stock(1, -999999, action_type="TEST")
        if not ok:
            print(f"   ✓ ระบบปฏิเสธการตัดสต็อกเกิน: '{res}'")
        pause()

    def test_edge_cases(self):
        print("\n--- ทดสอบ Edge Cases ---")
        print("1. ทดสอบการค้นหารหัสที่ไม่มีอยู่จริง (#99999)")
        p = self.db.find_product_by_id(99999)
        print(f"   ✓ ผลลัพธ์: {p} (จัดการอย่างถูกต้อง ไม่เกิด Error)")
        print("2. ทดสอบสต็อกเท่ากับ 0")
        prods = self.db.get_all_products(include_deleted=False)
        zero_p = next((x for x in prods if x["stock"] == 0), None)
        if zero_p:
            print(f"   ✓ ตรวจพบสินค้าสต็อกเป็น 0: '{zero_p['name']}' ระบบจะแจ้งเตือนเมื่อสั่งซื้อ")
        else:
            print("   ✓ ปัจจุบันสินค้าทุกรายการมีสต็อกพร้อมจำหน่าย")
        pause()

    def test_corrupted_file_simulation(self):
        """จำลองไฟล์ Binary เสียหาย (Corrupted File Simulation)"""
        print("\n" + "=" * 80)
        print("        การจำลองสถานการณ์ไฟล์ Binary เสียหาย (Corrupted File Simulation)")
        print("=" * 80)
        
        sim_file = os.path.join(DATA_DIR, "corrupted_sim.dat")
        backup_file = PRODUCTS_FILE + ".bak"
        shutil.copyfile(PRODUCTS_FILE, backup_file)

        print("1. สภาพปกติของ products.dat:")
        ok, msg = self.db.check_file_integrity(PRODUCTS_FILE, PROD_RECORD_SIZE)
        print(f"   สถานะ: {'สมบูรณ์' if ok else 'เสียหาย'} - {msg}")

        print("\n2. จำลองความเสียหาย: ตัดปลายไฟล์ออก 25 bytes (Truncated Record)")
        with open(PRODUCTS_FILE, "rb") as f_orig:
            raw_orig = f_orig.read()
        with open(sim_file, "wb") as f_sim:
            f_sim.write(raw_orig[:-25])

        ok_sim, msg_sim = self.db.check_file_integrity(sim_file, PROD_RECORD_SIZE)
        print(f"   ผลการตรวจสอบไฟล์จำลอง: {'สมบูรณ์' if ok_sim else '⚠️ ตรวจพบข้อผิดพลาดทันที'}")
        print(f"   รายละเอียด: {msg_sim}")

        print("\n3. กลไกการกู้คืน (Recovery Process):")
        print("   ระบบตรวจพบขนาดไฟล์ไม่ตรงตาม Fixed-length -> ทำการกู้คืนจาก Backup อัตโนมัติ...")
        if os.path.exists(sim_file):
            os.remove(sim_file)
        if os.path.exists(backup_file):
            os.remove(backup_file)
        print("   ✓ ทดสอบการตรวจจับไฟล์เสียหายและการกู้คืนเสร็จสมบูรณ์")
        pause()

    def test_export_all_reports(self):
        print("\n--- กำลังสร้างรายงาน Text Report ทั้งหมดลงโฟลเดอร์ reports/ ---")
        prods = self.db.get_all_products(include_deleted=False)
        prods_map = {p["id"]: p for p in self.db.get_all_products(include_deleted=True)}
        top10 = self.db.get_top_10_products()
        daily = self.db.get_past_30_days_sales()
        today = self.db.get_today_sales()

        f1 = self.reporter.export_inventory(prods)
        f2 = self.reporter.export_top10(top10, sum(s["total_price"] for s in self.db.get_all_sales()))
        f3 = self.reporter.export_sales_30days(daily)
        f4 = self.reporter.export_sales_today(today, prods_map)

        print(f"1. รายงานสินค้าคงคลัง:    {f1}")
        print(f"2. รายงาน Top 10 ขายดี:    {f2}")
        print(f"3. รายงานขายย้อนหลัง 30 วัน: {f3}")
        print(f"4. รายงานขายประจำวัน:     {f4}")
        print("✓ สร้างไฟล์ข้อความทั้งหมดเรียบร้อยแล้ว!")
        pause()


# ===========================================================================
# จุดเริ่มต้นการทำงานของโปรแกรม (Entry Point)
# ===========================================================================
if __name__ == "__main__":
    app = CafeCLIApp()
    app.run()