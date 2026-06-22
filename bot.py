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
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import aiohttp
from aiogram import Bot, Dispatcher, F
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
)
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
BOT_NAME = os.getenv("BOT_NAME", "MD Game ID").strip()
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "md_game_id.db"))
DB_PATH = str(Path(DATABASE_PATH) if Path(DATABASE_PATH).is_absolute() else BASE_DIR / DATABASE_PATH)
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x.isdigit()}

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

# ------------------------- FSM -------------------------
class DepositStates(StatesGroup):
    waiting_amount = State()

class PurchaseStates(StatesGroup):
    waiting_quantity = State()
    waiting_game_id = State()
    waiting_confirm = State()

class ManualOrderStates(StatesGroup):
    waiting_text = State()

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
            created_at TEXT NOT NULL
        )""")
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

# ------------------------- Keyboards -------------------------
def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚀 Game ID Recharge (Auto)")],
            [KeyboardButton(text="🎮 PUBG UC CODE")],
            [KeyboardButton(text="💰 My Balance"), KeyboardButton(text="📦 My Orders")],
            [KeyboardButton(text="📊 My Transaction"), KeyboardButton(text="⚡ Manual Order")],
            [KeyboardButton(text="☎️ Contact Support")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Select an option...",
    )

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
    for key, name, price in GAME_CATEGORIES[category]:
        rows.append([InlineKeyboardButton(text=f"{name} | {price:.2f}$", callback_data=f"buy:auto:{category}:{key}")])
    rows.append([InlineKeyboardButton(text="🔙 Back to Collection", callback_data="game_auto")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def pubg_code_kb() -> InlineKeyboardMarkup:
    rows = []
    for key, name, price in PUBG_UC_CODE_PRODUCTS:
        rows.append([InlineKeyboardButton(text=f"{name} | {price:.2f} USDT", callback_data=f"buy:code:PUBG UC CODE:{key}")])
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
    logo = Path(LOGO_PATH)
    if logo.exists():
        await message.answer_photo(FSInputFile(str(logo)), caption=WELCOME_TEXT, reply_markup=main_keyboard())
    else:
        await message.answer(WELCOME_TEXT, reply_markup=main_keyboard())

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

# ------------------------- Start and menu handlers -------------------------
@dp.message(CommandStart())
async def cmd_start(message: Message):
    ensure_user(message)
    await send_welcome(message)

@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    ensure_user(message)
    await send_welcome(message)

@dp.callback_query(F.data == "main")
async def cb_main(query: CallbackQuery):
    ensure_user(query)
    await query.message.answer(WELCOME_TEXT, reply_markup=main_keyboard())
    await query.answer()

@dp.message(F.text == "🚀 Game ID Recharge (Auto)")
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

@dp.message(F.text == "🎮 PUBG UC CODE")
async def msg_pubg_code(message: Message):
    ensure_user(message)
    await message.answer("✨ Here are some amazing products we have for you:", reply_markup=pubg_code_kb())

@dp.message(F.text == "💰 My Balance")
async def msg_balance(message: Message):
    await show_balance(message)

@dp.message(F.text == "☎️ Contact Support")
async def msg_support(message: Message):
    ensure_user(message)
    await message.answer(CONTACT_TEXT, reply_markup=support_kb())

@dp.message(F.text == "📦 My Orders")
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

@dp.message(F.text == "📊 My Transaction")
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

@dp.message(F.text == "⚡ Manual Order")
async def msg_manual(message: Message, state: FSMContext):
    ensure_user(message)
    await state.set_state(ManualOrderStates.waiting_text)
    await message.answer("⚡ Please send your manual order details.\n\n❌ Send /cancel to cancel.")

@dp.message(ManualOrderStates.waiting_text)
async def manual_received(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Cancelled.", reply_markup=main_keyboard())
        return
    await state.clear()
    text = f"⚡ <b>New Manual Order</b>\n\nUser ID: {message.from_user.id}\nUsername: @{message.from_user.username or '-'}\n\n{message.text}"
    for admin in ADMIN_IDS:
        with suppress(Exception):
            await bot.send_message(admin, text)
    await message.answer("✅ Your manual order has been sent to support.")

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
        await message.answer("❌ Deposit cancelled.", reply_markup=main_keyboard())
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
    ok = await check_single_invoice(invoice_id)
    if ok:
        await query.answer("✅ Payment confirmed", show_alert=True)
    else:
        await query.answer("Payment not found yet. Please wait a little and try again.", show_alert=True)

# ------------------------- Purchase flow -------------------------
def find_product(category: str, key: str, ptype: str) -> Optional[Tuple[str, str, float]]:
    if ptype == "code":
        return next((p for p in PUBG_UC_CODE_PRODUCTS if p[0] == key), None)
    return next((p for p in GAME_CATEGORIES.get(category, []) if p[0] == key), None)

@dp.callback_query(F.data.startswith("buy:"))
async def cb_buy(query: CallbackQuery, state: FSMContext):
    ensure_user(query)
    _, ptype, category, key = query.data.split(":", 3)
    product = find_product(category, key, ptype)
    if not product:
        await query.answer("Product not found", show_alert=True)
        return
    await state.update_data(ptype=ptype, category=category, key=key)
    await state.set_state(PurchaseStates.waiting_quantity)
    await query.message.answer(f"🧾 Selected: {product[1]}\n💰 Unit Price: ${product[2]:.2f}\n\nPlease send the quantity you want.\n❌ Send /cancel to cancel.")
    await query.answer()

@dp.message(PurchaseStates.waiting_quantity)
async def purchase_quantity(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.answer("❌ Cancelled.", reply_markup=main_keyboard())
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
    # Minimum appears only at purchase attempt.
    if total < MIN_ORDER_AMOUNT:
        await state.clear()
        await message.answer(f"Minimum order amount is ${MIN_ORDER_AMOUNT:.0f}.")
        return
    balance = float(get_user(message.from_user.id)["balance"])
    if balance < total:
        await state.clear()
        await message.answer(f"❌ Insufficient balance.\nRequired: ${total:.2f}\nYour balance: ${balance:.2f}")
        return
    await state.update_data(quantity=qty, total=total)
    if ptype == "auto":
        await state.set_state(PurchaseStates.waiting_game_id)
        await message.answer("🆔 Please send your Game ID / Player ID.\n❌ Send /cancel to cancel.")
    else:
        await complete_order(message, state, game_id="")

@dp.message(PurchaseStates.waiting_game_id)
async def purchase_game_id(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.answer("❌ Cancelled.", reply_markup=main_keyboard())
        return
    game_id = (message.text or "").strip()
    if len(game_id) < 3:
        await message.answer("❌ Please send a valid Game ID.")
        return
    await complete_order(message, state, game_id=game_id)

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
    await message.answer(text, reply_markup=main_keyboard())
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
    payload = f"{timestamp}{BYBIT_API_KEY}{BYBIT_RECV_WINDOW}{query}"
    return hmac.new(BYBIT_API_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()

async def bybit_get_deposits(start_ms: int, end_ms: int) -> List[Dict[str, Any]]:
    if not BYBIT_API_KEY or not BYBIT_API_SECRET:
        return []
    params = {"coin": "USDT", "startTime": start_ms, "endTime": end_ms, "limit": 50}
    query = urlencode(params)
    timestamp = str(int(time.time() * 1000))
    headers = {
        "X-BAPI-API-KEY": BYBIT_API_KEY,
        "X-BAPI-SIGN": bybit_sign(query, timestamp),
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-RECV-WINDOW": BYBIT_RECV_WINDOW,
        "X-BAPI-SIGN-TYPE": "2",
    }
    url = f"{BYBIT_BASE_URL}/v5/asset/deposit/query-record?{query}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=20) as resp:
            data = await resp.json(content_type=None)
    if str(data.get("retCode")) != "0":
        print("Bybit deposit error:", data)
        return []
    result = data.get("result") or {}
    return result.get("rows") or []

def chain_matches(network: str, chain: str, to_address: str) -> bool:
    c = (chain or "").upper()
    addr = (to_address or "").strip().lower()
    if network == "BEP20":
        return ("BSC" in c or "BEP20" in c or "BSC(BEP20)" in c) and addr == USDT_BEP20_ADDRESS.lower()
    if network == "TRC20":
        return ("TRX" in c or "TRC20" in c) and addr == USDT_TRC20_ADDRESS.lower()
    return False

def close_amount(a: float, b: float) -> bool:
    return abs(a - b) <= 0.000001

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
    if now > expires:
        with db() as con:
            con.execute("UPDATE invoices SET status='expired' WHERE id=? AND status='waiting'", (inv["id"],))
            con.commit()
        return False
    start_ms = int((created - timedelta(minutes=5)).timestamp() * 1000)
    end_ms = int((now + timedelta(minutes=5)).timestamp() * 1000)
    deposits = await bybit_get_deposits(start_ms, end_ms)
    for dep in deposits:
        txid = dep.get("txID") or dep.get("txId") or ""
        if not txid:
            continue
        with db() as con:
            used = con.execute("SELECT txid FROM used_bybit_txids WHERE txid=?", (txid,)).fetchone()
        if used:
            continue
        try:
            amount = float(dep.get("amount", "0"))
        except ValueError:
            continue
        # status 3 is Success in Bybit V5 deposit records; some accounts may return string statuses.
        status = str(dep.get("status", ""))
        if status not in {"3", "SUCCESS", "Success", "success", "1"}:
            continue
        if not close_amount(amount, float(inv["amount"])):
            continue
        if not chain_matches(inv["network"], dep.get("chain", ""), dep.get("toAddress", "")):
            continue
        await mark_invoice_paid(inv, txid, amount)
        return True
    return False

async def mark_invoice_paid(inv: sqlite3.Row, txid: str, amount: float) -> None:
    user_id = int(inv["user_id"])
    network = inv["network"]
    description = f"Payment from {network} Pay"
    with db() as con:
        con.execute("INSERT OR IGNORE INTO used_bybit_txids(txid, invoice_id, user_id, amount, created_at) VALUES(?,?,?,?,?)", (txid, inv["id"], user_id, amount, now_iso()))
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
            for inv in rows:
                with suppress(Exception):
                    await match_invoice(inv)
        except Exception as e:
            print("invoice_watcher error:", repr(e))
        await asyncio.sleep(30)

# ------------------------- Admin commands -------------------------
def admin_only(message: Message) -> bool:
    return message.from_user and message.from_user.id in ADMIN_IDS

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
    await message.answer("❌ Cancelled.", reply_markup=main_keyboard())

# ------------------------- Fallback -------------------------
@dp.message()
async def fallback(message: Message):
    ensure_user(message)
    await message.answer("Please select one of the options below:", reply_markup=main_keyboard())

async def main():
    init_db()
    asyncio.create_task(invoice_watcher())
    print("MD Game ID bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
