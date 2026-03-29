from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
import os
from .schemas import LoginIn, TelegramLoginIn
from security import verify_password, create_token
from db import (
    login as db_login,
    telegram_login_db,
    get_default_branch_id,
    get_app_expiry_db,
    sync_admin_active_by_expiry_db,
    create_admin_if_not_exists,
)
from api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])

ROOT_ADMIN_TELEGRAM = os.getenv("ROOT_ADMIN_TELEGRAM", "muzaffar_developer")
ROOT_ADMIN_PHONE = os.getenv("ROOT_ADMIN_PHONE", "+998991422110")
ROOT_TELEGRAM_ID = int(os.getenv("ROOT_TELEGRAM_ID", "1343842535"))


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
        f"РЎРІСЏР¶РёС‚РµСЃСЊ СЃ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂРѕРј:\n"
        f"Telegram: @{ROOT_ADMIN_TELEGRAM}\n"
        f"РўРµР»РµС„РѕРЅ: {ROOT_ADMIN_PHONE}"
    )


def _assert_not_expired(lang_hint="ru"):
    expires_at = get_app_expiry_db()
    lang = _lang_code(lang_hint)

    # Block login if expiry is not configured (None)
    if not expires_at:
        msg = (
            "РЎСЂРѕРє РґРѕСЃС‚СѓРїР° РЅРµ РЅР°СЃС‚СЂРѕРµРЅ. Р’С…РѕРґ РІСЂРµРјРµРЅРЅРѕ Р·Р°РїСЂРµС‰РµРЅ.\n\n"
            if lang == "ru"
            else "Muddat sozlanmagan. Kirish vaqtincha taqiqlangan.\n\n"
        )
        raise HTTPException(status_code=403, detail=msg + _contact_block(lang))

    # Block login if expired
    if datetime.utcnow() > expires_at:
        expiry_text = expires_at.strftime("%Y-%m-%d %H:%M:%S")
        msg = (
            f"РЎСЂРѕРє РґРѕСЃС‚СѓРїР° РёСЃС‚РµРє: {expiry_text}.\n\n"
            if lang == "ru"
            else f"Kirish muddati tugagan: {expiry_text}.\n\n"
        )
        raise HTTPException(status_code=403, detail=msg + _contact_block(lang))


def _is_root_user(u):
    try:
        return bool(u) and int(u.get("telegram_id") or 0) == ROOT_TELEGRAM_ID and bool(u.get("is_admin"))
    except Exception:
        return False


def _is_admin_user(u):
    try:
        return bool(u) and bool(u.get("is_admin"))
    except Exception:
        return False


def _assert_user_not_expired(u):
    expires_at = u.get("admin_expires_at") if isinstance(u, dict) else None
    if not expires_at:
        return
    if isinstance(expires_at, str):
        try:
            expires_at = datetime.fromisoformat(expires_at)
        except Exception:
            return
    if datetime.utcnow() > expires_at:
        lang = _lang_code(u.get("language") if isinstance(u, dict) else "ru")
        msg = (
            f"РЎСЂРѕРє РґРµР№СЃС‚РІРёСЏ РІР°С€РµР№ СѓС‡РµС‚РЅРѕР№ Р·Р°РїРёСЃРё Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР° РёСЃС‚РµРє: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}.\n\n"
            if lang == "ru"
            else f"Admin hisobingiz muddati tugagan: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}.\n\n"
        )
        raise HTTPException(status_code=403, detail=msg + _contact_block(lang))


def _assert_parent_admin_not_blocked(u):
    if not isinstance(u, dict):
        return
    # If this account belongs to an admin and that admin is blocked -> block this user too
    if u.get("created_by") and u.get("creator_is_active") is False:
        lang = _lang_code(u.get("language") or "ru")
        msg = (
            "Р’Р°С€ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂ Р·Р°Р±Р»РѕРєРёСЂРѕРІР°РЅ. Р”РѕСЃС‚СѓРї РІСЂРµРјРµРЅРЅРѕ Р·Р°РїСЂРµС‰РµРЅ.\n\n"
            if lang == "ru"
            else "Adminingiz bloklangan. Kirish vaqtincha taqiqlangan.\n\n"
        )
        raise HTTPException(status_code=403, detail=msg + _contact_block(lang))


@router.get("/me")
def me(user=Depends(get_current_user)):
    with open("/tmp/backend_auth_me.log", "a") as f:
        f.write(f"[ /auth/me CALLED | user={user}\n")
    default_branch = get_default_branch_id(user["user_id"])
    return {
        "id": user["user_id"],
        "is_admin": user["is_admin"],
        "branch_id": default_branch or user.get("branch_id"),
        "language": user.get("language") or "ru",
    }


@router.post("/login")
def login(data: LoginIn):
    sync_admin_active_by_expiry_db(ROOT_TELEGRAM_ID)
    u = db_login(data.username)
    # Global/system expiry applies to non-admin users only.
    # Admins are controlled by admin_expires_at.
    if not _is_root_user(u) and not _is_admin_user(u):
        _assert_not_expired((u or {}).get("language", "ru"))
    _assert_parent_admin_not_blocked(u)

    if not u or not verify_password(data.password, u["password_hash"]):
        # Default language is Russian. If user exists, use their saved language.
        lang = (u.get("language") if isinstance(u, dict) else None) or "ru"
        msg = "РќРµРІРµСЂРЅС‹Р№ Р»РѕРіРёРЅ РёР»Рё РїР°СЂРѕР»СЊ."
        if str(lang).lower().startswith("uz"):
            msg = "Login yoki parol noto'g'ri."
        raise HTTPException(401, msg)
    _assert_user_not_expired(u)

    default_branch = get_default_branch_id(u["id"])

    token = create_token(
        {
            "user_id": u["id"],
            "is_admin": u["is_admin"],
            "branch_id": default_branch or u["branch_id"],
            "language": u["language"] or "ru",
            "telegram_id": u["telegram_id"],
        }
    )

    return {
        "access_token": token,
        "user_id": u["id"],
        "is_admin": u["is_admin"],
        "branch_id": default_branch or u["branch_id"],
        "language": u["language"] or "ru",
        "telegram_id": u["telegram_id"],
    }


@router.post("/telegram")
def telegram_login(data: TelegramLoginIn):
    sync_admin_active_by_expiry_db(ROOT_TELEGRAM_ID)
    u = telegram_login_db(data.telegram_id)

    # Global/system expiry applies to non-admin users only.
    # Admins are controlled by admin_expires_at.
    if not (u and _is_root_user(u)) and int(data.telegram_id) != ROOT_TELEGRAM_ID and not _is_admin_user(u):
        _assert_not_expired((u or {}).get("language", "ru"))
    _assert_parent_admin_not_blocked(u)

    # Root admin must always be able to log in by Telegram ID.
    if not u and int(data.telegram_id) == ROOT_TELEGRAM_ID:
        create_admin_if_not_exists()
        u = telegram_login_db(data.telegram_id)

    if not u:
        raise HTTPException(
            status_code=401,
            detail="User is not registered. Please contact admin.",
        )

    _assert_user_not_expired(u)
    user_id = u["id"]
    is_admin = u["is_admin"]
    branch_id = get_default_branch_id(user_id) or u.get("branch_id")

    token = create_token(
        {
            "user_id": user_id,
            "is_admin": is_admin,
            "branch_id": branch_id,
            "language": u["language"] or "ru",
            "telegram_id": data.telegram_id,
        }
    )

    return {
        "access_token": token,
        "user_id": user_id,
        "is_admin": is_admin,
        "branch_id": branch_id,
        "language": u["language"] or "ru",
        "telegram_id": data.telegram_id,
    }
