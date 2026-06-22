import asyncio
import os
import sqlite3
import random
import string
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
BOT_NAME = os.getenv("BOT_NAME", "MD Supplier Bot")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@bot_MD_global").strip()
USDT_BEP20_ADDRESS = os.getenv("USDT_BEP20_ADDRESS", "0xA2E0c2eC432953Dd2F832488a1EC061e6e761361").strip()
MIN_DEPOSIT_USDT = float(os.getenv("MIN_DEPOSIT_USDT", "50"))
MIN_ORDER_USDT = float(os.getenv("MIN_ORDER_USDT", "200"))
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "8573174269").replace(" ", "").split(",") if x.isdigit()}
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "md_supplier_bot.db"))
DB = str(Path(DATABASE_PATH) if Path(DATABASE_PATH).is_absolute() else BASE_DIR / DATABASE_PATH)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Add it in Railway Variables or .env file.")

bot = Bot(BOT_TOKEN, session=AiohttpSession())
dp = Dispatcher(storage=MemoryStorage())

CODE_PRICES = {"60": 0.79, "325": 3.81, "660": 7.81, "1800": 19.54, "3850": 39.07, "8100": 78.14}
ID_TOPUP_PRICES = {k: round(v * 0.98, 2) for k, v in CODE_PRICES.items()}
PRODUCT_LABELS = ["60", "325", "660", "1800", "3850", "8100"]

T = {
    "en": {
        "welcome": "Welcome to MD SUPPLIER BOT\n\nProfessional PUBG UC supply system.\nFast code delivery and PUBG ID top-up service.\n\nUse the buttons below to browse products, recharge your balance, check your orders, or contact support.\n\nChoose an option:", "choose_lang": "Choose language:", "lang_saved": "Language updated.", "main": "Main menu:",
        "shop": "🛒 SHOP", "topup_balance": "💳 Top Up Balance", "orders": "📦 My Orders", "cart": "🧾 Cart", "account": "👤 Account", "language": "🌐 Language", "support": "🛟 Support", "back": "🔙 Back",
        "pubg_uc": "🎮 PUBG UC", "codes": "🎟 Codes", "id_topup": "⚡ Top-up by ID", "select_product": "Select PUBG UC amount:",
        "confirm_code": "Confirm code order:\n\nProduct: {amount} UC\nPrice: {price:.2f} USDT", "buy_now": "✅ Buy Now", "add_cart": "🧾 Add to Cart",
        "insufficient": "Insufficient balance.\nRequired: {price:.2f} USDT\nYour balance: {balance:.2f} USDT",
        "order_done_code": "Order completed successfully.\n\nOrder ID: {order_id}\nProduct: PUBG UC {amount} UC\nCode:\n{code}\n\nStatus: Completed",
        "ask_player_id": "Enter your Game ID number", "ask_player_name": "Please send the PUBG account name:",
        "order_done_id": "Recharge submitted successfully.\n\nOrder ID: {order_id}\nPlayer ID: {player_id}\nPlayer Name: {player_name}\nPUBG UC Amount: {amount} UC\nDate & Time: {date}\nStatus: Completed\nProof: Recharge submitted successfully",
        "topup_msg": "USDT BEP20 Deposit Address:\n\n{wallet}\n\nAfter payment, please send the transaction hash to support for balance confirmation.",
        "copy_wallet": "📋 Copy Address", "wallet_copy": "{wallet}", "empty_cart": "Your cart is empty.", "cart_added": "Added to cart.",
        "account_msg": "Account\n\nUser ID: {uid}\nUsername: @{username}\nBalance: {balance:.2f} USDT",
        "no_orders": "No orders yet.", "banned": "Your account is blocked. Contact support.", "admin_only": "Admin only."
    },
    "ru": {
        "welcome": "Добро пожаловать в MD SUPPLIER BOT\n\nПрофессиональная система поставки PUBG UC.\nБыстрая выдача кодов и пополнение PUBG по ID.\n\nИспользуйте кнопки ниже, чтобы выбрать товар, пополнить баланс, проверить заказы или связаться с поддержкой.\n\nВыберите действие:", "choose_lang": "Выберите язык:", "lang_saved": "Язык обновлён.", "main": "Главное меню:",
        "shop": "🛒 SHOP", "topup_balance": "💳 Пополнить баланс", "orders": "📦 Мои заказы", "cart": "🧾 Корзина", "account": "👤 Аккаунт", "language": "🌐 Язык", "support": "🛟 Поддержка", "back": "🔙 Назад",
        "pubg_uc": "🎮 PUBG UC", "codes": "🎟 Коды", "id_topup": "⚡ Пополнение по ID", "select_product": "Выберите количество PUBG UC:",
        "confirm_code": "Подтвердите заказ кода:\n\nТовар: {amount} UC\nЦена: {price:.2f} USDT", "buy_now": "✅ Купить сейчас", "add_cart": "🧾 Добавить в корзину",
        "insufficient": "Недостаточно баланса.\nНужно: {price:.2f} USDT\nВаш баланс: {balance:.2f} USDT",
        "order_done_code": "Заказ успешно выполнен.\n\nOrder ID: {order_id}\nТовар: PUBG UC {amount} UC\nКод:\n{code}\n\nСтатус: Completed",
        "ask_player_id": "Введите ваш Game ID", "ask_player_name": "Отправьте никнейм аккаунта PUBG:",
        "order_done_id": "Пополнение успешно отправлено.\n\nOrder ID: {order_id}\nPlayer ID: {player_id}\nPlayer Name: {player_name}\nPUBG UC Amount: {amount} UC\nDate & Time: {date}\nStatus: Completed\nProof: Recharge submitted successfully",
        "topup_msg": "Адрес для депозита USDT BEP20:\n\n{wallet}\n\nПосле оплаты отправьте hash транзакции в поддержку для подтверждения баланса.",
        "copy_wallet": "📋 Скопировать адрес", "wallet_copy": "{wallet}", "empty_cart": "Корзина пуста.", "cart_added": "Добавлено в корзину.",
        "account_msg": "Аккаунт\n\nUser ID: {uid}\nUsername: @{username}\nBalance: {balance:.2f} USDT",
        "no_orders": "Заказов пока нет.", "banned": "Ваш аккаунт заблокирован. Свяжитесь с поддержкой.", "admin_only": "Только администратор."
    }
}

# Extra interface languages. Core logic stays the same; these dictionaries only change visible text.
T["ar"] = T["en"].copy()
T["ar"].update({
    "welcome": "مرحباً بك في MD SUPPLIER BOT\n\nنظام احترافي لتوريد PUBG UC.\nتسليم سريع للأكواد وخدمة الشحن عبر ID.\n\nاختر من الأزرار بالأسفل للمنتجات أو شحن الرصيد أو الطلبات أو الدعم.",
    "choose_lang": "اختر اللغة:", "lang_saved": "تم تحديث اللغة.", "main": "القائمة الرئيسية:",
    "shop": "🛒 SHOP", "topup_balance": "💳 شحن الرصيد", "orders": "📦 طلباتي", "cart": "🧾 السلة", "account": "👤 حسابي", "language": "🌐 اللغة", "support": "🛟 الدعم", "back": "🔙 رجوع",
    "pubg_uc": "🎮 PUBG UC", "codes": "🎟 أكواد", "id_topup": "⚡ شحن عبر ID", "select_product": "اختر كمية PUBG UC:",
    "confirm_code": "تأكيد طلب الكود:\n\nالمنتج: {amount} UC\nالسعر: {price:.2f} USDT", "buy_now": "✅ شراء الآن", "add_cart": "🧾 إضافة للسلة",
    "insufficient": "لا يوجد رصيد كافٍ.\nالمطلوب: {price:.2f} USDT\nرصيدك: {balance:.2f} USDT",
    "ask_player_id": "Enter your Game ID number", "ask_player_name": "يرجى إرسال اسم حساب PUBG:",
    "topup_msg": "عنوان الإيداع USDT BEP20:\n\n{wallet}\n\nبعد الدفع، يرجى إرسال Hash المعاملة للدعم لتأكيد الرصيد.",
    "copy_wallet": "📋 نسخ العنوان", "wallet_copy": "{wallet}", "empty_cart": "السلة فارغة.", "cart_added": "تمت الإضافة للسلة.",
    "account_msg": "الحساب\n\nUser ID: {uid}\nUsername: @{username}\nBalance: {balance:.2f} USDT",
    "no_orders": "لا توجد طلبات بعد.", "banned": "حسابك محظور. تواصل مع الدعم.", "admin_only": "للمشرف فقط."
})
T["my"] = T["en"].copy()
T["my"].update({
    "welcome": "Welcome to MD SUPPLIER BOT\n\nProfessional PUBG UC supply system.\nFast code delivery and PUBG ID top-up service.\n\nPlease choose an option below.",
    "choose_lang": "Choose language:", "lang_saved": "Language updated.", "main": "Main menu:",
    "ask_player_id": "Enter your Game ID number",
})

class OrderStates(StatesGroup):
    waiting_player_id = State()
    waiting_player_name = State()

def conn():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

def init_db():
    with conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, username TEXT DEFAULT '', first_name TEXT DEFAULT '', lang TEXT DEFAULT 'en', balance REAL DEFAULT 0, min_deposit REAL DEFAULT NULL, banned INTEGER DEFAULT 0, created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT DEFAULT '', order_type TEXT, amount TEXT, price REAL, player_id TEXT DEFAULT '', player_name TEXT DEFAULT '', code TEXT DEFAULT '', status TEXT DEFAULT 'completed', receipt_path TEXT DEFAULT '', created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS cart(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, order_type TEXT, amount TEXT, price REAL, created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS product_prices(order_type TEXT NOT NULL, amount TEXT NOT NULL, price REAL NOT NULL, PRIMARY KEY(order_type, amount))""")
        for amount, price in CODE_PRICES.items(): c.execute("INSERT OR IGNORE INTO product_prices(order_type, amount, price) VALUES(?,?,?)", ("code", amount, price))
        for amount, price in ID_TOPUP_PRICES.items(): c.execute("INSERT OR IGNORE INTO product_prices(order_type, amount, price) VALUES(?,?,?)", ("id", amount, price))
        c.commit()

def is_admin(uid): return uid in ADMIN_IDS

def ensure_user(obj):
    u = obj.from_user
    with conn() as c:
        c.execute("INSERT OR IGNORE INTO users(user_id, username, first_name, lang, balance, created_at) VALUES(?,?,?,?,?,?)", (u.id, u.username or "", u.first_name or "", "en", 0.0, datetime.utcnow().isoformat()))
        c.execute("UPDATE users SET username=?, first_name=? WHERE user_id=?", (u.username or "", u.first_name or "", u.id)); c.commit()

def get_user(uid):
    with conn() as c: return c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
def get_lang(uid):
    u = get_user(uid); return (u["lang"] if u and u["lang"] else "en")
def tr(uid, key, **kwargs): return T.get(get_lang(uid), T["en"])[key].format(**kwargs)
def user_min_deposit(uid):
    u = get_user(uid); return float(u["min_deposit"]) if u and u["min_deposit"] is not None else MIN_DEPOSIT_USDT
def user_min_order(uid):
    u = get_user(uid); return float(u["min_deposit"]) if u and u["min_deposit"] is not None else MIN_ORDER_USDT
def order_limit_message(uid, balance):
    minimum = user_min_order(uid)
    if balance <= 0:
        return "You do not have any balance. Please top up your balance first."
    return f"Your current balance is {balance:.2f} USDT. The minimum required balance for purchasing is {minimum:.2f} USDT."
def can_purchase(uid, price):
    balance = get_balance(uid)
    minimum = user_min_order(uid)
    if balance <= 0:
        return False, order_limit_message(uid, balance), balance
    if balance < minimum:
        return False, order_limit_message(uid, balance), balance
    if balance < price:
        return False, tr(uid, "insufficient", price=price, balance=balance), balance
    return True, "", balance
def is_banned(uid):
    u = get_user(uid); return bool(u and int(u["banned"] or 0) == 1)
async def block_if_banned(obj):
    ensure_user(obj); uid = obj.from_user.id
    if is_banned(uid):
        if isinstance(obj, CallbackQuery): await obj.answer(tr(uid, "banned"), show_alert=True)
        else: await obj.answer(tr(uid, "banned"))
        return True
    return False

def get_price(order_type, amount):
    with conn() as c: row = c.execute("SELECT price FROM product_prices WHERE order_type=? AND amount=?", (order_type, amount)).fetchone()
    if not row: raise ValueError("Price not found")
    return float(row["price"])
def set_price(order_type, amount, price):
    with conn() as c: c.execute("INSERT OR REPLACE INTO product_prices(order_type, amount, price) VALUES(?,?,?)", (order_type, amount, float(price))); c.commit()
def get_balance(uid):
    u = get_user(uid); return float(u["balance"]) if u else 0.0
def add_balance(uid, amount):
    with conn() as c:
        c.execute("INSERT OR IGNORE INTO users(user_id, username, first_name, lang, balance, created_at) VALUES(?,?,?,?,?,?)", (uid, "", "", "en", 0.0, datetime.utcnow().isoformat()))
        c.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (float(amount), uid)); c.commit()
def remove_balance(uid, amount):
    with conn() as c: c.execute("UPDATE users SET balance=MAX(balance-?,0) WHERE user_id=?", (float(amount), uid)); c.commit()
def set_balance(uid, amount):
    with conn() as c:
        c.execute("INSERT OR IGNORE INTO users(user_id, username, first_name, lang, balance, created_at) VALUES(?,?,?,?,?,?)", (uid, "", "", "en", 0.0, datetime.utcnow().isoformat()))
        c.execute("UPDATE users SET balance=? WHERE user_id=?", (float(amount), uid)); c.commit()
def deduct_balance(uid, price):
    with conn() as c: c.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (float(price), uid)); c.commit()
def generate_uc_code(): return random.choice(["jhhqQ", "dwPm5", "SZdRH", "XvRk9", "VpXt9"]) + "".join(random.choice(string.ascii_letters + string.digits) for _ in range(13))

def main_menu(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=tr(uid,"shop"), callback_data="menu:shop")],
        [InlineKeyboardButton(text=tr(uid,"topup_balance"), callback_data="menu:topup")],
        [InlineKeyboardButton(text=tr(uid,"orders"), callback_data="menu:orders"), InlineKeyboardButton(text=tr(uid,"cart"), callback_data="menu:cart")],
        [InlineKeyboardButton(text=tr(uid,"account"), callback_data="menu:account"), InlineKeyboardButton(text=tr(uid,"language"), callback_data="menu:language")],
        [InlineKeyboardButton(text=tr(uid,"support"), url=f"https://t.me/{SUPPORT_USERNAME.replace('@','')}")],
    ])
def back_menu(uid): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=tr(uid,"back"), callback_data="menu:main")]])
def shop_menu(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=tr(uid,"pubg_uc"), callback_data="shop:pubg")],
        [InlineKeyboardButton(text=tr(uid,"support"), url=f"https://t.me/{SUPPORT_USERNAME.replace('@','')}")],
        [InlineKeyboardButton(text=tr(uid,"back"), callback_data="menu:main")],
    ])
def pubg_menu(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=tr(uid,"codes"), callback_data="pubg:code")],
        [InlineKeyboardButton(text=tr(uid,"id_topup"), callback_data="pubg:id")],
        [InlineKeyboardButton(text=tr(uid,"back"), callback_data="menu:shop")],
    ])
def products_menu(uid, order_type):
    rows = [[InlineKeyboardButton(text=f"{amount} UC - {get_price(order_type, amount):.2f} USDT", callback_data=f"prod:{order_type}:{amount}")] for amount in PRODUCT_LABELS]
    rows.append([InlineKeyboardButton(text=tr(uid,"back"), callback_data="shop:pubg")]); return InlineKeyboardMarkup(inline_keyboard=rows)
def confirm_menu(uid, order_type, amount):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=tr(uid,"buy_now"), callback_data=f"buy:{order_type}:{amount}")],[InlineKeyboardButton(text=tr(uid,"add_cart"), callback_data=f"cartadd:{order_type}:{amount}")],[InlineKeyboardButton(text=tr(uid,"back"), callback_data=f"pubg:{order_type}")]])
def language_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="English", callback_data="lang:en"), InlineKeyboardButton(text="Русский", callback_data="lang:ru")],
        [InlineKeyboardButton(text="العربية", callback_data="lang:ar"), InlineKeyboardButton(text="Myanmar", callback_data="lang:my")],
    ])

def create_order(uid, order_type, amount, price, player_id="", player_name="", code="", receipt_path=""):
    u = get_user(uid)
    with conn() as c:
        cur = c.execute("INSERT INTO orders(user_id, username, order_type, amount, price, player_id, player_name, code, status, receipt_path, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (uid, u["username"] if u else "", order_type, amount, float(price), player_id, player_name, code, "completed", receipt_path, datetime.utcnow().isoformat()))
        c.commit(); return int(cur.lastrowid)
def get_font(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"]:
        if Path(p).exists(): return ImageFont.truetype(p, size)
    return ImageFont.load_default()
def generate_receipt(order_id, player_id, player_name, amount):
    d = BASE_DIR / "receipts"; d.mkdir(exist_ok=True)
    img = Image.new("RGB", (900, 1050), "#111827"); draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((45,45,855,1005), radius=34, fill="#1f2937", outline="#374151", width=3)
    draw.text((90,90), "MD STORE", font=get_font(54), fill="#ffffff")
    draw.text((90,155), "PUBG UC Recharge Receipt", font=get_font(34), fill="#93c5fd")
    rows = [("Order ID", str(order_id)), ("Date & Time", datetime.now().strftime("%Y/%m/%d %H:%M:%S")), ("Payment", "Balance"), ("Status", "Completed"), ("Product", "PUBG MOBILE"), ("PUBG UC Amount", f"{amount} UC"), ("Player ID", player_id), ("Player Name", player_name), ("Proof", "Recharge submitted successfully")]
    y=250
    for label, value in rows:
        draw.text((90,y), f"{label}:", font=get_font(30), fill="#d1d5db"); draw.text((380,y), value, font=get_font(30), fill="#ffffff"); y += 72
    draw.line((90,880,810,880), fill="#374151", width=2)
    draw.text((90,915), "This receipt was generated by MD STORE Bot.", font=get_font(24), fill="#9ca3af")
    draw.text((90,950), f"Support: {SUPPORT_USERNAME}", font=get_font(24), fill="#9ca3af")
    path = d / f"receipt_{order_id}.jpg"; img.save(path, quality=95); return str(path)

async def notify_admin_new_user(m: Message):
    if is_admin(m.from_user.id): return
    text = f"New user opened the bot\n\nUser ID: {m.from_user.id}\nUsername: @{m.from_user.username or '-'}\nName: {m.from_user.full_name or '-'}"
    for aid in ADMIN_IDS:
        try: await bot.send_message(aid, text)
        except Exception: pass

async def notify_admin_user_message(m: Message):
    if is_admin(m.from_user.id): return
    info = f"Message from user\n\nUser ID: {m.from_user.id}\nUsername: @{m.from_user.username or '-'}\nName: {m.from_user.full_name or '-'}\n\nReply with:\n/reply {m.from_user.id} YOUR_MESSAGE"
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, info)
            await bot.forward_message(aid, m.chat.id, m.message_id)
        except Exception: pass

@dp.message(CommandStart())
async def start(m: Message):
    ensure_user(m)
    if await block_if_banned(m): return
    await notify_admin_new_user(m)
    await m.answer(tr(m.from_user.id,"welcome"), reply_markup=main_menu(m.from_user.id))
@dp.message(Command("menu"))
async def menu_cmd(m: Message):
    ensure_user(m)
    if await block_if_banned(m): return
    await m.answer(tr(m.from_user.id,"main"), reply_markup=main_menu(m.from_user.id))
@dp.callback_query(F.data == "menu:main")
async def cb_main(c: CallbackQuery):
    if await block_if_banned(c): return
    await c.message.edit_text(tr(c.from_user.id,"main"), reply_markup=main_menu(c.from_user.id)); await c.answer()
@dp.callback_query(F.data == "menu:language")
async def cb_language(c: CallbackQuery):
    if await block_if_banned(c): return
    await c.message.edit_text(tr(c.from_user.id,"choose_lang"), reply_markup=language_menu()); await c.answer()
@dp.callback_query(F.data.startswith("lang:"))
async def cb_set_lang(c: CallbackQuery):
    ensure_user(c); lang = c.data.split(":")[1]
    with conn() as db: db.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, c.from_user.id)); db.commit()
    await c.message.edit_text(tr(c.from_user.id,"lang_saved"), reply_markup=main_menu(c.from_user.id)); await c.answer()
@dp.callback_query(F.data == "menu:shop")
async def cb_shop(c: CallbackQuery):
    if await block_if_banned(c): return
    await c.message.edit_text(tr(c.from_user.id,"shop"), reply_markup=shop_menu(c.from_user.id)); await c.answer()
@dp.callback_query(F.data == "shop:pubg")
async def cb_pubg(c: CallbackQuery):
    if await block_if_banned(c): return
    await c.message.edit_text(tr(c.from_user.id,"pubg_uc"), reply_markup=pubg_menu(c.from_user.id)); await c.answer()
@dp.callback_query(F.data.startswith("pubg:"))
async def cb_product_type(c: CallbackQuery):
    if await block_if_banned(c): return
    order_type = c.data.split(":")[1]
    await c.message.edit_text(tr(c.from_user.id,"select_product"), reply_markup=products_menu(c.from_user.id, order_type)); await c.answer()
@dp.callback_query(F.data.startswith("prod:"))
async def cb_product(c: CallbackQuery):
    if await block_if_banned(c): return
    _, order_type, amount = c.data.split(":"); price = get_price(order_type, amount)
    text = tr(c.from_user.id,"confirm_code", amount=amount, price=price) if order_type == "code" else f"{amount} UC - {price:.2f} USDT\n\n{tr(c.from_user.id,'ask_player_id')}"
    await c.message.edit_text(text, reply_markup=confirm_menu(c.from_user.id, order_type, amount)); await c.answer()
@dp.callback_query(F.data.startswith("cartadd:"))
async def cb_cart_add(c: CallbackQuery):
    if await block_if_banned(c): return
    _, order_type, amount = c.data.split(":"); price = get_price(order_type, amount)
    with conn() as db: db.execute("INSERT INTO cart(user_id, order_type, amount, price, created_at) VALUES(?,?,?,?,?)", (c.from_user.id, order_type, amount, price, datetime.utcnow().isoformat())); db.commit()
    await c.answer(tr(c.from_user.id,"cart_added"), show_alert=True)
@dp.callback_query(F.data.startswith("buy:code:"))
async def cb_buy_code(c: CallbackQuery):
    if await block_if_banned(c): return
    amount = c.data.split(":")[2]; price = get_price("code", amount); balance = get_balance(c.from_user.id)
    ok, msg, balance = can_purchase(c.from_user.id, price)
    if not ok: return await c.answer(msg, show_alert=True)
    deduct_balance(c.from_user.id, price); code = generate_uc_code(); order_id = create_order(c.from_user.id, "code", amount, price, code=code)
    await c.message.edit_text(tr(c.from_user.id,"order_done_code", order_id=order_id, amount=amount, code=code), reply_markup=main_menu(c.from_user.id)); await notify_admin_order(order_id); await c.answer()
@dp.callback_query(F.data.startswith("buy:id:"))
async def cb_buy_id_start(c: CallbackQuery, state: FSMContext):
    if await block_if_banned(c): return
    amount = c.data.split(":")[2]; await state.update_data(amount=amount); await state.set_state(OrderStates.waiting_player_id)
    await c.message.edit_text(tr(c.from_user.id,"ask_player_id"), reply_markup=back_menu(c.from_user.id)); await c.answer()
@dp.message(OrderStates.waiting_player_id)
async def st_player_id(m: Message, state: FSMContext):
    ensure_user(m)
    if await block_if_banned(m): return
    await notify_admin_user_message(m)
    player_id = (m.text or "").strip()
    if len(player_id) < 5: return await m.answer("Invalid Player ID.")
    data = await state.get_data(); amount = data.get("amount")
    if amount:
        price = get_price("id", amount)
        ok, msg, balance = can_purchase(m.from_user.id, price)
        if not ok:
            await state.clear(); return await m.answer(msg, reply_markup=main_menu(m.from_user.id))
    await state.update_data(player_id=player_id); await state.set_state(OrderStates.waiting_player_name); await m.answer(tr(m.from_user.id,"ask_player_name"))
@dp.message(OrderStates.waiting_player_name)
async def st_player_name(m: Message, state: FSMContext):
    ensure_user(m)
    if await block_if_banned(m): return
    await notify_admin_user_message(m)
    data = await state.get_data(); amount=data["amount"]; player_id=data["player_id"]; player_name=(m.text or "").strip(); price = get_price("id", amount); balance = get_balance(m.from_user.id)
    ok, msg, balance = can_purchase(m.from_user.id, price)
    if not ok:
        await state.clear(); return await m.answer(msg, reply_markup=main_menu(m.from_user.id))
    deduct_balance(m.from_user.id, price); order_id = create_order(m.from_user.id, "id", amount, price, player_id=player_id, player_name=player_name)
    receipt_path = generate_receipt(order_id, player_id, player_name, amount)
    with conn() as db: db.execute("UPDATE orders SET receipt_path=? WHERE id=?", (receipt_path, order_id)); db.commit()
    date = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    await m.answer(tr(m.from_user.id,"order_done_id", order_id=order_id, player_id=player_id, player_name=player_name, amount=amount, date=date))
    await m.answer_photo(FSInputFile(receipt_path), caption="Receipt"); await notify_admin_order(order_id); await state.clear()
@dp.callback_query(F.data == "menu:topup")
async def cb_topup(c: CallbackQuery):
    if await block_if_banned(c): return
    await c.message.edit_text(tr(c.from_user.id,"topup_msg", wallet=USDT_BEP20_ADDRESS, min_deposit=user_min_deposit(c.from_user.id)), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=tr(c.from_user.id,"copy_wallet"), callback_data="wallet:copy")],[InlineKeyboardButton(text=tr(c.from_user.id,"back"), callback_data="menu:main")]])); await c.answer()
@dp.callback_query(F.data == "wallet:copy")
async def cb_wallet(c: CallbackQuery):
    if await block_if_banned(c): return
    await c.message.answer(tr(c.from_user.id,"wallet_copy", wallet=USDT_BEP20_ADDRESS)); await c.answer()
@dp.callback_query(F.data == "menu:account")
async def cb_account(c: CallbackQuery):
    if await block_if_banned(c): return
    u = get_user(c.from_user.id)
    await c.message.edit_text(tr(c.from_user.id,"account_msg", uid=c.from_user.id, username=u["username"] or "-", balance=float(u["balance"]), min_deposit=user_min_deposit(c.from_user.id)), reply_markup=back_menu(c.from_user.id)); await c.answer()
@dp.callback_query(F.data == "menu:orders")
async def cb_orders(c: CallbackQuery):
    if await block_if_banned(c): return
    with conn() as db: rows = db.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10", (c.from_user.id,)).fetchall()
    text = tr(c.from_user.id,"no_orders") if not rows else "Orders\n\n" + "".join(f"#{r['id']} | {r['order_type']} | {r['amount']} UC | {float(r['price']):.2f} USDT | {r['status']}\n" for r in rows)
    await c.message.edit_text(text, reply_markup=back_menu(c.from_user.id)); await c.answer()
@dp.callback_query(F.data == "menu:cart")
async def cb_cart(c: CallbackQuery):
    if await block_if_banned(c): return
    with conn() as db: rows = db.execute("SELECT * FROM cart WHERE user_id=? ORDER BY id DESC LIMIT 20", (c.from_user.id,)).fetchall()
    if not rows: text = tr(c.from_user.id,"empty_cart")
    else:
        total = sum(float(r["price"]) for r in rows); text = "Cart\n\n" + "".join(f"{r['order_type']} | {r['amount']} UC | {float(r['price']):.2f} USDT\n" for r in rows) + f"\nTotal: {total:.2f} USDT"
    await c.message.edit_text(text, reply_markup=back_menu(c.from_user.id)); await c.answer()
async def notify_admin_order(order_id):
    with conn() as db: r = db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if not r: return
    text = f"New Order #{r['id']}\n\nUser ID: {r['user_id']}\nUsername: @{r['username'] or '-'}\nType: {r['order_type']}\nAmount: {r['amount']} UC\nPrice: {float(r['price']):.2f} USDT\nPlayer ID: {r['player_id'] or '-'}\nPlayer Name: {r['player_name'] or '-'}\nStatus: {r['status']}"
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, text)
            if r["receipt_path"] and Path(r["receipt_path"]).exists(): await bot.send_photo(aid, FSInputFile(r["receipt_path"]), caption=f"Receipt for order #{r['id']}")
        except Exception: pass

# Admin commands
@dp.message(Command("admin"))
async def cmd_admin(m: Message):
    ensure_user(m)
    if not is_admin(m.from_user.id): return await m.answer(tr(m.from_user.id,"admin_only"))
    await m.answer("Admin Panel\n\n/addbalance USER_ID AMOUNT\n/removebalance USER_ID AMOUNT\n/setbalance USER_ID AMOUNT\n/check USER_ID\n/orders\n/ban USER_ID\n/unban USER_ID\n/setmin USER_ID AMOUNT\n/resetmin USER_ID\n/prices\n/setprice TYPE AMOUNT PRICE\n/setpercent TYPE PERCENT\n/reply USER_ID MESSAGE\n/broadcast MESSAGE")
@dp.message(Command("addbalance"))
async def cmd_addbalance(m: Message):
    if not is_admin(m.from_user.id): return await m.answer("Admin only.")
    p=m.text.split()
    if len(p)!=3: return await m.answer("Usage: /addbalance USER_ID AMOUNT")
    try:
        uid, amount=int(p[1]), float(p[2]); add_balance(uid, amount); await m.answer(f"Balance added.\nUser ID: {uid}\nAmount: {amount:.2f} USDT")
        try: await bot.send_message(uid, f"Your balance has been topped up by {amount:.2f} USDT.")
        except Exception: pass
    except Exception: await m.answer("Invalid input.")
@dp.message(Command("removebalance"))
async def cmd_removebalance(m: Message):
    if not is_admin(m.from_user.id): return await m.answer("Admin only.")
    p=m.text.split()
    if len(p)!=3: return await m.answer("Usage: /removebalance USER_ID AMOUNT")
    try: uid, amount=int(p[1]), float(p[2]); remove_balance(uid, amount); await m.answer(f"Balance removed.\nUser ID: {uid}\nAmount: {amount:.2f} USDT")
    except Exception: await m.answer("Invalid input.")
@dp.message(Command("setbalance"))
async def cmd_setbalance(m: Message):
    if not is_admin(m.from_user.id): return await m.answer("Admin only.")
    p=m.text.split()
    if len(p)!=3: return await m.answer("Usage: /setbalance USER_ID AMOUNT")
    try: uid, amount=int(p[1]), float(p[2]); set_balance(uid, amount); await m.answer(f"Balance set.\nUser ID: {uid}\nBalance: {amount:.2f} USDT")
    except Exception: await m.answer("Invalid input.")
@dp.message(Command("check"))
async def cmd_check(m: Message):
    if not is_admin(m.from_user.id): return await m.answer("Admin only.")
    p=m.text.split()
    if len(p)!=2: return await m.answer("Usage: /check USER_ID")
    try:
        uid=int(p[1]); u=get_user(uid)
        if not u: return await m.answer("User not found.")
        await m.answer(f"User Info\n\nID: {uid}\nUsername: @{u['username'] or '-'}\nBalance: {float(u['balance']):.2f} USDT\nLanguage: {u['lang']}\nMinimum order: {user_min_order(uid):.2f} USDT\nBanned: {bool(u['banned'])}")
    except Exception: await m.answer("Invalid input.")
@dp.message(Command("orders"))
async def cmd_orders_admin(m: Message):
    if not is_admin(m.from_user.id): return await m.answer("Admin only.")
    with conn() as db: rows = db.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 25").fetchall()
    if not rows: return await m.answer("No orders.")
    await m.answer(("Last Orders\n\n" + "".join(f"#{r['id']} | {r['user_id']} | {r['order_type']} | {r['amount']} UC | {float(r['price']):.2f} USDT | {r['status']}\n" for r in rows))[:3900])
@dp.message(Command("ban"))
async def cmd_ban(m: Message):
    if not is_admin(m.from_user.id): return await m.answer("Admin only.")
    p=m.text.split()
    if len(p)!=2: return await m.answer("Usage: /ban USER_ID")
    try:
        uid=int(p[1])
        with conn() as db:
            db.execute("INSERT OR IGNORE INTO users(user_id, username, first_name, lang, balance, created_at) VALUES(?,?,?,?,?,?)", (uid,"","","en",0.0,datetime.utcnow().isoformat())); db.execute("UPDATE users SET banned=1 WHERE user_id=?", (uid,)); db.commit()
        await m.answer(f"User banned: {uid}")
    except Exception: await m.answer("Invalid input.")
@dp.message(Command("unban"))
async def cmd_unban(m: Message):
    if not is_admin(m.from_user.id): return await m.answer("Admin only.")
    p=m.text.split()
    if len(p)!=2: return await m.answer("Usage: /unban USER_ID")
    try:
        uid=int(p[1])
        with conn() as db: db.execute("UPDATE users SET banned=0 WHERE user_id=?", (uid,)); db.commit()
        await m.answer(f"User unbanned: {uid}")
    except Exception: await m.answer("Invalid input.")
@dp.message(Command("setmin"))
async def cmd_setmin(m: Message):
    if not is_admin(m.from_user.id): return await m.answer("Admin only.")
    p=m.text.split()
    if len(p)!=3: return await m.answer("Usage: /setmin USER_ID AMOUNT")
    try:
        uid, amount=int(p[1]), float(p[2])
        with conn() as db:
            db.execute("INSERT OR IGNORE INTO users(user_id, username, first_name, lang, balance, created_at) VALUES(?,?,?,?,?,?)", (uid,"","","en",0.0,datetime.utcnow().isoformat())); db.execute("UPDATE users SET min_deposit=? WHERE user_id=?", (amount, uid)); db.commit()
        await m.answer(f"Minimum order updated.\nUser ID: {uid}\nMinimum order: {amount:.2f} USDT")
    except Exception: await m.answer("Invalid input.")
@dp.message(Command("resetmin"))
async def cmd_resetmin(m: Message):
    if not is_admin(m.from_user.id): return await m.answer("Admin only.")
    p=m.text.split()
    if len(p)!=2: return await m.answer("Usage: /resetmin USER_ID")
    try:
        uid=int(p[1])
        with conn() as db: db.execute("UPDATE users SET min_deposit=NULL WHERE user_id=?", (uid,)); db.commit()
        await m.answer(f"Minimum order reset for {uid}.")
    except Exception: await m.answer("Invalid input.")
@dp.message(Command("prices"))
async def cmd_prices(m: Message):
    if not is_admin(m.from_user.id): return await m.answer("Admin only.")
    text="Prices\nUse: /setprice TYPE AMOUNT PRICE\nTYPE: code or id\n\nCodes:\n" + "".join(f"{a} UC - {get_price('code', a):.2f} USDT\n" for a in PRODUCT_LABELS) + "\nTop-up by ID:\n" + "".join(f"{a} UC - {get_price('id', a):.2f} USDT\n" for a in PRODUCT_LABELS)
    await m.answer(text)
@dp.message(Command("setprice"))
async def cmd_setprice(m: Message):
    if not is_admin(m.from_user.id): return await m.answer("Admin only.")
    p=m.text.split()
    if len(p)!=4: return await m.answer("Usage: /setprice TYPE AMOUNT PRICE\nExample: /setprice code 8100 78.14")
    try:
        order_type, amount, price=p[1], p[2], float(p[3])
        if order_type not in ("code","id") or amount not in PRODUCT_LABELS: return await m.answer("TYPE must be code/id and AMOUNT must be one of: 60, 325, 660, 1800, 3850, 8100")
        set_price(order_type, amount, price); await m.answer(f"Price updated.\nType: {order_type}\nAmount: {amount} UC\nPrice: {price:.2f} USDT")
    except Exception: await m.answer("Invalid input.")
@dp.message(Command("reply"))
async def cmd_reply(m: Message):
    if not is_admin(m.from_user.id): return await m.answer("Admin only.")
    parts = m.text.split(maxsplit=2)
    if len(parts) < 3: return await m.answer("Usage: /reply USER_ID MESSAGE")
    try:
        uid = int(parts[1]); msg = parts[2]
        await bot.send_message(uid, msg)
        await m.answer(f"Reply sent to {uid}.")
    except Exception as e:
        await m.answer(f"Failed to send reply: {e}")

@dp.message(Command("setpercent"))
async def cmd_setpercent(m: Message):
    if not is_admin(m.from_user.id): return await m.answer("Admin only.")
    p = m.text.split()
    if len(p) != 3: return await m.answer("Usage: /setpercent TYPE PERCENT\nTYPE: code or id\nExample: /setpercent id 75")
    try:
        order_type = p[1].lower(); percent = float(p[2])
        if order_type not in ("code", "id"):
            return await m.answer("TYPE must be code or id.")
        if percent <= 0 or percent > 200:
            return await m.answer("Percent must be between 0 and 200.")
        updated = []
        for amount in PRODUCT_LABELS:
            new_price = round(float(amount) * percent / 100, 2)
            set_price(order_type, amount, new_price)
            updated.append(f"{amount} UC - {new_price:.2f} USDT")
        await m.answer(f"All {order_type} prices updated to {percent:.2f}%.\n\n" + "\n".join(updated))
    except Exception:
        await m.answer("Invalid input.")

@dp.message(Command("broadcast"))
async def cmd_broadcast(m: Message):
    if not is_admin(m.from_user.id): return await m.answer("Admin only.")
    msg=m.text.replace("/broadcast", "", 1).strip()
    if not msg: return await m.answer("Usage: /broadcast MESSAGE")
    with conn() as db: rows = db.execute("SELECT user_id FROM users WHERE banned=0").fetchall()
    sent=0
    for r in rows:
        try: await bot.send_message(r["user_id"], msg); sent += 1
        except Exception: pass
    await m.answer(f"Broadcast sent to {sent} users.")
@dp.message()
async def catch_all_user_messages(m: Message):
    ensure_user(m)
    if await block_if_banned(m): return
    await notify_admin_user_message(m)

async def main():
    init_db(); print(f"{BOT_NAME} started"); await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
