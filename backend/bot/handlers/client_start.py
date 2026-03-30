from aiogram import Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import CommandStart
import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_MINI_APP_URL = os.getenv("CLIENT_MINI_APP_URL", "").strip()
MINI_APP_URL = os.getenv("MINI_APP_URL", "").strip()


def _client_webapp_url() -> str:
    base = CLIENT_MINI_APP_URL or MINI_APP_URL or ""
    base = base.rstrip("/")
    if not base:
        return "https://hmsuz.com/catalog"
    if base.endswith("/catalog"):
        return base
    return f"{base}/catalog"


router = Router()


@router.message(CommandStart())
async def client_start(message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Open Hotel/Hostel Catalog",
                    web_app=WebAppInfo(url=_client_webapp_url())
                )
            ]
        ]
    )

    await message.answer(
        (
            "HMS Client Bot\n\n"
            "Use this mini app to:\n"
            "- find hotels/hostels\n"
            "- filter by type/rating/price\n"
            "- view photos and room details\n"
            "- send feedback and room reports\n\n"
            "Tap the button below to continue."
        ),
        reply_markup=keyboard
    )

