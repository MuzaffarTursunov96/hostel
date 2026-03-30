import asyncio
import os
from aiogram import Bot

BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip()
WEBHOOK_URL = (os.getenv("WEBHOOK_URL") or "").strip()
CLIENT_BOT_TOKEN = (os.getenv("CLIENT_BOT_TOKEN") or "").strip()
CLIENT_WEBHOOK_URL = (os.getenv("CLIENT_WEBHOOK_URL") or "").strip()


async def main():
    if BOT_TOKEN and WEBHOOK_URL:
        bot = Bot(token=BOT_TOKEN)
        await bot.set_webhook(WEBHOOK_URL)
        print("Admin webhook set:", WEBHOOK_URL)
        await bot.session.close()
    else:
        print("Admin webhook skipped: BOT_TOKEN/WEBHOOK_URL missing")

    if CLIENT_BOT_TOKEN:
        url = CLIENT_WEBHOOK_URL
        if not url and WEBHOOK_URL:
            url = WEBHOOK_URL.replace("/tg/webhook", "/tg/client-webhook")

        if url:
            cbot = Bot(token=CLIENT_BOT_TOKEN)
            await cbot.set_webhook(url)
            print("Client webhook set:", url)
            await cbot.session.close()
        else:
            print("Client webhook skipped: CLIENT_WEBHOOK_URL missing")
    else:
        print("Client webhook skipped: CLIENT_BOT_TOKEN missing")


asyncio.run(main())
