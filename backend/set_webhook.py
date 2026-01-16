import asyncio
import os
from aiogram import Bot

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

async def main():
    bot = Bot(token=BOT_TOKEN)
    await bot.set_webhook(WEBHOOK_URL)
    print("✅ Webhook set successfully")
    await bot.session.close()

asyncio.run(main())
