# MD Supplier Bot

Telegram supplier bot for PUBG UC codes and PUBG UC top-up by ID.

## Features

- English and Russian languages
- Main menu: SHOP, Top Up Balance, My Orders, Cart, Account, Language
- SHOP > PUBG UC > Codes / Top-up by ID
- Code prices:
  - 60 UC - 0.79 USDT
  - 325 UC - 3.81 USDT
  - 660 UC - 7.81 USDT
  - 1800 UC - 19.54 USDT
  - 3850 UC - 39.07 USDT
  - 8100 UC - 78.14 USDT
- Top-up by ID prices are 2% lower
- USDT BEP20 balance top-up section
- Automatic test code delivery
- Automatic MD STORE receipt image for ID top-up orders
- Admin panel commands

Telegram does not allow bots to choose exact inline button colors. Telegram clients render inline buttons in their own colors automatically.

## Railway Variables

Add these variables in Railway:

```env
BOT_TOKEN=YOUR_NEW_BOT_TOKEN
BOT_NAME=MD Supplier Bot
SUPPORT_USERNAME=@bot_MD_global
ADMIN_IDS=8573174269
USDT_BEP20_ADDRESS=0xA2E0c2eC432953Dd2F832488a1EC061e6e761361
MIN_DEPOSIT_USDT=50
DATABASE_PATH=md_supplier_bot.db
```

Important: If you already shared your bot token anywhere, revoke it from BotFather and create a new token.

## Admin Commands

```text
/admin
/addbalance USER_ID AMOUNT
/removebalance USER_ID AMOUNT
/setbalance USER_ID AMOUNT
/check USER_ID
/orders
/ban USER_ID
/unban USER_ID
/setmin USER_ID AMOUNT
/resetmin USER_ID
/prices
/setprice TYPE AMOUNT PRICE
/broadcast MESSAGE
```

TYPE in `/setprice` must be `code` or `id`.

Examples:

```text
/setprice code 8100 78.14
/setprice id 8100 76.58
/addbalance 123456789 100
/setmin 123456789 200
```

## Deploy to Railway

1. Upload this folder to GitHub.
2. Create a new Railway project.
3. Connect the GitHub repository.
4. Add Railway Variables listed above.
5. Deploy.
6. Open Telegram and send `/start` to the bot.

## Notes

- The bot uses SQLite by default.
- Random codes are generated for testing only.
- For real production, replace random generation with real stock handling.
- Receipt images are generated as MD STORE receipts for order proof.
