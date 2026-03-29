from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from jose import jwt, JWTError
from security import SECRET_KEY, ALGORITHM
from datetime import datetime
from db import get_user_auth_state_db, get_app_expiry_db, sync_admin_active_by_expiry_db

import os
from dotenv import load_dotenv

load_dotenv()
ROOT_TELEGRAM_ID = int(os.getenv("ROOT_TELEGRAM_ID", "1343842535"))
ROOT_ADMIN_TELEGRAM = os.getenv("ROOT_ADMIN_TELEGRAM", "muzaffar_developer")
ROOT_ADMIN_PHONE = os.getenv("ROOT_ADMIN_PHONE", "+998991422110")

security = HTTPBearer()


def _lang_code(lang_hint):
    return "uz" if str(lang_hint or "ru").lower().startswith("uz") else "ru"


def _contact_block(lang_hint="ru"):
    if _lang_code(lang_hint) == "uz":
        return (
            f"Admin bilan bog'laning:\n"
            f"Telegram: @{ROOT_ADMIN_TELEGRAM}\n"
            f"Telefon: {ROOT_ADMIN_PHONE}"
        )
    return (
        f"Свяжитесь с администратором:\n"
        f"Telegram: @{ROOT_ADMIN_TELEGRAM}\n"
        f"Телефон: {ROOT_ADMIN_PHONE}"
    )


def _is_root(user_row):
    try:
        return bool(user_row) and bool(user_row.get("is_admin")) and int(user_row.get("telegram_id") or 0) == ROOT_TELEGRAM_ID
    except Exception:
        return False


def get_current_user(token=Depends(security)):
    sync_admin_active_by_expiry_db(ROOT_TELEGRAM_ID)
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("user_id")
    user_row = get_user_auth_state_db(user_id) if user_id else None
    lang = _lang_code((user_row or {}).get("language") or payload.get("language") or "ru")

    if not user_row or not bool(user_row.get("is_active")):
        msg = "Ваш доступ заблокирован. " if lang == "ru" else "Sizning kirishingiz bloklangan. "
        raise HTTPException(status_code=403, detail=msg + _contact_block(lang))

    # If parent admin is blocked, child users are also blocked
    if user_row.get("created_by") and user_row.get("creator_is_active") is False:
        msg = (
            "Ваш администратор заблокирован. Доступ временно запрещен.\n\n"
            if lang == "ru"
            else "Adminingiz bloklangan. Kirish vaqtincha taqiqlangan.\n\n"
        )
        raise HTTPException(status_code=403, detail=msg + _contact_block(lang))

    if not _is_root(user_row) and not bool(user_row.get("is_admin")):
        expires_at = get_app_expiry_db()
        if not expires_at:
            msg = "Срок доступа не настроен. Вход запрещен.\n\n" if lang == "ru" else "Muddat sozlanmagan. Kirish taqiqlangan.\n\n"
            raise HTTPException(status_code=403, detail=msg + _contact_block(lang))
        if datetime.utcnow() > expires_at:
            msg = (
                f"Срок доступа истек: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}.\n\n"
                if lang == "ru"
                else f"Kirish muddati tugagan: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}.\n\n"
            )
            raise HTTPException(status_code=403, detail=msg + _contact_block(lang))

    # Admin expiry applies only to the admin account itself
    admin_expires_at = user_row.get("admin_expires_at")
    if bool(user_row.get("is_admin")) and admin_expires_at and datetime.utcnow() > admin_expires_at and not _is_root(user_row):
        msg = (
            f"Срок действия учетной записи администратора истек: {admin_expires_at.strftime('%Y-%m-%d %H:%M:%S')}.\n\n"
            if lang == "ru"
            else f"Admin hisob muddati tugagan: {admin_expires_at.strftime('%Y-%m-%d %H:%M:%S')}.\n\n"
        )
        raise HTTPException(status_code=403, detail=msg + _contact_block(lang))

    return payload


def admin_required(user=Depends(get_current_user)):
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    return user


def is_root_admin(user):
    return user["is_admin"] == 1 and user["telegram_id"] == ROOT_TELEGRAM_ID


def is_admin(user):
    return user["is_admin"] == 1
