import itertools
from datetime import datetime
from flask import Flask, render_template, request, session, jsonify, Response
from jinja2 import DictLoader


app = Flask(__name__)
app.secret_key = "baifern-cafe-dev-secret"  # เปลี่ยนเป็นค่าอื่นก่อนใช้งานจริง


# ===========================================================================
# ส่วนที่ 0: PromptPay QR (มาตรฐาน EMV QR Code ของธนาคารแห่งประเทศไทย)
# ===========================================================================
# เปลี่ยนเป็นเบอร์พร้อมเพย์ หรือเลขบัตรประชาชน/เลขผู้เสียภาษีของร้านจริง
PROMPTPAY_ID = "0835080580"


def _crc16_ccitt(data: bytes) -> int:
    """คำนวณ checksum แบบ CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF)
    ตามที่มาตรฐาน EMV QR Code กำหนดไว้ท้าย payload"""
    crc = 0xFFFF
    for b in data:
        crc ^= (b << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def _tlv(tag, value):
    """ห่อค่าเป็นรูปแบบ Tag-Length-Value: เลขแท็ก 2 หลัก + ความยาว 2 หลัก + ค่า
    เช่น tag='53', value='764' -> '53' + '03' + '764' = '530376 4'"""
    return f"{tag}{len(value):02d}{value}"


def _format_promptpay_target(pp_id):
    """แปลงเบอร์/เลขที่ตั้งไว้ให้เป็นรูปแบบ subtag+value ตามสเปค PromptPay
    - เลขประจำตัว 13 หลัก (บัตร ปชช./เลขผู้เสียภาษี) -> subtag '02'
    - เบอร์โทร -> subtag '01' เอา 9 หลักท้ายเติม '0066' นำหน้า (แทนเลข 0 ตัวแรก)
    """
    digits = "".join(ch for ch in pp_id if ch.isdigit())
    if len(digits) >= 13:
        return "02", digits[-13:]
    last9 = digits[-9:]
    return "01", "0066" + last9


def build_promptpay_payload(pp_id, amount):
    """สร้าง payload string สำหรับ QR พร้อมเพย์ที่ระบุจำนวนเงินตายตัว (dynamic QR)"""
    subtag, value = _format_promptpay_target(pp_id)
    merchant_info = _tlv("00", "A000000677010111") + _tlv(subtag, value)

    payload = ""
    payload += _tlv("00", "01")                    # Payload Format Indicator
    payload += _tlv("01", "12")                     # 12 = dynamic QR (มีจำนวนเงินระบุ)
    payload += _tlv("29", merchant_info)            # ข้อมูลบัญชีพร้อมเพย์
    payload += _tlv("53", "764")                    # รหัสสกุลเงิน 764 = บาทไทย
    payload += _tlv("54", f"{amount:.2f}")          # จำนวนเงิน
    payload += _tlv("58", "TH")                     # รหัสประเทศ
    payload += "6304"                               # แท็ก CRC (เติมค่าจริงด้านล่าง)

    crc = _crc16_ccitt(payload.encode("ascii"))
    payload += f"{crc:04X}"
    return payload

# ===========================================================================
# ส่วนที่ 1: เมนูและตัวเลือกเสริม
# ===========================================================================
SUGAR_OPTS = ["หวานปกติ", "หวานน้อย 50%", "หวานน้อย 25%", "ไม่หวาน"]
ICE_OPTS = ["น้ำแข็งปกติ", "น้ำแข็งน้อย", "ไม่ใส่น้ำแข็ง"]

DRINK_TOPPINGS = [
    {"name": "ไข่มุก", "price": 10},
    {"name": "วิปครีมสด", "price": 15},
    {"name": "เยลลี่ลิ้นจี่", "price": 10},
    {"name": "ชอตกาแฟเพิ่ม", "price": 20},
]
BAKERY_TOPPINGS = [
    {"name": "ไอศกรีมสกู๊ป", "price": 25},
    {"name": "ซอสช็อกโกแลต", "price": 10},
    {"name": "วิปครีมสด", "price": 15},
]

MENU = [
    {
        "id": 1, "cat": "กาแฟ", "name": "เอสเปรสโซ",
        "desc": "เข้มข้น หอมกลิ่นคั่วเข้ม",
        "styles": {"ร้อน": 60, "เย็น": 60},
        "image": "เอส.jpg", "bg": "#EFE3CC",
        "sugar": True, "toppings": DRINK_TOPPINGS,
    },
    {
        "id": 2, "cat": "กาแฟ", "name": "ลาเต้",
        "desc": "นมสตีมเนียนนุ่ม หวานมันกำลังดี",
        "styles": {"ร้อน": 65, "เย็น": 70, "ปั่น": 75},
        "image": "ลาเต้.jpg", "bg": "#EFE3CC",
        "sugar": True, "toppings": DRINK_TOPPINGS,
    },
    {
        "id": 3, "cat": "กาแฟ", "name": "อเมริกาโน่",
        "desc": "บางเบา ดื่มง่าย เข้มสดชื่น",
        "styles": {"ร้อน": 55, "เย็น": 60},
        "image": "โน่ร้อน.jpg", "bg": "#EFE3CC",
        "sugar": True, "toppings": DRINK_TOPPINGS,
    },
    {
        "id": 17, "cat": "กาแฟ", "name": "คาปูชิโน่",
        "desc": "คาปูชิโน่แก้วโปรด ฟองนมฟูโอบใจ",
        "styles": {"ร้อน": 55, "เย็น": 60},
        "image": "คาปู.jpg", "bg": "#EFE3CC",
        "sugar": True, "toppings": DRINK_TOPPINGS,
    },
     {
        "id": 21, "cat": "กาแฟ", "name": "มัคคิอาโต้",
        "desc": "หอมคาราเมล ละมุนใจทุกเลเยอร์",
        "styles": {"ร้อน": 55, "เย็น": 60},
        "image": "มิคคิอาโต้.jpg", "bg": "#EFE3CC",
        "sugar": True, "toppings": DRINK_TOPPINGS,
    },
    {
        "id": 4, "cat": "เครื่องดื่ม", "name": "ชาไทย",
        "desc": "หอมกลิ่นใบชา หวานมัน",
        "styles": {"ร้อน": 55, "เย็น": 60, "ปั่น": 65},
        "image": "ชาไทยเย็น.jpg", "bg": "#F3D9B8",
        "sugar": True, "toppings": DRINK_TOPPINGS,
    },
    {
        "id": 5, "cat": "เครื่องดื่ม", "name": "ชามะนาว",
        "desc": "เปรี้ยวสดชื่น",
        "styles": {"เย็น": 55, "ปั่น": 60},
        "image": "ชามะนาว.jpg", "bg": "#F3D9B8",
        "sugar": True, "toppings": DRINK_TOPPINGS,
    },
    {
        "id": 6, "cat": "เครื่องดื่ม", "name": "มัทฉะลาเต้",
        "desc": "ชาเขียวญี่ปุ่นแท้",
        "styles": {"ร้อน": 70, "เย็น": 75, "ปั่น": 80},
        "image": "มัจฉะ.jpg", "bg": "#DCE7C8",
        "sugar": True, "toppings": DRINK_TOPPINGS,
    },
    {
        "id": 18, "cat": "เครื่องดื่ม", "name": "ชาไต้หวัน",
        "desc": "ชาหอมตะโกน หวานน้อยแต่นัวมาก ดื่มแล้วสดชื่นสุดๆ",
        "styles": {"ร้อน": 70, "เย็น": 75, "ปั่น": 80},
        "image": "ใต้หวัน.jpg", "bg": "#DCE7C8",
        "sugar": True, "toppings": DRINK_TOPPINGS,
    },
    {
        "id": 19, "cat": "เครื่องดื่ม", "name": "โกโก้",
        "desc": "เข้มข้นสะใจ โกโก้แท้ๆ",
        "styles": {"ร้อน": 70, "เย็น": 75, "ปั่น": 80},
        "image": "โกโก้.jpg", "bg": "#DCE7C8",
        "sugar": True, "toppings": DRINK_TOPPINGS,
    },
    {
        "id": 20, "cat": "เครื่องดื่ม", "name": "นมเย็น",
        "desc": "นมเย็นสีชมพูหวานกรุบ หอมมันนัวๆ ดื่มแล้วสดชื่นนน",
        "styles": {"ร้อน": 50, "เย็น": 55, "ปั่น": 60},
        "image": "นมเย็น.jpg", "bg": "#DCE7C8",
        "sugar": True, "toppings": DRINK_TOPPINGS,
    },
    {
        "id": 7, "cat": "เบเกอรี่", "name": "ครัวซองต์เนย",
        "desc": "อบใหม่ทุกเช้า กรอบนอกนุ่มใน",
        "price": 55, "image": "ครัวซอง.jpg", "bg": "#F1DCB8",
        "sugar": False, "toppings": BAKERY_TOPPINGS,
    },
    {
        "id": 8, "cat": "เบเกอรี่", "name": "บานอฟฟี่พาย",
        "desc": "กล้วย คาราเมล ครีมสด",
        "price": 85, "image": "บานอฟฟี่.jpg", "bg": "#F1DCB8",
        "sugar": False, "toppings": BAKERY_TOPPINGS,
    },
    {
        "id": 9, "cat": "เบเกอรี่", "name": "บราวนี่ช็อกโกแลต",
        "desc": "เข้มข้น หนึบหนับ",
        "price": 65, "image": "บราวนี่.jpg", "bg": "#E4CBB4",
        "sugar": False, "toppings": BAKERY_TOPPINGS,
    },
    {
        "id": 10, "cat": "เบเกอรี่", "name": "ทีรามิสุ",
        "desc": "หอมกาแฟมาก",
        "price": 60, "image": "Tiramisu.jpg", "bg": "#E4CBB4",
        "sugar": False, "toppings": BAKERY_TOPPINGS,
    },
    {
        "id": 11, "cat": "เบเกอรี่", "name": "โทสต์",
        "desc": "ขนมปังกรอบหวาน ไอติมน่าอีส",
        "price": 120, "image": "toast.jpg", "bg": "#E4CBB4",
        "sugar": False, "toppings": BAKERY_TOPPINGS,
    },
    {
        "id": 13, "cat": "เบเกอรี่", "name": "วอฟเฟิล",
        "desc": "อร่อยจัด ต้องลองนะ",
        "price": 20, "image": "waffles.jpg", "bg": "#E4CBB4",
        "sugar": False, "toppings": BAKERY_TOPPINGS,
    },
    {
        "id": 12, "cat": "เบเกอรี่", "name": "เค้กมะพร้าว",
        "desc": "หอมอร่อย มะพร้าวเน้นๆ",
          "price": 45, "image": "เค้กมะพร้าว.jpg", "bg": "#E4CBB4",
        "sugar": False, "toppings": BAKERY_TOPPINGS,
    },
    {
        "id": 14, "cat": "เบเกอรี่", "name": "เค้กสตอเบอรี่",
        "desc": "เปรี้ยวหวานลงตัว สตอเบอรี่แน่นๆ",
        "price": 45, "image": "เค้กสตอ.jpg", "bg": "#E4CBB4",
        "sugar": False, "toppings": BAKERY_TOPPINGS,
    },
    {
        "id": 15, "cat": "เบเกอรี่", "name": "เค้กส้ม",
        "desc": "เค้กส้มฉ่ำว้าว ได้กลิ่นส้มแท้ๆ หอมสดชื่น",
        "price": 45, "image": "เค้กส้ม.jpg", "bg": "#E4CBB4",
        "sugar": False, "toppings": BAKERY_TOPPINGS,
    },
    {
        "id": 16, "cat": "เบเกอรี่", "name": "เค้กหน้าไหม้",
        "desc": "เติมเต็มบ่ายวันหยุดด้วยเค้กหน้าไหม้โฮมเมด",
        "price": 45, "image": "ชีสเค้ดหน้าไหม้.jpg", "bg": "#E4CBB4",
        "sugar": False, "toppings": BAKERY_TOPPINGS,
    },

]

for _m in MENU:
    _m["display_price"] = min(_m["styles"].values()) if "styles" in _m else _m["price"]

CATEGORIES = ["ทั้งหมด"] + list(dict.fromkeys(m["cat"] for m in MENU))
MENU_BY_ID = {m["id"]: m for m in MENU}

# ===========================================================================
# ส่วนที่ 2: ที่เก็บข้อมูล (in-memory เดโมเท่านั้น — รีสตาร์ตแอปแล้วข้อมูลหาย)
# ===========================================================================
orders = []
order_seq = itertools.count(1001)

STATUSES = ["รอดำเนินการ", "กำลังทำ", "เสร็จแล้ว"]
NEXT_STATUS = {"รอดำเนินการ": "กำลังทำ", "กำลังทำ": "เสร็จแล้ว"}


def get_cart():
    return session.setdefault("cart", [])


def cart_total(cart):
    return sum(line["line_total"] for line in cart)


def line_opts_text(line):
    parts = []
    if line.get("style"):
        parts.append(line["style"])
    if line.get("sugar"):
        parts.append(line["sugar"])
    if line.get("ice"):
        parts.append(line["ice"])
    if line.get("toppings"):
        parts.append("เพิ่ม: " + ", ".join(line["toppings"]))
    return " · ".join(parts)
# ===========================================================================
# ส่วนที่ 3: CSS (เดิมอยู่ static/style.css) — ฝังเป็น string ในไฟล์เดียว
# ===========================================================================
STYLE_CSS = r"""
:root{
  --ink:#23291F;
  --cream:#F3EEDF;
  --cream-2:#EAE2CC;
  --forest:#3B5240;
  --forest-dark:#2A3C2E;
  --ochre:#C9971F;
  --clay:#A64B32;
  --white:#FFFFFF;
  --line: rgba(35,41,31,0.14);
}
*{box-sizing:border-box;}
html,body{margin:0;padding:0;}
body{
  background:var(--cream);
  color:var(--ink);
  font-family:'Inter','Noto Sans Thai',sans-serif;
  -webkit-font-smoothing:antialiased;
  min-height:100vh;
}
h1,h2,h3,.serif{
  font-family:'Fraunces','Noto Serif Thai',serif;
  font-weight:600;
  letter-spacing:-0.01em;
  margin:0;
}
::selection{background:var(--ochre); color:var(--ink);}

.topbar{ position:sticky; top:0; z-index:40; background:var(--cream); border-bottom:1px solid var(--line); }
.topbar-inner{ max-width:1100px; margin:0 auto; display:flex; align-items:center; justify-content:space-between; padding:16px 24px; gap:16px; }
.brand{display:flex; align-items:center; gap:10px;}
.brand-mark{ width:34px;height:34px;border-radius:50%; background:var(--forest); display:flex;align-items:center;justify-content:center; color:var(--cream); font-family:'Fraunces',serif; font-size:17px; flex:none; }
.brand-text .name{font-size:18px; font-family:'Fraunces','Noto Serif Thai',serif; font-weight:600;}
.brand-text .sub{font-size:11.5px; color:var(--ink); opacity:.55;}

.role-switch{ display:flex; background:var(--cream-2); border-radius:999px; padding:3px; border:1px solid var(--line); }
.role-switch a{
  border:none; background:transparent; padding:8px 16px; text-decoration:none;
  font-family:inherit; font-size:13.5px; font-weight:600; color:var(--ink);
  opacity:.55; cursor:pointer; border-radius:999px; transition:.18s; white-space:nowrap;
}
.role-switch a.active{background:var(--forest); color:var(--cream); opacity:1;}

.cart-btn{
  position:relative; border:1px solid var(--line); background:var(--white);
  border-radius:999px; padding:9px 16px 9px 14px; cursor:pointer;
  font-family:inherit; font-weight:600; font-size:13.5px; color:var(--ink);
  display:flex; align-items:center; gap:8px;
}
.cart-btn .dot{
  background:var(--clay); color:var(--white); font-size:11px; font-weight:700;
  min-width:18px; height:18px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  padding:0 4px;
}

main{max-width:1100px; margin:0 auto; padding:0 24px 80px;}

.hero{ padding:56px 0 40px; display:grid; grid-template-columns:1.3fr 1fr; gap:40px; align-items:end; border-bottom:1px solid var(--line); }
.hero h1{font-size:clamp(34px,5vw,52px); line-height:1.05;}
.hero p{margin-top:14px; font-size:15.5px; line-height:1.6; opacity:.75; max-width:46ch;}
.hero-stats{display:flex; gap:28px; padding-bottom:4px;}
.hero-stats div{border-left:2px solid var(--ochre); padding-left:12px;}
.hero-stats .num{font-family:'Fraunces',serif; font-size:26px;}
.hero-stats .lbl{font-size:12px; opacity:.6; margin-top:2px;}

.cat-tabs{ display:flex; gap:8px; overflow-x:auto; padding:24px 0 8px; scrollbar-width:none; }
.cat-tabs::-webkit-scrollbar{display:none;}
.cat-tabs a{
  border:1px solid var(--line); background:var(--white); color:var(--ink); text-decoration:none;
  padding:9px 18px; border-radius:999px; font-family:inherit; font-weight:600;
  font-size:13.5px; cursor:pointer; white-space:nowrap; transition:.15s; display:inline-block;
}
.cat-tabs a.active{background:var(--ink); color:var(--cream); border-color:var(--ink);}

.menu-grid{ display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:18px; padding:20px 0 10px; }
.item-card{ background:var(--white); border:1px solid var(--line); border-radius:6px; padding:16px; display:flex; flex-direction:column; gap:10px; }
.item-top{display:flex; gap:12px; align-items:flex-start;}
.item-emoji{ width:52px;height:52px;border-radius:50%;flex:none; display:flex;align-items:center;justify-content:center; font-size:24px; }
.item-img{ width:52px;height:52px;border-radius:50%;flex:none; object-fit:cover; border:1px solid var(--line); }
.item-name{font-family:'Fraunces','Noto Serif Thai',serif; font-size:17px; font-weight:600;}
.item-desc{font-size:12.5px; opacity:.6; line-height:1.5; margin-top:3px;}
.item-bottom{display:flex; align-items:center; justify-content:space-between; margin-top:auto;}
.item-price{font-weight:700; font-size:15px;}
.item-price .from-lbl{font-weight:600; font-size:11px; opacity:.55; display:block;}
.add-btn{ border:none; background:var(--forest); color:var(--cream); font-family:inherit; font-weight:600; font-size:13px; padding:8px 14px; border-radius:5px; cursor:pointer; }
.add-btn:active{transform:scale(.97);}
.in-cart-tag{font-size:11px; font-weight:700; color:var(--forest); background:var(--cream-2); border-radius:999px; padding:3px 10px; align-self:flex-start;}

.overlay{ position:fixed; inset:0; background:rgba(35,41,31,.35); z-index:60; opacity:0; pointer-events:none; transition:opacity .2s; }
.overlay.show{opacity:1; pointer-events:auto;}
.drawer{
  position:fixed; top:0; right:0; height:100%; width:min(420px,92vw);
  background:var(--cream); z-index:61; box-shadow:-8px 0 24px rgba(0,0,0,.12);
  transform:translateX(100%); transition:transform .25s ease; display:flex; flex-direction:column;
}
.drawer.show{transform:translateX(0);}
.drawer-head{ padding:20px 22px; border-bottom:1px solid var(--line); display:flex; align-items:center; justify-content:space-between; }
.drawer-head h3{font-size:19px;}
.close-x{background:none; border:none; font-size:20px; cursor:pointer; color:var(--ink); opacity:.6;}
.drawer-body{flex:1; overflow-y:auto; padding:18px 22px;}
.drawer-foot{padding:18px 22px; border-top:1px solid var(--line); background:var(--white);}

.cart-line{display:flex; gap:10px; padding:12px 0; border-bottom:1px solid var(--line); align-items:flex-start;}
.cart-line:last-child{border-bottom:none;}
.cart-line .ci-emoji{width:38px;height:38px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px;flex:none;}
.cart-line .ci-img{width:38px;height:38px;border-radius:50%;object-fit:cover;flex:none;border:1px solid var(--line);}
.cart-line-mid{flex:1;}
.cart-line-mid .n{font-weight:600; font-size:14px;}
.cart-line-mid .p{font-size:12.5px; opacity:.6; margin-top:2px;}
.cart-line-mid .opts{font-size:11.5px; opacity:.55; margin-top:3px; line-height:1.5;}
.cart-line-right{display:flex; flex-direction:column; align-items:flex-end; gap:6px;}
.remove-link{border:none; background:none; font-size:11.5px; color:var(--clay); cursor:pointer; text-decoration:underline; padding:0;}

.sum-row{display:flex; justify-content:space-between; font-size:13.5px; margin-bottom:6px;}
.sum-row.total{font-weight:700; font-size:16px; margin-top:10px; padding-top:10px; border-top:1px dashed var(--line);}
.primary-btn{
  width:100%; border:none; background:var(--forest); color:var(--cream); padding:13px; border-radius:6px;
  font-family:inherit; font-weight:700; font-size:14.5px; cursor:pointer; margin-top:12px;
}
.primary-btn:disabled{opacity:.4; cursor:not-allowed;}
.empty-cart{text-align:center; padding:50px 10px; opacity:.55; font-size:14px;}

.field{margin-bottom:12px;}
.field label{display:block; font-size:12px; font-weight:600; opacity:.7; margin-bottom:5px;}
.field input, .field select, .field textarea{
  width:100%; border:1px solid var(--line); background:var(--white); border-radius:5px;
  padding:10px 11px; font-family:inherit; font-size:13.5px; color:var(--ink);
}
.field textarea{resize:vertical; min-height:56px;}
.pill-choice{display:flex; gap:8px; flex-wrap:wrap;}
.pill-choice button{
  flex:1; min-width:80px; border:1px solid var(--line); background:var(--white); padding:9px; border-radius:5px;
  font-family:inherit; font-size:13px; font-weight:600; cursor:pointer;
}
.pill-choice button.active{background:var(--ink); color:var(--cream); border-color:var(--ink);}

.check-row{display:flex; align-items:center; justify-content:space-between; border:1px solid var(--line); background:var(--white); border-radius:5px; padding:10px 12px; margin-bottom:8px; cursor:pointer;}
.check-row.active{border-color:var(--forest); background:#EEF2EC;}
.check-row .cn{font-size:13.5px; font-weight:600; display:flex; align-items:center; gap:8px;}
.check-row .cp{font-size:12.5px; opacity:.65;}
.checkbox-dot{width:16px;height:16px;border-radius:4px;border:1.5px solid var(--line); flex:none; display:flex; align-items:center; justify-content:center; font-size:11px; color:var(--white);}
.check-row.active .checkbox-dot{background:var(--forest); border-color:var(--forest);}

.back-link{background:none; border:none; font-size:12.5px; color:var(--forest); font-weight:700; cursor:pointer; padding:0; margin-bottom:14px;}

.confirm-box{text-align:center; padding:20px 6px;}
.confirm-box .big{font-family:'Fraunces',serif; font-size:40px; color:var(--forest);}
.confirm-box .oid{font-size:22px; font-weight:700; margin:10px 0 4px; font-family:'Fraunces',serif;}
.confirm-box p{font-size:13px; opacity:.65; line-height:1.5;}

.qr-box{ text-align:center; border:1px solid var(--line); background:var(--white); border-radius:8px; padding:16px; margin-top:6px; }
.qr-box img{ width:180px; height:180px; image-rendering:pixelated; }
.qr-box .qr-note{ font-size:11.5px; opacity:.6; margin-top:8px; }

.modal-overlay{ position:fixed; inset:0; background:rgba(35,41,31,.4); z-index:70; display:none; align-items:center; justify-content:center; padding:20px; }
.modal-overlay.show{display:flex;}
.modal-box{ background:var(--cream); width:min(440px,100%); max-height:88vh; overflow-y:auto; border-radius:10px; box-shadow:0 20px 50px rgba(0,0,0,.25); }
.modal-head{padding:20px 22px 6px; display:flex; gap:14px; align-items:center;}
.modal-head .m-emoji{width:48px;height:48px;border-radius:50%; display:flex;align-items:center;justify-content:center; font-size:22px; flex:none;}
.modal-head .m-img{width:48px;height:48px;border-radius:50%; object-fit:cover; flex:none; border:1px solid var(--line);}
.modal-head .m-name{font-size:18px;}
.modal-head .m-price{font-size:12.5px; opacity:.6; margin-top:2px;}
.modal-body{padding:14px 22px 4px;}
.opt-group{margin-bottom:18px;}
.opt-group-label{font-size:12.5px; font-weight:700; opacity:.8; margin-bottom:8px;}
.stepper{display:flex; align-items:center; gap:14px;}
.stepper button{width:34px;height:34px;border-radius:50%; border:1px solid var(--line); background:var(--white); font-size:16px; cursor:pointer; font-family:inherit;}
.stepper span{font-weight:700; font-size:16px; min-width:20px; text-align:center;}
.modal-foot{padding:16px 22px 22px;}

.owner-head{padding:44px 0 20px; display:flex; align-items:flex-end; justify-content:space-between; flex-wrap:wrap; gap:16px; border-bottom:1px solid var(--line);}
.owner-head h1{font-size:32px;}
.stat-cards{display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin:26px 0 6px;}
.stat-card{background:var(--white); border:1px solid var(--line); border-radius:6px; padding:16px 18px;}
.stat-card .lbl{font-size:12px; opacity:.6; font-weight:600;}
.stat-card .val{font-family:'Fraunces',serif; font-size:28px; margin-top:6px;}

.board{display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-top:26px;}
.board-col{display:flex; flex-direction:column; gap:12px;}
.board-col-head{display:flex; align-items:center; gap:8px; font-weight:700; font-size:13.5px; padding-bottom:8px; border-bottom:2px solid var(--line);}
.board-col-head .count{background:var(--cream-2); border-radius:999px; padding:1px 9px; font-size:11.5px;}
.order-card{background:var(--white); border:1px solid var(--line); border-radius:6px; padding:14px;}
.order-card .oid{font-family:'Fraunces',serif; font-weight:600; font-size:15.5px;}
.order-card .meta{font-size:11.5px; opacity:.55; margin-top:2px;}
.order-card ul{list-style:none; margin:10px 0; padding:0; font-size:12.5px;}
.order-card li{padding:4px 0; border-bottom:1px dotted var(--line);}
.order-card li:last-child{border-bottom:none;}
.order-card li .li-top{display:flex; justify-content:space-between;}
.order-card li .li-opts{font-size:11px; opacity:.55; margin-top:2px;}
.order-card .oc-total{display:flex; justify-content:space-between; font-weight:700; font-size:13.5px; border-top:1px dashed var(--line); padding-top:8px; margin-top:6px;}
.order-card .oc-note{font-size:11.5px; opacity:.6; font-style:italic; margin:6px 0;}
.oc-actions{display:flex; gap:8px; margin-top:10px;}
.oc-actions button{
  flex:1; border:1px solid var(--line); background:var(--cream); padding:7px; border-radius:5px;
  font-family:inherit; font-size:11.5px; font-weight:700; cursor:pointer;
}
.oc-actions button.primary{background:var(--forest); color:var(--cream); border-color:var(--forest);}
.empty-col{opacity:.4; font-size:12.5px; text-align:center; padding:24px 8px; border:1px dashed var(--line); border-radius:6px;}

@media (max-width:760px){
  .hero{grid-template-columns:1fr;}
  .board{grid-template-columns:1fr;}
  .stat-cards{grid-template-columns:1fr;}
  .brand-text .sub{display:none;}
}
"""

# ===========================================================================
# ส่วนที่ 4: JavaScript (เดิมอยู่ static/customer.js และ static/owner.js)
# ===========================================================================
CUSTOMER_JS = r"""
const $ = (sel) => document.querySelector(sel);
const money = (n) => "฿" + Number(n).toLocaleString("th-TH");

const MENU_BY_ID = {};
window.MENU_DATA.forEach(m => MENU_BY_ID[m.id] = m);

let drawerMode = "cart";
let lastOrder = null;
let currentCart = { cart: [], total: 0, count: 0 };

let modalItem = null;
let modalStyle = null;
let modalSugar = null;
let modalIce = null;
let modalToppings = [];
let modalQty = 1;

async function apiGetCart(){
  const r = await fetch("/api/cart");
  return r.json();
}
async function apiAddToCart(payload){
  const r = await fetch("/api/cart/add", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload)});
  return r.json();
}
async function apiRemoveLine(uid){
  const r = await fetch("/api/cart/remove/"+uid, {method:"POST"});
  return r.json();
}
async function apiCheckout(payload){
  const r = await fetch("/api/checkout", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload)});
  return r.json();
}

function setCartCount(n){ $("#cartCount").textContent = n; }

function visualHTML(obj, cls){
  if(obj.image){
    return `<img class="${cls.img}" src="${window.STATIC_URL}images/${obj.image}" alt="${obj.name||''}">`;
  }
  return `<div class="${cls.emoji}" style="background:${obj.bg}">${obj.emoji||''}</div>`;
}

function iceAvailable(){
  if(modalItem.styles) return modalStyle === "เย็น";
  return !!modalItem.ice;
}

document.querySelectorAll(".add-btn").forEach(b=>{
  b.onclick = () => openCustomizeModal(parseInt(b.dataset.id));
});

function openCustomizeModal(itemId){
  modalItem = MENU_BY_ID[itemId];
  modalStyle = modalItem.styles ? Object.keys(modalItem.styles)[0] : null;
  modalSugar = modalItem.sugar ? window.SUGAR_OPTS[0] : null;
  modalIce = iceAvailable() ? window.ICE_OPTS[0] : null;
  modalToppings = [];
  modalQty = 1;
  renderModal();
  $("#modalOverlay").classList.add("show");
}
function closeModal(){ $("#modalOverlay").classList.remove("show"); }

function modalExtra(){
  return modalToppings.reduce((sum,name)=>{
    const t = modalItem.toppings.find(x=>x.name===name);
    return sum + (t?t.price:0);
  },0);
}
function modalBasePrice(){
  return modalItem.styles ? modalItem.styles[modalStyle] : modalItem.price;
}
function modalUnitPrice(){ return modalBasePrice() + modalExtra(); }

function renderModal(){
  const box = $("#modalBox");
  box.innerHTML = `
    <div class="modal-head">
      ${visualHTML(modalItem, {img:"m-img", emoji:"m-emoji"})}
      <div>
        <div class="m-name serif">${modalItem.name}</div>
        <div class="m-price">${money(modalItem.display_price)} เริ่มต้น</div>
      </div>
    </div>
    <div class="modal-body">
      ${modalItem.styles ? `
        <div class="opt-group">
          <div class="opt-group-label">รูปแบบ</div>
          <div class="pill-choice" id="styleChoice">
            ${Object.keys(modalItem.styles).map(s=>`<button data-v="${s}" class="${s===modalStyle?'active':''}">${s} · ${money(modalItem.styles[s])}</button>`).join("")}
          </div>
        </div>` : ``}
      ${modalItem.sugar ? `
        <div class="opt-group">
          <div class="opt-group-label">ระดับความหวาน</div>
          <div class="pill-choice" id="sugarChoice">
            ${window.SUGAR_OPTS.map(s=>`<button data-v="${s}" class="${s===modalSugar?'active':''}">${s}</button>`).join("")}
          </div>
        </div>` : ``}
      ${iceAvailable() ? `
        <div class="opt-group">
          <div class="opt-group-label">ระดับน้ำแข็ง</div>
          <div class="pill-choice" id="iceChoice">
            ${window.ICE_OPTS.map(s=>`<button data-v="${s}" class="${s===modalIce?'active':''}">${s}</button>`).join("")}
          </div>
        </div>` : ``}
      <div class="opt-group">
        <div class="opt-group-label">ท็อปปิ้งเสริม (เลือกได้หลายอย่าง)</div>
        <div id="toppingChoice">
          ${modalItem.toppings.map(t=>`
            <div class="check-row ${modalToppings.includes(t.name)?'active':''}" data-v="${t.name}">
              <div class="cn"><span class="checkbox-dot">${modalToppings.includes(t.name)?'✓':''}</span>${t.name}</div>
              <div class="cp">+${money(t.price)}</div>
            </div>`).join("")}
        </div>
      </div>
      <div class="opt-group">
        <div class="opt-group-label">จำนวน</div>
        <div class="stepper">
          <button id="mQtyDec">−</button>
          <span id="mQtyVal">${modalQty}</span>
          <button id="mQtyInc">+</button>
        </div>
      </div>
    </div>
    <div class="modal-foot">
      <div class="sum-row total"><span>ราคารวม</span><span id="mLineTotal">${money(modalUnitPrice()*modalQty)}</span></div>
      <button class="primary-btn" id="mAdd">ใส่ตะกร้า</button>
      <button class="back-link" style="margin-top:10px;" id="mCancel">ยกเลิก</button>
    </div>
  `;

  if(modalItem.styles){
    box.querySelectorAll("#styleChoice button").forEach(b=>{
      b.onclick = ()=>{
        modalStyle = b.dataset.v;
        modalIce = iceAvailable() ? (modalIce || window.ICE_OPTS[0]) : null;
        renderModal();
      };
    });
  }
  if(modalItem.sugar){
    box.querySelectorAll("#sugarChoice button").forEach(b=>{
      b.onclick = ()=>{ modalSugar=b.dataset.v; renderModal(); };
    });
  }
  if(iceAvailable()){
    box.querySelectorAll("#iceChoice button").forEach(b=>{
      b.onclick = ()=>{ modalIce=b.dataset.v; renderModal(); };
    });
  }
  box.querySelectorAll("#toppingChoice .check-row").forEach(row=>{
    row.onclick = ()=>{
      const v = row.dataset.v;
      if(modalToppings.includes(v)) modalToppings = modalToppings.filter(x=>x!==v);
      else modalToppings.push(v);
      renderModal();
    };
  });
  $("#mQtyDec").onclick = ()=>{ if(modalQty>1) modalQty--; renderModal(); };
  $("#mQtyInc").onclick = ()=>{ modalQty++; renderModal(); };
  $("#mCancel").onclick = closeModal;
  $("#mAdd").onclick = async ()=>{
    const res = await apiAddToCart({
      item_id: modalItem.id,
      qty: modalQty,
      style: modalStyle,
      sugar: modalSugar,
      ice: modalIce,
      toppings: modalToppings,
    });
    currentCart = res;
    setCartCount(res.count);
    closeModal();
    window.location.reload();
  };
}

function openDrawer(mode){
  drawerMode = mode || "cart";
  $("#overlay").classList.add("show");
  $("#drawer").classList.add("show");
  refreshAndRenderDrawer();
}
function closeDrawer(){
  $("#overlay").classList.remove("show");
  $("#drawer").classList.remove("show");
}

function lineOptsText(l){
  const parts = [];
  if(l.style) parts.push(l.style);
  if(l.sugar) parts.push(l.sugar);
  if(l.ice) parts.push(l.ice);
  if(l.toppings && l.toppings.length) parts.push("เพิ่ม: "+l.toppings.join(", "));
  return parts.join(" · ");
}

async function refreshAndRenderDrawer(){
  if(drawerMode === "cart"){
    currentCart = await apiGetCart();
    setCartCount(currentCart.count);
  }
  renderDrawer();
}

// อัปเดตรูป QR พร้อมเพย์ให้ตรงกับยอดที่ต้องชำระปัจจุบัน
function updateQrBox(){
  const box = $("#qrBox");
  if(!box) return;
  const paySelect = $("#ckPay");
  const isPromptpay = paySelect && paySelect.value === "พร้อมเพย์ / โอนเงิน";
  box.style.display = isPromptpay ? "block" : "none";
  if(isPromptpay){
    const img = $("#qrImg");
    img.src = `/api/qr?amount=${currentCart.total}&t=${Date.now()}`;
  }
}

function renderDrawer(){
  const body = $("#drawerBody");
  const foot = $("#drawerFoot");
  const title = $("#drawerTitle");

  if(drawerMode === "cart"){
    title.textContent = "ตะกร้าของคุณ";
    const lines = currentCart.cart;
    if(lines.length===0){
      body.innerHTML = `<div class="empty-cart">ยังไม่มีสินค้าในตะกร้า<br>เลือกเมนูที่ชอบแล้วปรับแต่งได้เลย</div>`;
      foot.style.display = "none";
    } else {
      body.innerHTML = lines.map(l=>{
        const optsTxt = lineOptsText(l);
        return `
        <div class="cart-line">
          ${visualHTML(l, {img:"ci-img", emoji:"ci-emoji"})}
          <div class="cart-line-mid">
            <div class="n">${l.name} × ${l.qty}</div>
            <div class="p">${money(l.unit_price)} / แก้ว</div>
            ${optsTxt ? `<div class="opts">${optsTxt}</div>` : ``}
          </div>
          <div class="cart-line-right">
            <div style="font-weight:700; font-size:14px;">${money(l.line_total)}</div>
            <button class="remove-link" data-uid="${l.uid}">นำออก</button>
          </div>
        </div>`;
      }).join("");
      body.querySelectorAll(".remove-link").forEach(b=>{
        b.onclick = async ()=>{
          currentCart = await apiRemoveLine(b.dataset.uid);
          setCartCount(currentCart.count);
          renderDrawer();
        };
      });

      foot.style.display = "block";
      foot.innerHTML = `
        <div class="sum-row"><span>ยอดรวมสินค้า</span><span>${money(currentCart.total)}</span></div>
        <div class="sum-row total"><span>ยอดที่ต้องชำระ</span><span>${money(currentCart.total)}</span></div>
        <button class="primary-btn" id="toCheckout">ไปหน้าชำระเงิน</button>
      `;
      $("#toCheckout").onclick = ()=>{ drawerMode="checkout"; renderDrawer(); };
    }
  }

  else if(drawerMode === "checkout"){
    title.textContent = "ข้อมูลการสั่งซื้อ";
    foot.style.display = "none";
    body.innerHTML = `
      <button class="back-link" id="backToCart">‹ กลับไปที่ตะกร้า</button>
      <div class="field">
        <label>ชื่อผู้สั่ง</label>
        <input id="ckName" placeholder="เช่น คุณใบเฟิร์น">
      </div>
      <div class="field">
        <label>เบอร์โทร</label>
        <input id="ckPhone" placeholder="08x-xxx-xxxx">
      </div>
      <div class="field">
        <label>รับสินค้าแบบไหน</label>
        <div class="pill-choice">
          <button data-v="รับที่ร้าน" class="active" id="ckPickup">รับที่ร้าน</button>
          <button data-v="เดลิเวอรี่" id="ckDelivery">เดลิเวอรี่</button>
        </div>
      </div>
      <div class="field">
        <label>ช่องทางชำระเงิน</label>
        <select id="ckPay">
          <option>เงินสดหน้าร้าน</option>
           <option>พร้อมเพย์ / โอนเงิน</option>
           <option>บัตรเครดิต/เดบิต</option>
        </select>
      </div>
      <div class="field" id="qrBox" style="display:none;">
        <div class="qr-box">
          <img id="qrImg" alt="พร้อมเพย์ QR">
          <div class="qr-note">สแกนจ่าย ${money(currentCart.total)} ผ่านแอปธนาคาร</div>
        </div>
      </div>
      <div class="field">
        <label>หมายเหตุถึงร้าน (ถ้ามี)</label>
        <textarea id="ckNote" placeholder="เช่น ขอถุงแยก, เผื่อหลอด 2 อัน"></textarea>
      </div>
      <div class="sum-row total"><span>ยอดที่ต้องชำระ</span><span>${money(currentCart.total)}</span></div>
    `;
    let fulfil = "รับที่ร้าน";
    $("#ckPickup").onclick = ()=>{ fulfil="รับที่ร้าน"; $("#ckPickup").classList.add("active"); $("#ckDelivery").classList.remove("active"); };
    $("#ckDelivery").onclick = ()=>{ fulfil="เดลิเวอรี่"; $("#ckDelivery").classList.add("active"); $("#ckPickup").classList.remove("active"); };
    $("#backToCart").onclick = ()=>{ drawerMode="cart"; refreshAndRenderDrawer(); };
    $("#ckPay").onchange = updateQrBox;
    updateQrBox();

    foot.style.display = "block";
    foot.innerHTML = `<button class="primary-btn" id="placeOrder">ยืนยันสั่งซื้อ</button>`;
    $("#placeOrder").onclick = async ()=>{
      const payload = {
        name: $("#ckName").value.trim(),
        phone: $("#ckPhone").value.trim(),
        fulfil,
        pay: $("#ckPay").value,
        note: $("#ckNote").value.trim(),
      };
      const res = await apiCheckout(payload);
      if(res.error){ alert(res.error); return; }
      lastOrder = res.order;
      setCartCount(0);
      drawerMode = "confirm";
      renderDrawer();
    };
  }

  else if(drawerMode === "confirm"){
    title.textContent = "สั่งซื้อสำเร็จ";
    foot.style.display = "block";
    body.innerHTML = `
      <div class="confirm-box">
        <div class="big">✓</div>
        <div class="oid">คำสั่งซื้อ #${lastOrder.id}</div>
        <p>ทางร้านได้รับออเดอร์ของคุณแล้ว<br>สถานะ: ${lastOrder.status} · ${lastOrder.fulfil}<br>ยอดชำระ ${money(lastOrder.total)}</p>
      </div>
    `;
    foot.innerHTML = `<button class="primary-btn" id="doneBtn">สั่งซื้อเพิ่ม</button>`;
    $("#doneBtn").onclick = ()=>{ closeDrawer(); window.location.reload(); };
  }
}

$("#openCart").onclick = ()=> openDrawer(drawerMode!=="cart" ? drawerMode : "cart");
$("#closeCart").onclick = closeDrawer;
$("#overlay").onclick = closeDrawer;
$("#modalOverlay").onclick = (e)=>{ if(e.target.id==="modalOverlay") closeModal(); };
"""

OWNER_JS = r"""
const money = (n) => "฿" + Number(n).toLocaleString("th-TH");
const NEXT_LABEL = { "รอดำเนินการ": "กำลังทำ", "กำลังทำ": "เสร็จแล้ว" };

async function fetchOrders(){
  const r = await fetch("/api/orders");
  return r.json();
}

function lineItemHTML(it){
  return `<li>
    <div class="li-top"><span>${it.name} ×${it.qty}</span><span>${money(it.line_total)}</span></div>
    ${it.opts ? `<div class="li-opts">${it.opts}</div>` : ``}
  </li>`;
}

function orderCardHTML(o){
  const nextLabel = NEXT_LABEL[o.status];
  return `
  <div class="order-card">
    <div class="oid">#${o.id} · ${o.name}</div>
    <div class="meta">${o.time} · ${o.fulfil} · ${o.pay}</div>
    <ul>${o.items.map(lineItemHTML).join("")}</ul>
    ${o.note ? `<div class="oc-note">หมายเหตุ: ${o.note}</div>` : ``}
    <div class="oc-total"><span>รวม</span><span>${money(o.total)}</span></div>
    <div class="oc-actions">
      ${nextLabel
        ? `<button class="primary" data-id="${o.id}" data-act="next">ทำเป็น "${nextLabel}"</button>`
        : `<button data-id="${o.id}" data-act="reopen">เปิดใหม่</button>`}
    </div>
  </div>`;
}

async function render(){
  const data = await fetchOrders();
  document.querySelector("#statSales").textContent = money(data.sales);
  document.querySelector("#statOrders").textContent = data.order_count;
  document.querySelector("#statPending").textContent = data.pending;

  window.STATUSES.forEach((st, idx)=>{
    const list = data.orders.filter(o=>o.status===st);
    document.querySelector("#cnt-"+idx).textContent = list.length;
    const col = document.querySelector("#col-"+idx);
    col.innerHTML = list.length
      ? list.map(orderCardHTML).join("")
      : `<div class="empty-col">ไม่มีออเดอร์</div>`;
  });

  document.querySelectorAll(".oc-actions button").forEach(b=>{
    b.onclick = async ()=>{
      await fetch(`/api/orders/${b.dataset.id}/advance`, {method:"POST"});
      render();
    };
  });
}

render();
setInterval(render, 4000);
"""

# ===========================================================================
# ส่วนที่ 5: HTML templates (เดิมอยู่ templates/*.html) — ฝังด้วย DictLoader
# ===========================================================================
BASE_HTML = """
<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{% block title %}ใบเฟิร์น คาเฟ่{% endblock %}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;1,9..144,500&family=Noto+Serif+Thai:wght@500;600;700&family=Inter:wght@400;500;600;700&family=Noto+Sans+Thai:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>""" + STYLE_CSS + """</style>
</head>
<body>
<div class="topbar">
  <div class="topbar-inner">
    <div class="brand">
      <div class="brand-mark">didy</div>
      <div class="brand-text">
        <div class="name">คาเฟ่ ชายแท้</div>
        <div class="sub">Baifern Coffee &amp; Bakery</div>
      </div>
    </div>
    <div class="role-switch">
      <a href="{{ url_for('index') }}" class="{{ 'active' if request.endpoint=='index' else '' }}">ลูกค้า</a>
      <a href="{{ url_for('owner') }}" class="{{ 'active' if request.endpoint=='owner' else '' }}">เจ้าของร้าน</a>
    </div>
    {% block cartbtn %}<div style="width:1px;"></div>{% endblock %}
  </div>
</div>
<main>
{% block content %}{% endblock %}
</main>
{% block extra %}{% endblock %}
{% block scripts %}{% endblock %}
</body>
</html>
"""

INDEX_HTML = """
{% extends "base.html" %}
{% block title %} สั่งเครื่องดื่ม{% endblock %}

{% block cartbtn %}
<button class="cart-btn" id="openCart">
  🛍 ตะกร้า <span class="dot" id="cartCount">{{ cart_count }}</span>
</button>
{% endblock %}

{% block content %}
<section class="hero">
  <div>
    <h1>กาแฟดี ๆ<br>จากมุมสงบของเมือง</h1>
    <p>คั่วเมล็ดเองทุกสัปดาห์ เลือกท็อปปิ้งเองได้ทุกแก้ว น้ำแข็งเย็นทุกก้อน</p>
  </div>
  <div class="hero-stats">
    <div><div class="num">08:00–18:00</div><div class="lbl">เปิดทุกวัน</div></div>
  </div>
</section>

<div id="statusContainer"></div>
<script>
let previousStatuses = {};
// ฟังก์ชันสร้างเสียง Beep ผ่าน Web Audio API (ไม่ต้องพึ่งไฟล์เสียงจากภายนอก)
function playBeepSound() {
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.type = "sine";
  osc.frequency.setValueAtTime(800, ctx.currentTime); // ความถี่ 800Hz
  gain.gain.setValueAtTime(0.5, ctx.currentTime);
  osc.start();
  osc.stop(ctx.currentTime + 0.35); // ดัง 0.35 วินาที
}
async function monitorOrders() {
  const currentTable = "{{ session.get('table', 'T1') }}";
  const res = await fetch(`/api/table/${currentTable}/status`);
  const data = await res.json();
  
  const container = document.getElementById("statusContainer");
  container.innerHTML = "";
  
  data.orders.forEach(order => {
    // ตรวจสอบว่าออเดอร์เพิ่งเปลี่ยนสถานะเป็น 'เสร็จแล้ว' หรือไม่
    if (previousStatuses[order.id] && previousStatuses[order.id] !== "เสร็จแล้ว" && order.status === "เสร็จแล้ว") {
      playBeepSound();
      alert(`🔔 ออเดอร์ #${order.id} ทำเสร็จแล้ว มารับได้เลย!`);
    }
    previousStatuses[order.id] = order.status;
    container.innerHTML += `
      <div style="padding:10px; border:1px solid #ddd; margin-bottom:8px; border-radius:6px;">
        <b>ออเดอร์ #${order.id}</b> - สถานะ: <span style="color:green;">${order.status}</span>
      </div>
    `;
  });
}
// ตรวจสอบสถานะทุกๆ 3 วินาที
setInterval(monitorOrders, 3000);
</script>

<div class="cat-tabs">
  {% for c in categories %}
  <a href="{{ url_for('index', cat=c) }}" class="{{ 'active' if c==active_cat else '' }}">{{ c }}</a>
  {% endfor %}
</div>

<div class="menu-grid">
  {% for m in items %}
  <div class="item-card">
    <div class="item-top">
      {% if m.image %}
      <img class="item-img" src="{{ url_for('static', filename='images/' + m.image) }}" alt="{{ m.name }}">
      {% else %}
      <div class="item-emoji" style="background:{{ m.bg }}">{{ m.emoji }}</div>
      {% endif %}
      <div>
        <div class="item-name">{{ m.name }}</div>
        <div class="item-desc">{{ m.desc }}</div>
      </div>
    </div>
    {% set n = in_cart_counts.get(m.id, 0) %}
    {% if n > 0 %}<div class="in-cart-tag">ในตะกร้า {{ n }} แก้ว/ชิ้น</div>{% endif %}
    <div class="item-bottom">
      <div class="item-price">
        {% if m.styles %}<span class="from-lbl">เริ่มต้น</span>{% endif %}฿{{ m.display_price }}
      </div>
      <button class="add-btn" data-id="{{ m.id }}">ปรับแต่ง &amp; เพิ่ม</button>
    </div>
  </div>
  {% endfor %}
</div>
{% endblock %}

{% block extra %}
<div class="overlay" id="overlay"></div>
<div class="drawer" id="drawer">
  <div class="drawer-head">
    <h3 id="drawerTitle">ตะกร้าของคุณ</h3>
    <button class="close-x" id="closeCart">✕</button>
  </div>
  <div class="drawer-body" id="drawerBody"></div>
  <div class="drawer-foot" id="drawerFoot" style="display:none;"></div>
</div>

<div class="modal-overlay" id="modalOverlay">
  <div class="modal-box" id="modalBox"></div>
</div>
{% endblock %}

{% block scripts %}
<script>
  window.MENU_DATA = {{ menu_json|tojson }};
  window.SUGAR_OPTS = {{ sugar_opts|tojson }};
  window.ICE_OPTS = {{ ice_opts|tojson }};
  window.STATIC_URL = "{{ url_for('static', filename='') }}";
</script>
<script>""" + CUSTOMER_JS + """</script>
{% endblock %}
"""

OWNER_HTML = """
{% extends "base.html" %}
{% block title %}ใบเฟิร์น คาเฟ่ — ออเดอร์วันนี้{% endblock %}

{% block content %}
<div class="owner-head">
  <h1>ออเดอร์วันนี้</h1>
</div>
<div class="stat-cards">
  <div class="stat-card"><div class="lbl">ยอดขายวันนี้</div><div class="val" id="statSales">฿0</div></div>
  <div class="stat-card"><div class="lbl">จำนวนออเดอร์</div><div class="val" id="statOrders">0</div></div>
  <div class="stat-card"><div class="lbl">กำลังดำเนินการ</div><div class="val" id="statPending">0</div></div>
</div>

<div class="board">
  {% for st in statuses %}
  <div class="board-col" data-status="{{ st }}">
    <div class="board-col-head">{{ st }} <span class="count" id="cnt-{{ loop.index0 }}">0</span></div>
    <div class="col-body" id="col-{{ loop.index0 }}"></div>
  </div>
  {% endfor %}
</div>
{% endblock %}

{% block scripts %}
<script>
  window.STATUSES = {{ statuses|tojson }};
</script>
<script>""" + OWNER_JS + """</script>
{% endblock %}
"""

app.jinja_loader = DictLoader({
    "base.html": BASE_HTML,
    "index.html": INDEX_HTML,
    "owner.html": OWNER_HTML,
})

# ===========================================================================
# ส่วนที่ 6: Routes — หน้าเว็บ
# ===========================================================================
@app.route("/")
def index():
    active_cat = request.args.get("cat", "ทั้งหมด")
    items = MENU if active_cat == "ทั้งหมด" else [m for m in MENU if m["cat"] == active_cat]
    cart = get_cart()
    in_cart_counts = {}
    for line in cart:
        in_cart_counts[line["item_id"]] = in_cart_counts.get(line["item_id"], 0) + line["qty"]
    return render_template(
        "index.html",
        categories=CATEGORIES,
        active_cat=active_cat,
        items=items,
        in_cart_counts=in_cart_counts,
        cart_count=sum(l["qty"] for l in cart),
        menu_json=MENU,
        sugar_opts=SUGAR_OPTS,
        ice_opts=ICE_OPTS,
    )


@app.route("/owner")
def owner():
    return render_template("owner.html", statuses=STATUSES)


# ===========================================================================
# ส่วนที่ 7: Routes — API ตะกร้า
# ===========================================================================
@app.route("/api/cart", methods=["GET"])
def api_get_cart():
    cart = get_cart()
    return jsonify(cart=cart, total=cart_total(cart), count=sum(l["qty"] for l in cart))


@app.route("/api/cart/add", methods=["POST"])
def api_add_to_cart():
    data = request.get_json(force=True)
    item = MENU_BY_ID.get(int(data.get("item_id", 0)))
    if not item:
        return jsonify(error="ไม่พบเมนูนี้"), 404

    qty = max(1, int(data.get("qty", 1)))

    if "styles" in item:
        style = data.get("style")
        if style not in item["styles"]:
            style = next(iter(item["styles"]))
        base_price = item["styles"][style]
        ice = data.get("ice") if style == "เย็น" else None
    else:
        style = None
        base_price = item["price"]
        ice = data.get("ice") if item.get("ice") else None

    sugar = data.get("sugar") if item.get("sugar") else None
    valid_topping_names = {t["name"] for t in item["toppings"]}
    toppings = [t for t in data.get("toppings", []) if t in valid_topping_names]

    extra = sum(t["price"] for t in item["toppings"] if t["name"] in toppings)
    unit_price = base_price + extra

    cart = get_cart()
    next_uid = (max((l["uid"] for l in cart), default=0)) + 1
    cart.append({
        "uid": next_uid,
        "item_id": item["id"],
        "name": item["name"],
        "emoji": item.get("emoji"),
        "image": item.get("image"),
        "bg": item["bg"],
        "qty": qty,
        "style": style,
        "sugar": sugar,
        "ice": ice,
        "toppings": toppings,
        "unit_price": unit_price,
        "line_total": unit_price * qty,
    })
    session["cart"] = cart
    session.modified = True
    return jsonify(cart=cart, total=cart_total(cart), count=sum(l["qty"] for l in cart))


@app.route("/api/cart/remove/<int:uid>", methods=["POST"])
def api_remove_from_cart(uid):
    cart = [l for l in get_cart() if l["uid"] != uid]
    session["cart"] = cart
    session.modified = True
    return jsonify(cart=cart, total=cart_total(cart), count=sum(l["qty"] for l in cart))


@app.route("/api/checkout", methods=["POST"])
def api_checkout():
    cart = get_cart()
    if not cart:
        return jsonify(error="ตะกร้าว่าง"), 400

    data = request.get_json(force=True)
    order = {
        "id": next(order_seq),
        "name": (data.get("name") or "").strip() or "ลูกค้าไม่ระบุชื่อ",
        "phone": (data.get("phone") or "").strip(),
        "fulfil": data.get("fulfil") or "รับที่ร้าน",
        "pay": data.get("pay") or "เงินสดหน้าร้าน",
        "note": (data.get("note") or "").strip(),
        "items": [
            {
                "name": l["name"],
                "qty": l["qty"],
                "unit_price": l["unit_price"],
                "line_total": l["line_total"],
                "opts": line_opts_text(l),
            }
            for l in cart
        ],
        "total": cart_total(cart),
        "status": STATUSES[0],
        "time": datetime.now().strftime("%H:%M"),
    }
    orders.insert(0, order)
    session["cart"] = []
    session.modified = True
    return jsonify(order=order)

@app.route("/api/table/<table_no>/status", methods=["GET"])
def get_table_order_status(table_no):
    table_orders = [o for o in orders if o.get("table") == table_no.upper()]
    return jsonify(orders=table_orders)


# ===========================================================================
# ส่วนที่ 7.5: Route — สร้างรูป QR พร้อมเพย์ตามยอดที่ต้องชำระ
# ===========================================================================
@app.route("/api/qr")
def api_qr():
    import qrcode
    import qrcode.image.svg
    import io

    try:
        amount = float(request.args.get("amount", "0"))
    except (TypeError, ValueError):
        amount = 0.0
    amount = max(0.0, amount)

    payload = build_promptpay_payload(PROMPTPAY_ID, amount)
    # ใช้ SvgPathImage เพราะเป็น pure-python ไม่ต้องพึ่ง Pillow เหมือน PNG
    img = qrcode.make(payload, image_factory=qrcode.image.svg.SvgPathImage, box_size=8, border=2)

    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)
    return Response(buf.getvalue(), mimetype="image/svg+xml")


# ===========================================================================
# ส่วนที่ 8: Routes — API เจ้าของร้าน
# ===========================================================================
@app.route("/api/orders", methods=["GET"])
def api_orders():
    sales = sum(o["total"] for o in orders)
    pending = sum(1 for o in orders if o["status"] != STATUSES[-1])
    return jsonify(orders=orders, sales=sales, order_count=len(orders), pending=pending)


@app.route("/api/orders/<int:order_id>/advance", methods=["POST"])
def api_advance_order(order_id):
    for o in orders:
        if o["id"] == order_id:
            o["status"] = NEXT_STATUS.get(o["status"], "กำลังทำ")
            break
    return jsonify(orders=orders)


if __name__ == "__main__":
    app.run(debug=True)