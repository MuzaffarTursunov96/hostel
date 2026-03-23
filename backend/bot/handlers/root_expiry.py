from datetime import datetime
import os
from dotenv import load_dotenv

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

try:
    from db import set_app_expiry_db, get_app_expiry_db
    EXPIRY_SUPPORT = True
except Exception:
    set_app_expiry_db = None
    get_app_expiry_db = None
    EXPIRY_SUPPORT = False

load_dotenv()
ROOT_TELEGRAM_ID = int(os.getenv("ROOT_TELEGRAM_ID", "0"))

router = Router()


def _is_root(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id == ROOT_TELEGRAM_ID)


def _feature_unavailable_text() -> str:
    return (
        "Expiry feature is not available on this server build. "
        "Please update backend db.py and restart backend."
    )


@router.message(Command("getexpiry"))
async def get_expiry_cmd(message: Message):
    if not _is_root(message):
        await message.answer("Not allowed.")
        return
    if not EXPIRY_SUPPORT:
        await message.answer(_feature_unavailable_text())
        return

    expires_at = get_app_expiry_db()
    if not expires_at:
        await message.answer("App expiry is not set.")
        return

    await message.answer(
        f"App expiry is set to: {expires_at.strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )


@router.message(Command("clearexpiry"))
async def clear_expiry_cmd(message: Message):
    if not _is_root(message):
        await message.answer("Not allowed.")
        return
    if not EXPIRY_SUPPORT:
        await message.answer(_feature_unavailable_text())
        return

    set_app_expiry_db(None)
    await message.answer("App expiry cleared.")


@router.message(Command("setexpiry"))
async def set_expiry_cmd(message: Message):
    if not _is_root(message):
        await message.answer("Not allowed.")
        return
    if not EXPIRY_SUPPORT:
        await message.answer(_feature_unavailable_text())
        return

    # Expected: /setexpiry 2026-12-31
    parts = (message.text or "").strip().split()
    if len(parts) != 2:
        await message.answer("Usage: /setexpiry YYYY-MM-DD")
        return

    raw_date = parts[1]
    try:
        d = datetime.strptime(raw_date, "%Y-%m-%d")
    except ValueError:
        await message.answer("Invalid date. Use format: YYYY-MM-DD")
        return

    # Expire at end of chosen day (UTC)
    expires_at = datetime(d.year, d.month, d.day, 23, 59, 59)
    set_app_expiry_db(expires_at)

    await message.answer(
        f"App expiry saved: {expires_at.strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
