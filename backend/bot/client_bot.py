from aiogram import Bot
import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_BOT_TOKEN = os.getenv("CLIENT_BOT_TOKEN", "").strip()
client_bot = Bot(token=CLIENT_BOT_TOKEN) if CLIENT_BOT_TOKEN else None

