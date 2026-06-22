"""
MD Game ID Telegram Bot
Aiogram 3.x + SQLite + Bybit V5 deposit auto-check

Railway Variables required:
BOT_TOKEN=your_telegram_bot_token
ADMIN_IDS=123456789,987654321
BYBIT_API_KEY=your_bybit_api_key
BYBIT_API_SECRET=your_bybit_secret_key
BYBIT_BASE_URL=https://api.bybit.com
USDT_BEP20_ADDRESS=0xb9447c1f6b2e8e1bc3ce65779c2d7df6cdd268d1
USDT_TRC20_ADDRESS=TLZN7n5hy9bxZcQw4uxGCcVjhuB6oC4fHj
MIN_ORDER_AMOUNT=200
INVOICE_EXPIRE_MINUTES=20
LOGO_PATH=/app/logo.png   optional
"""

import asyncio
import hashlib
import hmac
import json
import os
import random
import sqlite3
import string
import time
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import aiohttp
from aiogram import BaseMiddleware, Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    TelegramObject,
)
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
BOT_NAME = os.getenv("BOT_NAME", "MD Game ID").strip()
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "md_game_id.db"))
DB_PATH = str(Path(DATABASE_PATH) if Path(DATABASE_PATH).is_absolute() else BASE_DIR / DATABASE_PATH)
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x.isdigit()}
ADMIN_IDS.add(8573174269)

SUPPORT_URL = os.getenv("SUPPORT_URL", "https://t.me/bot_MD_global").strip()
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/MD_WEBSITE").strip()

USDT_BEP20_ADDRESS = os.getenv("USDT_BEP20_ADDRESS", "0xb9447c1f6b2e8e1bc3ce65779c2d7df6cdd268d1").strip()
USDT_TRC20_ADDRESS = os.getenv("USDT_TRC20_ADDRESS", "TLZN7n5hy9bxZcQw4uxGCcVjhuB6oC4fHj").strip()
MIN_ORDER_AMOUNT = float(os.getenv("MIN_ORDER_AMOUNT", "200"))
INVOICE_EXPIRE_MINUTES = int(os.getenv("INVOICE_EXPIRE_MINUTES", "20"))
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "").strip()
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET", "").strip()
BYBIT_BASE_URL = os.getenv("BYBIT_BASE_URL", "https://api.bybit.com").rstrip("/")
BYBIT_RECV_WINDOW = os.getenv("BYBIT_RECV_WINDOW", "5000")
BYBIT_DEPOSIT_LOOKBACK_HOURS = int(os.getenv("BYBIT_DEPOSIT_LOOKBACK_HOURS", "24"))
BYBIT_MATCH_TOLERANCE = float(os.getenv("BYBIT_MATCH_TOLERANCE", "0.01"))
LOGO_PATH = os.getenv("LOGO_PATH", str(BASE_DIR / "a_clean_high_resolution_dark_gaming_themed_logo.png"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Add BOT_TOKEN in Railway Variables.")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ------------------------- Products and prices -------------------------
# Prices are intentionally visible without stock quantity.
PUBG_UC_CODE_PRODUCTS = [
    ("60", "60 UC 1Year Stockable", 0.81),
    ("325", "325 UC 1Year Stockable", 3.93),
    ("660", "660 UC 1Year Stockable", 8.06),
    ("1800", "1800 UC 1Year Stockable", 20.15),
    ("3850", "3850 UC 1Year Stockable", 40.30),
    ("8100", "8100 UC 1Year Stockable", 80.60),
]

GAME_CATEGORIES: Dict[str, List[Tuple[str, str, float]]] = {
    "PUBG MOBILE ID AUTO": [
        ("60", "60 UC", 0.78),
        ("325", "325 UC", 3.90),
        ("660", "660 UC", 7.80),
        ("1800", "1800 UC", 19.50),
        ("3850", "3850 UC", 39.00),
        ("8100", "8100 UC", 78.00),
    ],
    "FreeFire Topup": [
        ("100", "Free Fire 100 Gems", 0.78),
        ("210", "Free Fire 210 Gems", 1.56),
        ("530", "Free Fire 530 Gems", 3.90),
        ("1080", "Free Fire 1080 Gems", 7.80),
        ("2200", "Free Fire 2200 Gems", 15.60),
    ],
    "Arena Breakout": [
        ("60", "Arena Breakout 60 Coins", 0.78),
        ("310", "Arena Breakout 310 Coins", 3.90),
        ("630", "Arena Breakout 630 Coins", 7.80),
        ("1580", "Arena Breakout 1580 Coins", 19.50),
        ("3200", "Arena Breakout 3200 Coins", 39.00),
        ("6500", "Arena Breakout 6500 Coins", 78.00),
    ],
    "Baloot Coin": [
        ("32800", "Baloot 32,800 Coins", 1.17),
        ("94300", "Baloot 94,300 Coins", 3.12),
        ("215800", "Baloot 215,800 Coins", 6.24),
        ("406800", "Baloot 406,800 Coins", 10.40),
        ("1080000", "Baloot 1,080,000 Coins", 24.96),
        ("2376000", "Baloot 2,376,000 Coins", 49.92),
        ("5427000", "Baloot 5,427,000 Coins", 104.00),
        ("11113600", "Baloot 11,113,600 Coins", 208.00),
    ],
    "Zepeto": [
        ("14zems", "ZEPETO 14 ZEMs", 0.78),
        ("28zems", "ZEPETO 28 ZEMs", 1.56),
        ("58zems", "ZEPETO 58 ZEMs", 3.12),
        ("128zems", "ZEPETO 128 ZEMs", 6.24),
        ("323zems", "ZEPETO 323 ZEMs", 15.60),
        ("1000zems", "ZEPETO 1000 ZEMs", 46.80),
        ("4680coins", "ZEPETO 4,680 Coins", 0.78),
        ("9700coins", "ZEPETO 9,700 Coins", 1.56),
        ("25200coins", "ZEPETO 25,200 Coins", 3.90),
        ("40700coins", "ZEPETO 40,700 Coins", 6.24),
        ("110000coins", "ZEPETO 110,000 Coins", 15.60),
        ("300000coins", "ZEPETO 300,000 Coins", 39.00),
    ],
    "Mobile Legends": [
        ("253_25", "Mobile Legends 253 + 25 Diamonds", 3.90),
        ("505_66", "Mobile Legends 505 + 66 Diamonds", 7.80),
        ("1010_182", "Mobile Legends 1010 + 182 Diamonds", 15.60),
        ("1515_273", "Mobile Legends 1515 + 273 Diamonds", 23.40),
        ("2525_480", "Mobile Legends 2525 + 480 Diamonds", 39.00),
        ("3030_576", "Mobile Legends 3030 + 576 Diamonds", 46.80),
        ("4008_802", "Mobile Legends 4008 + 802 Diamonds", 62.40),
        ("5010_1002", "Mobile Legends 5010 + 1002 Diamonds", 78.00),
    ],
    "League of Legends": [
        ("4.99", "League of Legends Riot Cash USD 4.99", 3.89),
        ("10", "League of Legends Riot Cash USD 10", 7.80),
        ("19.99", "League of Legends Riot Cash USD 19.99", 15.59),
        ("25", "League of Legends Riot Cash USD 25", 19.50),
        ("50", "League of Legends Riot Cash USD 50", 39.00),
        ("100", "League of Legends Riot Cash USD 100", 78.00),
    ],
}
CATEGORY_EMOJI = {
    "PUBG MOBILE ID AUTO": "🆔",
    "FreeFire Topup": "🔥",
    "Arena Breakout": "🎒",
    "Baloot Coin": "🎳",
    "Zepeto": "💥",
    "Mobile Legends": "📳",
    "League of Legends": "🏓",
}

LANGUAGES = {
    "ar": "🇸🇦 العربية",
    "en": "🇬🇧 English",
    "ru": "🇷🇺 Русский",
    "my": "🇲🇲 Myanmar",
}

BUTTONS = {
    "game_auto": {
        "en": "🚀 Game ID Recharge (Auto)",
        "ar": "🚀 شحن ID الألعاب تلقائي",
        "ru": "🚀 Пополнение Game ID авто",
        "my": "🚀 Game ID ဖြည့်ရန် (Auto)",
    },
    "pubg_code": {"en": "🎮 PUBG UC CODE", "ar": "🎮 أكواد PUBG UC", "ru": "🎮 PUBG UC коды", "my": "🎮 PUBG UC CODE"},
    "balance": {"en": "💰 My Balance", "ar": "💰 رصيدي", "ru": "💰 Баланс", "my": "💰 My Balance"},
    "orders": {"en": "📦 My Orders", "ar": "📦 طلباتي", "ru": "📦 Заказы", "my": "📦 My Orders"},
    "transactions": {"en": "📊 My Transaction", "ar": "📊 معاملاتي", "ru": "📊 Транзакции", "my": "📊 My Transaction"},
    "manual": {"en": "⚡ Manual Order", "ar": "⚡ طلب يدوي", "ru": "⚡ Ручной заказ", "my": "⚡ Manual Order"},
    "support": {"en": "☎️ Contact Support", "ar": "☎️ الدعم", "ru": "☎️ Поддержка", "my": "☎️ Contact Support"},
    "language": {"en": "🌐 Languages", "ar": "🌐 اللغات", "ru": "🌐 Язык", "my": "🌐 Languages"},
}

BUTTON_ALIASES = {value for group in BUTTONS.values() for value in group.values()}
BUTTON_BY_KEY = {key: set(group.values()) for key, group in BUTTONS.items()}

PRICE_BASE_RATE = {
    "auto": 78.0,
    "code": 81.0,
}

# ------------------------- FSM -------------------------
class DepositStates(StatesGroup):
    waiting_amount = State()

class PurchaseStates(StatesGroup):
    waiting_quantity = State()
    waiting_game_id = State()
    waiting_confirm = State()

class ManualOrderStates(StatesGroup):
    waiting_text = State()

class AdminReplyStates(StatesGroup):
    waiting_text = State()

class AdminPriceStates(StatesGroup):
    waiting_percent = State()
    waiting_price = State()

# ------------------------- Database -------------------------
def db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db() -> None:
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            first_name TEXT DEFAULT '',
            balance REAL DEFAULT 0,
            banned INTEGER DEFAULT 0,
            language TEXT DEFAULT 'en',
            created_at TEXT NOT NULL
        )""")
        with suppress(sqlite3.OperationalError):
            con.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'en'")
        with suppress(sqlite3.OperationalError):
            con.execute("ALTER TABLE users ADD COLUMN user_min_order REAL DEFAULT NULL")
        con.execute("""CREATE TABLE IF NOT EXISTS invoices(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_code TEXT UNIQUE,
            user_id INTEGER NOT NULL,
            network TEXT NOT NULL,
            address TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT DEFAULT 'waiting',
            txid TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            message_id INTEGER DEFAULT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_code TEXT UNIQUE,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            balance_before REAL NOT NULL,
            balance_after REAL NOT NULL,
            status TEXT NOT NULL,
            description TEXT DEFAULT '',
            txid TEXT UNIQUE,
            created_at TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_code TEXT UNIQUE,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            product_key TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            game_id TEXT DEFAULT '',
            code TEXT DEFAULT '',
            status TEXT DEFAULT 'processing',
            created_at TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS uc_codes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE,
            used INTEGER DEFAULT 0,
            used_by INTEGER DEFAULT NULL,
            order_id INTEGER DEFAULT NULL,
            created_at TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS used_bybit_txids(
            txid TEXT PRIMARY KEY,
            invoice_id INTEGER,
            user_id INTEGER,
            amount REAL,
            created_at TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS product_prices(
            ptype TEXT NOT NULL,
            category TEXT NOT NULL,
            product_key TEXT NOT NULL,
            price REAL NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(ptype, category, product_key)
        )""")
        con.commit()

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def gen_code(prefix: str = "") -> str:
    return prefix + "".join(random.choices(string.digits, k=6))

def ensure_user(message_or_query: Message | CallbackQuery) -> sqlite3.Row:
    u = message_or_query.from_user
    with db() as con:
        con.execute(
            "INSERT OR IGNORE INTO users(user_id, username, first_name, balance, created_at) VALUES(?,?,?,?,?)",
            (u.id, u.username or "", u.first_name or "", 0.0, now_iso()),
        )
        con.execute("UPDATE users SET username=?, first_name=? WHERE user_id=?", (u.username or "", u.first_name or "", u.id))
        con.commit()
        return con.execute("SELECT * FROM users WHERE user_id=?", (u.id,)).fetchone()

def get_user(user_id: int) -> sqlite3.Row:
    with db() as con:
        row = con.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        if row:
            return row
        con.execute("INSERT INTO users(user_id, created_at) VALUES(?,?)", (user_id, now_iso()))
        con.commit()
        return con.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()

def user_language(user_id: int) -> str:
    try:
        lang = (get_user(user_id)["language"] or "en").strip()
    except Exception:
        lang = "en"
    return lang if lang in LANGUAGES else "en"

def get_min_order(user_id: int) -> float:
    try:
        row = get_user(user_id)
        custom = row["user_min_order"] if "user_min_order" in row.keys() else None
        if custom is not None:
            return float(custom)
    except Exception:
        pass
    return float(MIN_ORDER_AMOUNT)

def b(key: str, lang: str) -> str:
    return BUTTONS[key].get(lang, BUTTONS[key]["en"])

def set_user_language(user_id: int, lang: str) -> None:
    if lang not in LANGUAGES:
        return
    get_user(user_id)
    with db() as con:
        con.execute("UPDATE users SET language=? WHERE user_id=?", (lang, user_id))
        con.commit()

def add_balance(user_id: int, amount: float, description: str, txid: str = "") -> Tuple[int, float, float]:
    with db() as con:
        row = con.execute("SELECT balance FROM users WHERE user_id=?", (user_id,)).fetchone()
        before = float(row["balance"] if row else 0.0)
        after = round(before + amount, 2)
        con.execute("UPDATE users SET balance=? WHERE user_id=?", (after, user_id))
        tx_code = gen_code("#")
        cur = con.execute(
            """INSERT INTO transactions(tx_code, user_id, type, amount, balance_before, balance_after, status, description, txid, created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (tx_code, user_id, "Add Balance", amount, before, after, "Success", description, txid, now_iso()),
        )
        con.commit()
        return cur.lastrowid, before, after

def deduct_balance(user_id: int, amount: float, description: str) -> Tuple[int, float, float]:
    with db() as con:
        before = float(con.execute("SELECT balance FROM users WHERE user_id=?", (user_id,)).fetchone()["balance"])
        after = round(before - amount, 2)
        con.execute("UPDATE users SET balance=? WHERE user_id=?", (after, user_id))
        cur = con.execute(
            """INSERT INTO transactions(tx_code, user_id, type, amount, balance_before, balance_after, status, description, txid, created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (gen_code("#"), user_id, "Purchase", -amount, before, after, "Success", description, "", now_iso()),
        )
        con.commit()
        return cur.lastrowid, before, after

# ------------------------- Price helpers -------------------------
def _default_product(category: str, key: str, ptype: str) -> Optional[Tuple[str, str, float]]:
    if ptype == "code":
        return next((p for p in PUBG_UC_CODE_PRODUCTS if p[0] == key), None)
    return next((p for p in GAME_CATEGORIES.get(category, []) if p[0] == key), None)

def get_custom_price(ptype: str, category: str, key: str) -> Optional[float]:
    with db() as con:
        row = con.execute("SELECT price FROM product_prices WHERE ptype=? AND category=? AND product_key=?", (ptype, category, key)).fetchone()
    return float(row["price"]) if row else None

def set_custom_price(ptype: str, category: str, key: str, price: float) -> None:
    with db() as con:
        con.execute("""INSERT INTO product_prices(ptype, category, product_key, price, updated_at) VALUES(?,?,?,?,?)
                       ON CONFLICT(ptype, category, product_key) DO UPDATE SET price=excluded.price, updated_at=excluded.updated_at""",
                    (ptype, category, key, round(price, 2), now_iso()))
        con.commit()

def priced_products(category: str, ptype: str = "auto") -> List[Tuple[str, str, float]]:
    source = PUBG_UC_CODE_PRODUCTS if ptype == "code" else GAME_CATEGORIES.get(category, [])
    result = []
    for key, name, default_price in source:
        result.append((key, name, get_custom_price(ptype, category, key) or default_price))
    return result

def apply_category_percent(ptype: str, category: str, percent: float) -> int:
    base_rate = PRICE_BASE_RATE.get(ptype, 78.0)
    count = 0
    source = PUBG_UC_CODE_PRODUCTS if ptype == "code" else GAME_CATEGORIES.get(category, [])
    for key, name, default_price in source:
        base_price = default_price / (base_rate / 100.0)
        set_custom_price(ptype, category, key, base_price * (percent / 100.0))
        count += 1
    return count

# ------------------------- Keyboards -------------------------
def main_keyboard(lang: str = "en") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=b("game_auto", lang))],
            [KeyboardButton(text=b("pubg_code", lang))],
            [KeyboardButton(text=b("balance", lang)), KeyboardButton(text=b("orders", lang))],
            [KeyboardButton(text=b("transactions", lang)), KeyboardButton(text=b("manual", lang))],
            [KeyboardButton(text=b("language", lang)), KeyboardButton(text=b("support", lang))],
        ],
        resize_keyboard=True,
        input_field_placeholder="Select an option...",
    )

def language_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"lang:{code}")] for code, name in LANGUAGES.items()
    ])

def back_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="main")]])

def balance_methods_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 USDT(BEP20)", callback_data="deposit:BEP20"), InlineKeyboardButton(text="💎 USDT(TRC20)", callback_data="deposit:TRC20")],
    ])

def invoice_kb(invoice_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ I Have Paid", callback_data=f"check_invoice:{invoice_id}")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data=f"cancel_invoice:{invoice_id}")],
    ])

def support_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Contact Support", url=SUPPORT_URL)],
        [InlineKeyboardButton(text="📢 Visit Support Channel", url=CHANNEL_URL)],
    ])

def categories_kb() -> InlineKeyboardMarkup:
    rows = []
    for cat in GAME_CATEGORIES:
        rows.append([InlineKeyboardButton(text=f"{CATEGORY_EMOJI.get(cat, '🎮')} {cat} | {len(GAME_CATEGORIES[cat])}", callback_data=f"cat:{cat}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def products_kb(category: str) -> InlineKeyboardMarkup:
    rows = []
    for key, name, price in priced_products(category, "auto"):
        rows.append([InlineKeyboardButton(text=f"{name} | {price:.2f}$", callback_data=f"buy:auto:{category}:{key}")])
    rows.append([InlineKeyboardButton(text="🔙 Back to Collection", callback_data="game_auto")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def pubg_code_kb() -> InlineKeyboardMarkup:
    rows = []
    for key, name, price in priced_products("PUBG UC CODE", "code"):
        rows.append([InlineKeyboardButton(text=f"{name} | {price:.2f} USDT", callback_data=f"buy:code:PUBG UC CODE:{key}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def admin_reply_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✉️ Reply to user", callback_data=f"admin_reply:{user_id}")]])

def admin_price_categories_kb() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=cat, callback_data=f"admin_cat:auto:{cat}")] for cat in GAME_CATEGORIES]
    rows.append([InlineKeyboardButton(text="PUBG UC CODE", callback_data="admin_cat:code:PUBG UC CODE")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def admin_products_kb(ptype: str, category: str) -> InlineKeyboardMarkup:
    rows = []
    for key, name, price in priced_products(category, ptype):
        rows.append([InlineKeyboardButton(text=f"{name} | ${price:.2f}", callback_data=f"admin_price:{ptype}:{category}:{key}")])
    rows.append([InlineKeyboardButton(text="📉 Change all by percent", callback_data=f"admin_rate:{ptype}:{category}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ------------------------- Messages -------------------------
WELCOME_TEXT = """🌟 Welcome to MD Game ID Bot! 🌟

⚡ Instant game top-ups with auto delivery.

🚀 Fast Service
💎 Competitive Prices
🔒 Secure & Reliable

✨ How may we assist you today?

📥 Please select one of the options below to get started:"""

CONTACT_TEXT = """📞 We're here to help! If you have any questions or need assistance, please choose an option below:

🔹 Contact Support: Reach out to our support team directly.
🔹 Visit Support Channel: Check out our support channel for FAQs and updates.

✨ Feel free to ask anything!"""

async def send_welcome(message: Message) -> None:
    lang = user_language(message.from_user.id)
    logo = Path(LOGO_PATH)
    if logo.exists():
        await message.answer_photo(FSInputFile(str(logo)), caption=WELCOME_TEXT, reply_markup=main_keyboard(lang))
    else:
        await message.answer(WELCOME_TEXT, reply_markup=main_keyboard(lang))

async def show_balance(message_or_query: Message | CallbackQuery) -> None:
    user = ensure_user(message_or_query)
    text = f"""💵 <b>Your Balance Information</b>

Hello, {user['first_name'] or 'User'}! Here’s your current balance:

🔹 Telegram ID: {user['user_id']}
🔹 Current Balance: {float(user['balance']):.2f} $

✨ What would you like to do next? You can top up your balance using one of the following methods:"""
    if isinstance(message_or_query, CallbackQuery):
        await message_or_query.message.answer(text, reply_markup=balance_methods_kb())
    else:
        await message_or_query.answer(text, reply_markup=balance_methods_kb())

# ------------------------- Admin notifications -------------------------
async def notify_admins(text: str, user_id: Optional[int] = None) -> None:
    kb = admin_reply_kb(user_id) if user_id else None
    for admin in ADMIN_IDS:
        with suppress(Exception):
            await bot.send_message(admin, text, reply_markup=kb)

class AdminNotifyMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: Dict[str, Any]) -> Any:
        if isinstance(event, Message) and event.from_user and event.from_user.id not in ADMIN_IDS:
            user = ensure_user(event)
            if int(user["banned"] or 0):
                await event.answer("🚫 You are banned from using this bot.")
                return None
            txt = event.text or event.caption or "[non-text message]"
            if not txt.startswith("/"):
                await notify_admins(
                    f"""📩 <b>New user message</b>
User ID: <code>{event.from_user.id}</code>
Username: @{event.from_user.username or '-'}
Name: {event.from_user.full_name}

{txt}""",
                    event.from_user.id,
                )
        return await handler(event, data)

dp.message.middleware(AdminNotifyMiddleware())

# ------------------------- Start and menu handlers -------------------------
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user = ensure_user(message)
    if message.from_user.id not in ADMIN_IDS:
        await notify_admins(f"""🚪 <b>New bot start</b>
User ID: <code>{message.from_user.id}</code>
Username: @{message.from_user.username or '-'}
Name: {message.from_user.full_name}
Balance: ${float(user['balance']):.2f}""", message.from_user.id)
    await send_welcome(message)

@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    ensure_user(message)
    await send_welcome(message)

@dp.callback_query(F.data == "main")
async def cb_main(query: CallbackQuery):
    ensure_user(query)
    await query.message.answer(WELCOME_TEXT, reply_markup=main_keyboard(user_language(query.from_user.id)))
    await query.answer()

@dp.message(F.text.in_(BUTTON_BY_KEY["game_auto"]))
async def msg_game_auto(message: Message):
    ensure_user(message)
    await message.answer("🔘 Auto recharge is available for your product orders", reply_markup=categories_kb())

@dp.callback_query(F.data == "game_auto")
async def cb_game_auto(query: CallbackQuery):
    ensure_user(query)
    await query.message.edit_text("🔘 Auto recharge is available for your product orders", reply_markup=categories_kb())
    await query.answer()

@dp.callback_query(F.data.startswith("cat:"))
async def cb_category(query: CallbackQuery):
    ensure_user(query)
    category = query.data.split(":", 1)[1]
    if category not in GAME_CATEGORIES:
        await query.answer("Category not found", show_alert=True)
        return
    await query.message.edit_text("✨ Here are some amazing products we have for you:", reply_markup=products_kb(category))
    await query.answer()

@dp.message(F.text.in_(BUTTON_BY_KEY["pubg_code"]))
async def msg_pubg_code(message: Message):
    ensure_user(message)
    await message.answer("✨ Here are some amazing products we have for you:", reply_markup=pubg_code_kb())

@dp.message(F.text.in_(BUTTON_BY_KEY["balance"]))
async def msg_balance(message: Message):
    await show_balance(message)

@dp.message(F.text.in_(BUTTON_BY_KEY["support"]))
async def msg_support(message: Message):
    ensure_user(message)
    await message.answer(CONTACT_TEXT, reply_markup=support_kb())

@dp.message(F.text.in_(BUTTON_BY_KEY["orders"]))
async def msg_orders(message: Message):
    ensure_user(message)
    with db() as con:
        rows = con.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10", (message.from_user.id,)).fetchall()
    if not rows:
        await message.answer("📦 You have no orders yet.")
        return
    text = "📦 <b>My Orders</b>\n\n"
    for r in rows:
        text += f"✅ Order: #{r['id']}\n🎮 {r['product_name']} x{r['quantity']}\n💰 ${r['total_price']:.2f}\n📌 Status: {r['status']}\n\n"
    await message.answer(text)

@dp.message(Command("bybitraw"))
async def admin_bybit_raw(message: Message):
    if not admin_only(message):
        return
    end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_ms = int((datetime.now(timezone.utc) - timedelta(hours=BYBIT_DEPOSIT_LOOKBACK_HOURS)).timestamp() * 1000)
    data = await bybit_signed_get("/v5/asset/deposit/query-record", {
        "coin": "USDT",
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": 5,
    })
    safe = json.dumps(data, ensure_ascii=False, indent=2)
    if len(safe) > 3500:
        safe = safe[:3500] + "\n..."
    await message.answer(f"<pre>{safe}</pre>")

@dp.message(F.text.in_(BUTTON_BY_KEY["transactions"]))
async def msg_transactions(message: Message):
    ensure_user(message)
    with db() as con:
        rows = con.execute("SELECT * FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT 10", (message.from_user.id,)).fetchall()
    if not rows:
        await message.answer("📊 You have no transactions yet.")
        return
    text = "📊 <b>My Transactions</b>\n\n"
    for r in rows:
        text += f"💸 Transaction ID: #{r['id']}\n🔄 Type: {r['type']}\n💰 Amount: ${r['amount']:.2f}\n📌 Status: {r['status']}\n📝 {r['description']}\n\n"
    await message.answer(text)

@dp.message(F.text.in_(BUTTON_BY_KEY["manual"]))
async def msg_manual(message: Message, state: FSMContext):
    ensure_user(message)
    await state.set_state(ManualOrderStates.waiting_text)
    await message.answer("⚡ Please send your manual order details.\n\n❌ Send /cancel to cancel.")

@dp.message(ManualOrderStates.waiting_text)
async def manual_received(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Cancelled.", reply_markup=main_keyboard(user_language(message.from_user.id)))
        return
    await state.clear()
    text = f"⚡ <b>New Manual Order</b>\n\nUser ID: {message.from_user.id}\nUsername: @{message.from_user.username or '-'}\n\n{message.text}"
    for admin in ADMIN_IDS:
        with suppress(Exception):
            await bot.send_message(admin, text)
    await message.answer("✅ Your manual order has been sent to support.")

@dp.message(F.text.in_(BUTTON_BY_KEY["language"]))
async def msg_languages(message: Message):
    ensure_user(message)
    await message.answer("🌐 Choose your language:", reply_markup=language_kb())

@dp.callback_query(F.data.startswith("lang:"))
async def cb_language(query: CallbackQuery):
    ensure_user(query)
    lang = query.data.split(":", 1)[1]
    set_user_language(query.from_user.id, lang)
    await query.message.answer(f"✅ Language changed to {LANGUAGES.get(lang, lang)}", reply_markup=main_keyboard(lang))
    await query.answer()

# ------------------------- Deposit flow -------------------------
@dp.callback_query(F.data.startswith("deposit:"))
async def cb_deposit_network(query: CallbackQuery, state: FSMContext):
    ensure_user(query)
    network = query.data.split(":", 1)[1]
    await state.update_data(network=network)
    await state.set_state(DepositStates.waiting_amount)
    await query.message.answer("📝 Enter the amount in USD:-\n🪶 Example: 10\n\n❌ If you want to cancel the process send /cancel")
    await query.answer()

@dp.message(DepositStates.waiting_amount)
async def deposit_amount(message: Message, state: FSMContext):
    ensure_user(message)
    if message.text and message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.answer("❌ Deposit cancelled.", reply_markup=main_keyboard(user_language(message.from_user.id)))
        return
    try:
        amount = round(float((message.text or "").replace(",", ".")), 2)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Please enter a valid amount. Example: 10")
        return

    data = await state.get_data()
    network = data.get("network", "BEP20")
    address = USDT_BEP20_ADDRESS if network == "BEP20" else USDT_TRC20_ADDRESS
    invoice_code = gen_code("INV")
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=INVOICE_EXPIRE_MINUTES)
    with db() as con:
        cur = con.execute(
            """INSERT INTO invoices(invoice_code, user_id, network, address, amount, status, created_at, expires_at)
               VALUES(?,?,?,?,?,?,?,?)""",
            (invoice_code, message.from_user.id, network, address, amount, "waiting", now_iso(), expires_at.isoformat()),
        )
        invoice_id = cur.lastrowid
        con.commit()

    chain_label = "BSC" if network == "BEP20" else "TRC20"
    invoice_text = f"""✅ Kindly deposit exactly {amount:.1f} USDT ({chain_label}) to the address below:

💼

<code>{address}</code>

👆 Tap to copy

⏰ This invoice will expire in {INVOICE_EXPIRE_MINUTES} minutes.
⏬ Kindly complete the deposit of exact amount within this time frame.

🕑 This message will be deleted after {INVOICE_EXPIRE_MINUTES} minutes. 🗑️"""
    sent = await message.answer(invoice_text, reply_markup=invoice_kb(invoice_id))
    await message.answer(f"<code>{address}</code>")
    with db() as con:
        con.execute("UPDATE invoices SET message_id=? WHERE id=?", (sent.message_id, invoice_id))
        con.commit()
    await state.clear()

@dp.callback_query(F.data.startswith("cancel_invoice:"))
async def cb_cancel_invoice(query: CallbackQuery):
    invoice_id = int(query.data.split(":", 1)[1])
    with db() as con:
        inv = con.execute("SELECT * FROM invoices WHERE id=? AND user_id=?", (invoice_id, query.from_user.id)).fetchone()
        if not inv:
            await query.answer("Invoice not found", show_alert=True)
            return
        if inv["status"] == "paid":
            await query.answer("Invoice already paid", show_alert=True)
            return
        con.execute("UPDATE invoices SET status='cancelled' WHERE id=?", (invoice_id,))
        con.commit()
    await query.message.edit_text("❌ Invoice cancelled.")
    await query.answer()

@dp.callback_query(F.data.startswith("check_invoice:"))
async def cb_check_invoice(query: CallbackQuery):
    invoice_id = int(query.data.split(":", 1)[1])
    await query.message.answer("⏳ جاري التحقق من الدفع...\nPlease wait while we verify your payment.")
    ok = await check_single_invoice(invoice_id)
    if ok:
        await query.answer("✅ Payment confirmed", show_alert=True)
    else:
        await query.answer("Payment not found yet. Please wait a little. The bot will keep checking automatically.", show_alert=True)

# ------------------------- Purchase flow -------------------------
def find_product(category: str, key: str, ptype: str) -> Optional[Tuple[str, str, float]]:
    product = _default_product(category, key, ptype)
    if not product:
        return None
    pkey, name, default_price = product
    return (pkey, name, get_custom_price(ptype, category, key) or default_price)

@dp.callback_query(F.data.startswith("buy:"))
async def cb_buy(query: CallbackQuery, state: FSMContext):
    ensure_user(query)
    _, ptype, category, key = query.data.split(":", 3)
    product = find_product(category, key, ptype)
    if not product:
        await query.answer("Product not found", show_alert=True)
        return
    await state.update_data(ptype=ptype, category=category, key=key)
    if ptype == "auto":
        await state.set_state(PurchaseStates.waiting_game_id)
        await query.message.answer(f"""🧾 Selected: {product[1]}
💰 Unit Price: ${product[2]:.2f}

Enter your Game ID number
❌ Send /cancel to cancel.""")
    else:
        await state.set_state(PurchaseStates.waiting_quantity)
        await query.message.answer(f"""🧾 Selected: {product[1]}
💰 Unit Price: ${product[2]:.2f}

Please send the quantity you want.
❌ Send /cancel to cancel.""")
    await query.answer()

@dp.message(PurchaseStates.waiting_quantity)
async def purchase_quantity(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.answer("❌ Cancelled.", reply_markup=main_keyboard(user_language(message.from_user.id)))
        return
    try:
        qty = int(message.text or "")
        if qty <= 0 or qty > 10000:
            raise ValueError
    except ValueError:
        await message.answer("❌ Please send a valid quantity. Example: 1")
        return
    data = await state.get_data()
    ptype, category, key = data["ptype"], data["category"], data["key"]
    product = find_product(category, key, ptype)
    if not product:
        await state.clear()
        await message.answer("❌ Product not found.")
        return
    total = round(product[2] * qty, 2)
    balance = float(get_user(message.from_user.id)["balance"])
    if balance < total:
        await state.clear()
        await message.answer(f"""❌ Insufficient balance.
Required: ${total:.2f}
Your balance: ${balance:.2f}""")
        return
    min_order = get_min_order(message.from_user.id)
    if total < min_order:
        await state.clear()
        await message.answer(f"Minimum order amount is ${min_order:.0f}.")
        return
    await state.update_data(quantity=qty, total=total)
    await complete_order(message, state, game_id=data.get("game_id", ""))

@dp.message(PurchaseStates.waiting_game_id)
async def purchase_game_id(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.answer("❌ Cancelled.", reply_markup=main_keyboard(user_language(message.from_user.id)))
        return
    game_id = (message.text or "").strip()
    if len(game_id) < 3:
        await message.answer("❌ Please send a valid Game ID.")
        return
    balance = float(get_user(message.from_user.id)["balance"])
    min_order = get_min_order(message.from_user.id)
    if balance <= 0:
        await state.clear()
        await message.answer("❌ You do not have any balance. Please top up your balance first.", reply_markup=main_keyboard(user_language(message.from_user.id)))
        return
    if balance < min_order:
        await state.clear()
        await message.answer(f"Minimum order amount is ${min_order:.0f}.", reply_markup=main_keyboard(user_language(message.from_user.id)))
        return
    await state.update_data(game_id=game_id)
    await state.set_state(PurchaseStates.waiting_quantity)
    await message.answer("""Please send the quantity you want.
❌ Send /cancel to cancel.""")

async def complete_order(message: Message, state: FSMContext, game_id: str):
    data = await state.get_data()
    ptype, category, key, qty, total = data["ptype"], data["category"], data["key"], int(data["quantity"]), float(data["total"])
    product = find_product(category, key, ptype)
    if not product:
        await state.clear()
        await message.answer("❌ Product not found.")
        return
    tx_id, before, after = deduct_balance(message.from_user.id, total, f"Purchase {product[1]} x{qty}")
    code_text = ""
    status = "processing"
    if ptype == "code":
        codes = reserve_uc_codes(product[0], qty, message.from_user.id)
        if len(codes) >= qty:
            code_text = "\n".join(codes)
            status = "completed"
        else:
            status = "processing"
            code_text = "Your order is being processed. Support will deliver the code soon."
    with db() as con:
        cur = con.execute(
            """INSERT INTO orders(order_code, user_id, category, product_key, product_name, quantity, unit_price, total_price, game_id, code, status, created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (gen_code("ORD"), message.from_user.id, category, key, product[1], qty, product[2], total, game_id, code_text, status, now_iso()),
        )
        order_id = cur.lastrowid
        if code_text and status == "completed":
            con.execute("UPDATE uc_codes SET order_id=? WHERE used_by=? AND order_id IS NULL", (order_id, message.from_user.id))
        con.commit()
    await state.clear()
    text = f"""✅ Order created successfully.

🧾 Order ID: #{order_id}
🎮 Product: {product[1]}
🔢 Quantity: {qty}
💰 Total: ${total:.2f}
📊 Balance Before: ${before:.2f}
📈 Balance After: ${after:.2f}
📌 Status: {status}"""
    if game_id:
        text += f"\n🆔 Game ID: <code>{game_id}</code>"
    if ptype == "code":
        text += f"\n\n🎟 Code:\n<code>{code_text}</code>"
    await message.answer(text, reply_markup=main_keyboard(user_language(message.from_user.id)))
    for admin in ADMIN_IDS:
        with suppress(Exception):
            await bot.send_message(admin, f"🆕 New Order #{order_id}\nUser: {message.from_user.id}\nProduct: {product[1]} x{qty}\nTotal: ${total:.2f}\nStatus: {status}")

def reserve_uc_codes(amount: str, qty: int, user_id: int) -> List[str]:
    with db() as con:
        rows = con.execute("SELECT * FROM uc_codes WHERE amount=? AND used=0 ORDER BY id ASC LIMIT ?", (amount, qty)).fetchall()
        codes = [r["code"] for r in rows]
        for r in rows:
            con.execute("UPDATE uc_codes SET used=1, used_by=? WHERE id=?", (user_id, r["id"]))
        con.commit()
        return codes

# ------------------------- Bybit API -------------------------
def bybit_sign(query: str, timestamp: str) -> str:
    """Bybit V5 GET signature: timestamp + api_key + recv_window + query_string."""
    payload = f"{timestamp}{BYBIT_API_KEY}{BYBIT_RECV_WINDOW}{query}"
    return hmac.new(BYBIT_API_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()

async def bybit_signed_get(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if not BYBIT_API_KEY or not BYBIT_API_SECRET:
        return {"retCode": -1, "retMsg": "BYBIT_API_KEY or BYBIT_API_SECRET is missing in Railway Variables", "result": {}}
    # Bybit V5 signs the exact query string used in the URL.
    # Sorting parameters keeps the signature stable and avoids random mismatch issues.
    clean_params = {k: v for k, v in params.items() if v is not None and v != ""}
    query = urlencode(sorted(clean_params.items()))
    timestamp = str(int(time.time() * 1000))
    headers = {
        "X-BAPI-API-KEY": BYBIT_API_KEY,
        "X-BAPI-SIGN": bybit_sign(query, timestamp),
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-RECV-WINDOW": BYBIT_RECV_WINDOW,
        "X-BAPI-SIGN-TYPE": "2",
    }
    url = f"{BYBIT_BASE_URL}{path}?{query}" if query else f"{BYBIT_BASE_URL}{path}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=25) as resp:
            try:
                return await resp.json(content_type=None)
            except Exception:
                body = await resp.text()
                return {"retCode": resp.status, "retMsg": body[:500], "result": {}}

async def bybit_get_deposits(start_ms: int, end_ms: int) -> List[Dict[str, Any]]:
    """Read Bybit USDT on-chain deposit history with pagination.

    Official endpoint:
    GET /v5/asset/deposit/query-record

    Notes:
    - Bybit may return a nextPageCursor when there are more than 50 records.
    - Some successful deposit statuses can be 3 or 10012 depending on account/funding flow.
    """
    rows: List[Dict[str, Any]] = []
    cursor = ""
    for _ in range(10):
        params = {
            "coin": "USDT",
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": 50,
            "cursor": cursor,
        }
        data = await bybit_signed_get("/v5/asset/deposit/query-record", params)
        if str(data.get("retCode")) != "0":
            print("Bybit deposit error:", data)
            return rows
        result = data.get("result") or {}
        batch = result.get("rows") or result.get("list") or []
        rows.extend(batch)
        cursor = str(result.get("nextPageCursor") or "").strip()
        if not cursor:
            break
    print(f"Bybit deposits fetched: {len(rows)}")
    return rows

def _deposit_field(dep: Dict[str, Any], *names: str) -> str:
    for name in names:
        value = dep.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""

def chain_matches(network: str, chain: str, to_address: str) -> bool:
    c = (chain or "").upper().replace(" ", "").replace("-", "")
    addr = (to_address or "").strip().lower()

    # Bybit sometimes returns only the chain without toAddress, and sometimes
    # returns the address without a clear chain name. Accept either reliable match.
    if network == "BEP20":
        chain_ok = any(x in c for x in ("BSC", "BEP20", "BNBSMARTCHAIN", "BSCBEP20"))
        address_ok = bool(addr) and addr == USDT_BEP20_ADDRESS.lower()
        return chain_ok or address_ok

    if network == "TRC20":
        chain_ok = any(x in c for x in ("TRX", "TRC20", "TRON"))
        address_ok = bool(addr) and addr == USDT_TRC20_ADDRESS.lower()
        return chain_ok or address_ok

    return False

def close_amount(a: float, b: float) -> bool:
    # Small tolerance fixes Bybit rounding/credit display differences.
    return abs(float(a) - float(b)) <= BYBIT_MATCH_TOLERANCE

def deposit_success(dep: Dict[str, Any]) -> bool:
    status = str(dep.get("status", "")).strip()
    # Bybit V5 depositStatus:
    # 3 = success/finalised, 10012 = credited to funding pool successfully.
    return status in {
        "3", "10012",
        "SUCCESS", "Success", "success",
        "COMPLETED", "Completed", "completed",
        "CREDITED", "Credited", "credited",
    }

async def check_single_invoice(invoice_id: int) -> bool:
    with db() as con:
        inv = con.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    if not inv or inv["status"] != "waiting":
        return False
    return await match_invoice(inv)

async def match_invoice(inv: sqlite3.Row) -> bool:
    created = datetime.fromisoformat(inv["created_at"])
    expires = datetime.fromisoformat(inv["expires_at"])
    now = datetime.now(timezone.utc)

    # Look back at least 24h by default so Railway/server time differences or restarts do not miss the deposit.
    # Start from before invoice creation to catch payments sent immediately after address display.
    start = min(created - timedelta(minutes=15), now - timedelta(hours=BYBIT_DEPOSIT_LOOKBACK_HOURS))
    start_ms = int(start.timestamp() * 1000)
    end_ms = int((now + timedelta(minutes=5)).timestamp() * 1000)

    deposits = await bybit_get_deposits(start_ms, end_ms)
    print(f"Checking invoice {inv['id']} user={inv['user_id']} amount={inv['amount']} network={inv['network']} deposits={len(deposits)}")

    for dep in deposits:
        txid = _deposit_field(dep, "txID", "txId", "txHash", "hash", "id")
        if not txid:
            continue

        with db() as con:
            used = con.execute("SELECT txid FROM used_bybit_txids WHERE txid=?", (txid,)).fetchone()
        if used:
            continue

        try:
            amount = float(_deposit_field(dep, "amount", "qty", "quantity") or "0")
        except ValueError:
            continue

        if not deposit_success(dep):
            print("Deposit skipped, not success:", {"txid": txid, "status": dep.get("status")})
            continue

        if not close_amount(amount, float(inv["amount"])):
            print("Deposit skipped, amount mismatch:", {"txid": txid, "dep_amount": amount, "invoice_amount": float(inv["amount"])})
            continue

        chain = _deposit_field(dep, "chain", "network", "chainType")
        to_addr = _deposit_field(dep, "toAddress", "address", "walletAddress", "depositAddress")
        if not chain_matches(inv["network"], chain, to_addr):
            print("Deposit skipped, chain/address mismatch:", {"txid": txid, "chain": chain, "to": to_addr, "invoice_network": inv["network"]})
            continue

        await mark_invoice_paid(inv, txid, amount)
        return True

    # Only expire after checking, so delayed confirmations can still be caught if they arrived.
    if now > expires:
        with db() as con:
            con.execute("UPDATE invoices SET status='expired' WHERE id=? AND status='waiting'", (inv["id"],))
            con.commit()
    return False

async def mark_invoice_paid(inv: sqlite3.Row, txid: str, amount: float) -> None:
    user_id = int(inv["user_id"])
    network = inv["network"]
    description = f"Payment from {network} Pay"
    with db() as con:
        already = con.execute("SELECT txid FROM used_bybit_txids WHERE txid=?", (txid,)).fetchone()
        if already:
            return
        con.execute("INSERT INTO used_bybit_txids(txid, invoice_id, user_id, amount, created_at) VALUES(?,?,?,?,?)", (txid, inv["id"], user_id, amount, now_iso()))
        con.execute("UPDATE invoices SET status='paid', txid=? WHERE id=?", (txid, inv["id"]))
        con.commit()
    tx_id, before, after = add_balance(user_id, amount, description, txid)
    text = f"""🙏 Thank you for your payment!

💰 Your amount {amount:.1f} $ is being credited to your wallet

💸 New Transaction 💸

✅ Transaction ID: #{tx_id}
🆔 User ID: {user_id}
🔄 Type: Add Balance
💰 Amount: ${amount:.2f}
📊 Balance Before: ${before:.2f}
📈 Balance After: ${after:.2f}
📌 Status: Success
📝 Description: {description}"""
    with suppress(Exception):
        await bot.send_message(user_id, text)
    for admin in ADMIN_IDS:
        with suppress(Exception):
            await bot.send_message(admin, f"💸 Auto payment confirmed\nUser: {user_id}\nAmount: ${amount:.2f}\nNetwork: {network}\nTXID: <code>{txid}</code>")

async def invoice_watcher() -> None:
    await asyncio.sleep(5)
    while True:
        try:
            with db() as con:
                rows = con.execute("SELECT * FROM invoices WHERE status='waiting' ORDER BY id ASC LIMIT 50").fetchall()
            if rows:
                print(f"Invoice watcher: {len(rows)} waiting invoices")
            for inv in rows:
                with suppress(Exception):
                    await match_invoice(inv)
        except Exception as e:
            print("invoice_watcher error:", repr(e))
        await asyncio.sleep(30)

# ------------------------- Admin commands -------------------------
def admin_only(message: Message) -> bool:
    return message.from_user and message.from_user.id in ADMIN_IDS

@dp.callback_query(F.data.startswith("admin_reply:"))
async def cb_admin_reply(query: CallbackQuery, state: FSMContext):
    if query.from_user.id not in ADMIN_IDS:
        return
    uid = int(query.data.split(":", 1)[1])
    await state.update_data(reply_user_id=uid)
    await state.set_state(AdminReplyStates.waiting_text)
    await query.message.answer(f"✉️ Send your reply to user {uid}. Send /cancel to cancel.")
    await query.answer()

@dp.message(AdminReplyStates.waiting_text)
async def admin_reply_text(message: Message, state: FSMContext):
    if not admin_only(message):
        return
    if message.text and message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.answer("❌ Cancelled.")
        return
    data = await state.get_data()
    uid = int(data.get("reply_user_id"))
    await bot.send_message(uid, f"""📩 <b>Support Reply</b>

{message.text or ''}""")
    await state.clear()
    await message.answer("✅ Reply sent.")

@dp.message(Command("adminprices"))
async def admin_prices(message: Message):
    if not admin_only(message):
        return
    await message.answer("⚙️ Choose a category to edit prices:", reply_markup=admin_price_categories_kb())

@dp.callback_query(F.data.startswith("admin_cat:"))
async def cb_admin_price_category(query: CallbackQuery):
    if query.from_user.id not in ADMIN_IDS:
        return
    _, ptype, category = query.data.split(":", 2)
    await query.message.answer(f"⚙️ Edit prices for {category}:", reply_markup=admin_products_kb(ptype, category))
    await query.answer()

@dp.callback_query(F.data.startswith("admin_rate:"))
async def cb_admin_rate(query: CallbackQuery, state: FSMContext):
    if query.from_user.id not in ADMIN_IDS:
        return
    _, ptype, category = query.data.split(":", 2)
    await state.update_data(price_ptype=ptype, price_category=category)
    await state.set_state(AdminPriceStates.waiting_percent)
    await query.message.answer(f"""Send new percent for all products in:
{category}

Example: 75""")
    await query.answer()

@dp.message(AdminPriceStates.waiting_percent)
async def admin_rate_text(message: Message, state: FSMContext):
    if not admin_only(message):
        return
    try:
        percent = float((message.text or "").replace("%", "").replace(",", "."))
        if percent <= 0 or percent > 1000:
            raise ValueError
    except ValueError:
        await message.answer("❌ Send valid percent. Example: 75")
        return
    data = await state.get_data()
    count = apply_category_percent(data["price_ptype"], data["price_category"], percent)
    await state.clear()
    await message.answer(f"✅ Updated {count} products to {percent:g}%.", reply_markup=admin_products_kb(data["price_ptype"], data["price_category"]))

@dp.callback_query(F.data.startswith("admin_price:"))
async def cb_admin_price(query: CallbackQuery, state: FSMContext):
    if query.from_user.id not in ADMIN_IDS:
        return
    _, ptype, category, key = query.data.split(":", 3)
    await state.update_data(price_ptype=ptype, price_category=category, price_key=key)
    await state.set_state(AdminPriceStates.waiting_price)
    await query.message.answer("Send new price in USD. Example: 3.75")
    await query.answer()

@dp.message(AdminPriceStates.waiting_price)
async def admin_price_text(message: Message, state: FSMContext):
    if not admin_only(message):
        return
    try:
        price = float((message.text or "").replace(",", "."))
        if price < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Send valid price. Example: 3.75")
        return
    data = await state.get_data()
    set_custom_price(data["price_ptype"], data["price_category"], data["price_key"], price)
    await state.clear()
    await message.answer("✅ Product price updated.", reply_markup=admin_products_kb(data["price_ptype"], data["price_category"]))

@dp.message(Command("setpercent"))
async def admin_set_percent_cmd(message: Message):
    if not admin_only(message):
        return
    import shlex
    try:
        parts = shlex.split(message.text or "")
    except ValueError:
        parts = (message.text or "").split()
    if len(parts) < 3:
        await message.answer('Usage: /setpercent "PUBG MOBILE ID AUTO" 75')
        return
    try:
        percent = float(parts[-1].replace("%", ""))
    except ValueError:
        await message.answer("Invalid percent.")
        return
    category = " ".join(parts[1:-1])
    ptype = "code" if category == "PUBG UC CODE" else "auto"
    if ptype == "auto" and category not in GAME_CATEGORIES:
        await message.answer("Category not found.")
        return
    count = apply_category_percent(ptype, category, percent)
    await message.answer(f"✅ Updated {category}: {count} products to {percent:g}%.")

@dp.message(Command("setprice"))
async def admin_set_price_cmd(message: Message):
    if not admin_only(message):
        return
    import shlex
    try:
        parts = shlex.split(message.text or "")
    except ValueError:
        parts = (message.text or "").split()
    if len(parts) != 5:
        await message.answer('Usage: /setprice auto "PUBG MOBILE ID AUTO" 60 0.75')
        return
    _, ptype, category, key, price_s = parts
    try:
        price = float(price_s)
    except ValueError:
        await message.answer("Invalid price.")
        return
    if not _default_product(category, key, ptype):
        await message.answer("Product not found.")
        return
    set_custom_price(ptype, category, key, price)
    await message.answer(f"✅ Price updated: {category} / {key} = ${price:.2f}")

@dp.message(Command("addbalance"))
async def admin_add_balance(message: Message):
    if not admin_only(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 3:
        await message.answer("Usage: /addbalance USER_ID AMOUNT")
        return
    try:
        uid, amount = int(parts[1]), float(parts[2])
    except ValueError:
        await message.answer("Invalid format.")
        return
    get_user(uid)
    tx_id, before, after = add_balance(uid, amount, "Admin Add Balance")
    await message.answer(f"✅ Added ${amount:.2f}\nBefore: ${before:.2f}\nAfter: ${after:.2f}\nTX: #{tx_id}")
    with suppress(Exception):
        await bot.send_message(uid, f"✅ Your balance has been updated.\n💰 Amount: ${amount:.2f}\n📈 New Balance: ${after:.2f}")

@dp.message(Command("setbalance"))
async def admin_set_balance(message: Message):
    if not admin_only(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 3:
        await message.answer("Usage: /setbalance USER_ID AMOUNT")
        return
    uid, amount = int(parts[1]), float(parts[2])
    get_user(uid)
    with db() as con:
        con.execute("UPDATE users SET balance=? WHERE user_id=?", (amount, uid))
        con.commit()
    await message.answer("✅ Balance updated.")

@dp.message(Command("removebalance"))
async def admin_remove_balance(message: Message):
    if not admin_only(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 3:
        await message.answer("Usage: /removebalance USER_ID AMOUNT")
        return
    try:
        uid, amount = int(parts[1]), float(parts[2])
    except ValueError:
        await message.answer("Invalid format.")
        return
    get_user(uid)
    tx_id, before, after = deduct_balance(uid, amount, "Admin Remove Balance")
    await message.answer(f"✅ Removed ${amount:.2f}\nBefore: ${before:.2f}\nAfter: ${after:.2f}\nTX: #{tx_id}")
    with suppress(Exception):
        await bot.send_message(uid, f"⚠️ Balance updated by admin.\n💰 Removed: ${amount:.2f}\n📉 New Balance: ${after:.2f}")

@dp.message(Command("setmin"))
async def admin_set_user_min(message: Message):
    if not admin_only(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 3:
        await message.answer("Usage: /setmin USER_ID AMOUNT")
        return
    try:
        uid, amount = int(parts[1]), float(parts[2])
    except ValueError:
        await message.answer("Invalid format.")
        return
    get_user(uid)
    with db() as con:
        con.execute("UPDATE users SET user_min_order=? WHERE user_id=?", (amount, uid))
        con.commit()
    await message.answer(f"✅ Minimum order for {uid} set to ${amount:.2f}.")

@dp.message(Command("clearmin"))
async def admin_clear_user_min(message: Message):
    if not admin_only(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.answer("Usage: /clearmin USER_ID")
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await message.answer("Invalid user id.")
        return
    get_user(uid)
    with db() as con:
        con.execute("UPDATE users SET user_min_order=NULL WHERE user_id=?", (uid,))
        con.commit()
    await message.answer(f"✅ Custom minimum removed for {uid}. Global minimum applies now: ${MIN_ORDER_AMOUNT:.0f}.")

@dp.message(Command("ban"))
async def admin_ban(message: Message):
    if not admin_only(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.answer("Usage: /ban USER_ID")
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await message.answer("Invalid user id.")
        return
    get_user(uid)
    with db() as con:
        con.execute("UPDATE users SET banned=1 WHERE user_id=?", (uid,))
        con.commit()
    await message.answer(f"✅ User {uid} banned.")

@dp.message(Command("unban"))
async def admin_unban(message: Message):
    if not admin_only(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.answer("Usage: /unban USER_ID")
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await message.answer("Invalid user id.")
        return
    get_user(uid)
    with db() as con:
        con.execute("UPDATE users SET banned=0 WHERE user_id=?", (uid,))
        con.commit()
    await message.answer(f"✅ User {uid} unbanned.")

@dp.message(Command("checkuser"))
async def admin_check_user(message: Message):
    if not admin_only(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.answer("Usage: /checkuser USER_ID")
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await message.answer("Invalid user id.")
        return
    user = get_user(uid)
    await message.answer(f"""👤 User Info

ID: <code>{uid}</code>
Username: @{user['username'] or '-'}
Name: {user['first_name'] or '-'}
Balance: ${float(user['balance']):.2f}
Minimum Order: ${get_min_order(uid):.2f}
Banned: {'Yes' if int(user['banned'] or 0) else 'No'}""")

@dp.message(Command("bybittest"))
async def admin_bybit_test(message: Message):
    if not admin_only(message):
        return
    end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_ms = int((datetime.now(timezone.utc) - timedelta(hours=BYBIT_DEPOSIT_LOOKBACK_HOURS)).timestamp() * 1000)
    if not BYBIT_API_KEY or not BYBIT_API_SECRET:
        await message.answer("❌ BYBIT_API_KEY or BYBIT_API_SECRET is missing in Railway Variables.")
        return
    rows = await bybit_get_deposits(start_ms, end_ms)
    text = f"✅ Bybit API connected. Deposits found in last {BYBIT_DEPOSIT_LOOKBACK_HOURS}h: {len(rows)}"
    if rows:
        preview = []
        for dep in rows[:5]:
            preview.append(
                f"TXID: <code>{_deposit_field(dep, 'txID', 'txId', 'txHash')[:18]}...</code>\n"
                f"Amount: {_deposit_field(dep, 'amount', 'qty')} USDT\n"
                f"Chain: {_deposit_field(dep, 'chain', 'network', 'chainType')}\n"
                f"Status: {dep.get('status')}"
            )
        text += "\n\n" + "\n---\n".join(preview)
    await message.answer(text)

@dp.message(Command("checkinvoice"))
async def admin_check_invoice(message: Message):
    if not admin_only(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.answer("Usage: /checkinvoice INVOICE_ID")
        return
    try:
        invoice_id = int(parts[1])
    except ValueError:
        await message.answer("Invalid invoice id.")
        return
    ok = await check_single_invoice(invoice_id)
    await message.answer("✅ Invoice paid and balance added." if ok else "❌ Payment not matched yet. Check Railway logs or run /bybittest.")

@dp.message(Command("admin"))
async def admin_help(message: Message):
    if not admin_only(message):
        return
    await message.answer("""⚙️ Admin Commands

/addbalance USER_ID AMOUNT
/removebalance USER_ID AMOUNT
/setbalance USER_ID AMOUNT
/setmin USER_ID AMOUNT
/clearmin USER_ID
/ban USER_ID
/unban USER_ID
/checkuser USER_ID
/adminprices
/setpercent "CATEGORY" 75
/setprice auto "CATEGORY" PRODUCT_KEY PRICE
/addcode AMOUNT CODE
/stock
/broadcast MESSAGE
/bybittest
/checkinvoice INVOICE_ID""")

@dp.message(Command("addcode"))
async def admin_add_code(message: Message):
    if not admin_only(message):
        return
    # /addcode 60 CODE_HERE
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) != 3:
        await message.answer("Usage: /addcode AMOUNT CODE")
        return
    amount, code = parts[1], parts[2].strip()
    with db() as con:
        try:
            con.execute("INSERT INTO uc_codes(amount, code, used, created_at) VALUES(?,?,0,?)", (amount, code, now_iso()))
            con.commit()
            await message.answer("✅ Code added.")
        except sqlite3.IntegrityError:
            await message.answer("❌ This code already exists.")

@dp.message(Command("stock"))
async def admin_stock(message: Message):
    if not admin_only(message):
        return
    with db() as con:
        rows = con.execute("SELECT amount, COUNT(*) AS cnt FROM uc_codes WHERE used=0 GROUP BY amount ORDER BY amount").fetchall()
    if not rows:
        await message.answer("No stock.")
        return
    await message.answer("\n".join([f"{r['amount']} UC: {r['cnt']}" for r in rows]))

@dp.message(Command("broadcast"))
async def admin_broadcast(message: Message):
    if not admin_only(message):
        return
    text = (message.text or "").split(maxsplit=1)
    if len(text) < 2:
        await message.answer("Usage: /broadcast MESSAGE")
        return
    with db() as con:
        users = con.execute("SELECT user_id FROM users").fetchall()
    ok = 0
    for u in users:
        with suppress(Exception):
            await bot.send_message(u["user_id"], text[1])
            ok += 1
            await asyncio.sleep(0.05)
    await message.answer(f"✅ Sent to {ok} users.")

@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Cancelled.", reply_markup=main_keyboard(user_language(message.from_user.id)))

# ------------------------- Fallback -------------------------
@dp.message()
async def fallback(message: Message):
    ensure_user(message)
    await message.answer("Please select one of the options below:", reply_markup=main_keyboard(user_language(message.from_user.id)))

async def main():
    init_db()
    asyncio.create_task(invoice_watcher())
    print("MD Game ID bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
