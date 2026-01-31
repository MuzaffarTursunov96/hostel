from fastapi import APIRouter, Depends, HTTPException
from api.deps import get_current_user
from db import (
    create_user_db,
    list_users_by_admin_db,
    delete_user_by_admin_db,
    reset_password_db,
    update_user_by_admin_db,
    list_user_branches_db,
    set_my_notifications_db,
    admin_set_user_notify_db,
    get_user_db
)

def require_admin(user):
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin only")

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("")
def create_user(data: dict, current_user=Depends(get_current_user)):
    require_admin(current_user)

    username = data.get("username")
    password = data.get("password")
    telegram_id = data.get("telegram_id")

    if not username or not password:
        raise HTTPException(400, "username and password required")

    user = create_user_db(
        username=username,
        password=password,
        telegram_id=telegram_id,
        created_by=current_user["user_id"]  # 🔥 OWNERSHIP
    )

    if user["status"] == "error":
        raise HTTPException(400, user["message"])

    return {"ok": True, "user_id": user["id"]}

@router.get("")
def list_users(current_user=Depends(get_current_user)):
    require_admin(current_user)
    return list_users_by_admin_db(current_user["user_id"])

@router.delete("/{user_id}")
def delete_user(user_id: int, current_user=Depends(get_current_user)):
    require_admin(current_user)

    ok = delete_user_by_admin_db(
        user_id=user_id,
        admin_id=current_user["user_id"]
    )

    if not ok:
        raise HTTPException(403, "You can delete only your own users")

    return {"ok": True}

@router.post("/{user_id}/password")
def reset_user_password(
    user_id: int,
    data: dict,
    current_user=Depends(get_current_user)
):
    require_admin(current_user)

    password = data.get("password")
    if not password:
        raise HTTPException(400, "password required")

    ok = reset_password_db(password, user_id, current_user["user_id"])
    if not ok:
        raise HTTPException(403, "Not your user")

    return {"ok": True}


@router.put("/{user_id}")
def update_user(
    user_id: int,
    data: dict,
    current_user=Depends(get_current_user)
):
    require_admin(current_user)

    username = data.get("username")
    telegram_id = data.get("telegram_id")
    is_active = data.get("is_active")

    ok = update_user_by_admin_db(
        admin_id=current_user["user_id"],
        user_id=user_id,
        username=username,
        telegram_id=telegram_id,
        is_active=is_active
    )

    if not ok:
        raise HTTPException(403, "Not your user")

    return {"ok": True}


@router.get("/{user_id}/branches")
def get_user_branches(
    user_id: int,
    current_user=Depends(get_current_user)
):
    if not current_user.get("is_admin"):
        raise HTTPException(403, "Admin only")

    return list_user_branches_db(
        admin_id=current_user["user_id"],
        user_id=user_id
    )

@router.post("/me/notify")
def set_my_notifications(data: dict, user=Depends(get_current_user)):
    enabled = bool(data.get("enabled", True))

    set_my_notifications_db(enabled, user["user_id"])

    return {"ok": True}


@router.post("/admin/users/{user_id}/notify")
def admin_set_user_notify(
        user_id: int,
        data: dict,
        current_user=Depends(get_current_user)
    ):
    require_admin(current_user)
    enabled = bool(data.get("enabled", True))
    
    admin_set_user_notify_db(enabled,user_id,current_user["user_id"])
    

    return {"ok": True}


@router.get("/{user_id}")
def get_user(
        user_id: int,
        current_user=Depends(get_current_user)
    ):
    require_admin(current_user)

    u = get_user_db(user_id, current_user["user_id"])
    

    if not u:
        raise HTTPException(404, "User not found")

    return u
