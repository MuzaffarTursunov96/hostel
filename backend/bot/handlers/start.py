from aiogram import Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import os
from aiogram.filters import CommandStart
from dotenv import load_dotenv
load_dotenv()


MINI_APP_URL = os.getenv("MINI_APP_URL")

router = Router()

@router.message(CommandStart())
async def start(message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🏨 Open Hostel App",
                web_app=WebAppInfo(
                    url=MINI_APP_URL
                )
            )
        ]
    ])

    await message.answer(
        "Open the app:",
        reply_markup=kb
    )