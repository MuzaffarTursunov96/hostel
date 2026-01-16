from fastapi import APIRouter, HTTPException,Depends
from .schemas import LoginIn,TelegramLoginIn
from security import verify_password, create_token
from db import login as db_login,telegram_login_db,user_auto_create,get_default_branch_id
from api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.get("/me")
def me(user=Depends(get_current_user)):
    default_branch = get_default_branch_id(user["user_id"])
    return {
        "id": user["user_id"],
        "is_admin": user["is_admin"],
        "branch_id": default_branch or user.get("branch_id"),
        "language": user.get("language") or "ru"
    }

@router.post("/login")
def login(data: LoginIn):
    u = db_login(data.username)

    if not u or not verify_password(data.password, u["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    
    default_branch = get_default_branch_id(u["id"])

    token = create_token({
        "user_id": u["id"],
        "is_admin": u["is_admin"],
        "branch_id": default_branch or u["branch_id"],
        "language": u["language"] or "ru",
        "telegram_id": u["telegram_id"]
    })


    return {
        "access_token": token,
        "user_id": u["id"],
        "is_admin": u["is_admin"],
        "branch_id":default_branch or u["branch_id"],
        "language": u["language"] or "ru",
        "telegram_id": u["telegram_id"]
    }

@router.post("/telegram")
def telegram_login(data: TelegramLoginIn):

    u = telegram_login_db(data.telegram_id)

    if not u:
        # AUTO CREATE USER (VERY IMPORTANT)

        user_id = user_auto_create(data.telegram_id, data.username)
        is_admin = 0
    else:
        user_id = u["id"]
        is_admin = u["is_admin"]

    default_branch = get_default_branch_id(user_id)

    token = create_token({
        "user_id": user_id,
        "is_admin": is_admin,
        "branch_id": default_branch or u["branch_id"],
        "language": u["language"] or "ru",
        "telegram_id": data.telegram_id
    })

    return {
        "access_token": token,
        "user_id": user_id,
        "is_admin": is_admin,
        "telegram_id": data.telegram_id
    }

