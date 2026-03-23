from fastapi import APIRouter, HTTPException,Depends
from .schemas import LoginIn,TelegramLoginIn
from security import verify_password, create_token
from db import login as db_login,telegram_login_db,get_default_branch_id,is_app_expired_db,get_app_expiry_db
from api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


def _assert_not_expired():
    if is_app_expired_db():
        expires_at = get_app_expiry_db()
        expiry_text = expires_at.strftime("%Y-%m-%d %H:%M:%S") if expires_at else "unknown"
        raise HTTPException(
            status_code=403,
            detail=f"Application access expired on {expiry_text}. Please contact root admin."
        )

@router.get("/me")
def me(user=Depends(get_current_user)):
    with open("/tmp/backend_auth_me.log", "a") as f:
        f.write(f"[ /auth/me CALLED | user={user}\n")
    default_branch = get_default_branch_id(user["user_id"])
    return {
        "id": user["user_id"],
        "is_admin": user["is_admin"],
        "branch_id": default_branch or user.get("branch_id"),
        "language": user.get("language") or "ru"
    }

@router.post("/login")
def login(data: LoginIn):
    _assert_not_expired()
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
    _assert_not_expired()

    u = telegram_login_db(data.telegram_id)

    if not u:
        # AUTO CREATE USER (VERY IMPORTANT)

        raise HTTPException(
            status_code=401,
            detail="User is not registered. Please contact administrator."
        )
    else:
        user_id = u["id"]
        is_admin = u["is_admin"]

    default_branch = get_default_branch_id(user_id)

    token = create_token({
        "user_id": user_id,
        "is_admin": is_admin,
        "branch_id": default_branch,
        "language": u["language"] or "ru",
        "telegram_id": data.telegram_id
    })

    return {
        "access_token": token,
        "user_id": user_id,
        "is_admin": is_admin,
        "telegram_id": data.telegram_id
    }

