from aiogram import Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import CommandStart
import os
from dotenv import load_dotenv

load_dotenv()

MINI_APP_URL = os.getenv("MINI_APP_URL")

router = Router()


@router.message(CommandStart())
async def start(message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏨 HMS tizimiga kirish",
                    web_app=WebAppInfo(url=MINI_APP_URL)
                )
            ]
        ]
    )

    await message.answer(
        (
            "👋 <b>HMS — Hotel Management System</b>\n\n"
            "Ushbu bot orqali mehmonxonangizni qulay va tez boshqarishingiz mumkin:\n"
            "• Xonalar va yotoqlar holati\n"
            "• Bron va joylashtirish\n"
            "• To‘lovlar va hisobotlar\n"
            "• Foydalanuvchi va filiallar\n\n"
            "👇 Davom etish uchun quyidagi tugmani bosing:"
        ),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
