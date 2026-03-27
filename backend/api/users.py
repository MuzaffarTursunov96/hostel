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
    get_user_db,
    get_user_preferences_db,
    upsert_user_device_token_db,
    remove_user_device_token_db,
    list_user_notifications_db,
    mark_notification_read_db,
    mark_all_notifications_read_db,
    get_unread_notification_count_db,
    delete_notification_db,
    delete_read_notifications_db,
    delete_all_notifications_db
)

def require_admin(user):
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin only")

router = APIRouter(prefix="/users", tags=["Users"])



@router.get("/me/preferences")
def get_user_preferences(user=Depends(get_current_user)):
    row = get_user_preferences_db(user["user_id"])
    return {
        "language": row["language"] or "ru",
        "notify_enabled": row["notify_enabled"]
    }


@router.post("")
def create_user(data: dict, current_user=Depends(get_current_user)):
    require_admin(current_user)

    username = data.get("username")
    password = data.get("password")
    telegram_id = data.get("telegram_id")

    if not username or not password or not telegram_id:
        raise HTTPException(400, "username, password and telegram_id required")

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

    try:
        ok = reset_password_db(password, user_id, current_user["user_id"])
    except ValueError as exc:
        raise HTTPException(400, str(exc))
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

    try:
        ok = update_user_by_admin_db(
            admin_id=current_user["user_id"],
            user_id=user_id,
            username=username,
            telegram_id=telegram_id,
            is_active=is_active
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))

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


@router.post("/me/device-token")
def register_my_device_token(data: dict, user=Depends(get_current_user)):
    fcm_token = str(data.get("fcm_token") or "").strip()
    platform = str(data.get("platform") or "").strip().lower()

    if not fcm_token:
        raise HTTPException(400, "fcm_token required")
    if platform and platform not in ("android", "ios"):
        raise HTTPException(400, "platform must be android or ios")

    ok = upsert_user_device_token_db(
        user_id=user["user_id"],
        fcm_token=fcm_token,
        platform=platform or None
    )
    if not ok:
        raise HTTPException(400, "Invalid fcm_token")

    return {"ok": True}


@router.delete("/me/device-token")
def remove_my_device_token(data: dict | None = None, user=Depends(get_current_user)):
    payload = data or {}
    fcm_token = str(payload.get("fcm_token") or "").strip() or None
    remove_user_device_token_db(user_id=user["user_id"], fcm_token=fcm_token)
    return {"ok": True}


@router.get("/me/notifications")
def my_notifications(
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    user=Depends(get_current_user)
):
    rows = list_user_notifications_db(
        user_id=user["user_id"],
        unread_only=bool(unread_only),
        limit=limit,
        offset=offset
    )
    unread_count = get_unread_notification_count_db(user["user_id"])
    return {"items": rows, "unread_count": unread_count}


@router.post("/me/notifications/{notification_id}/read")
def mark_my_notification_read(notification_id: int, user=Depends(get_current_user)):
    ok = mark_notification_read_db(user_id=user["user_id"], notification_id=notification_id)
    if not ok:
        raise HTTPException(404, "Notification not found")
    return {"ok": True}


@router.post("/me/notifications/read-all")
def mark_all_my_notifications_read(user=Depends(get_current_user)):
    updated = mark_all_notifications_read_db(user_id=user["user_id"])
    return {"ok": True, "updated": updated}


@router.delete("/me/notifications/{notification_id}")
def delete_my_notification(notification_id: int, user=Depends(get_current_user)):
    ok = delete_notification_db(
        user_id=user["user_id"],
        notification_id=notification_id
    )
    if not ok:
        raise HTTPException(404, "Notification not found")
    return {"ok": True}


@router.delete("/me/notifications/read")
def delete_my_read_notifications(user=Depends(get_current_user)):
    deleted = delete_read_notifications_db(user_id=user["user_id"])
    return {"ok": True, "deleted": deleted}


@router.delete("/me/notifications")
def delete_my_all_notifications(user=Depends(get_current_user)):
    deleted = delete_all_notifications_db(user_id=user["user_id"])
    return {"ok": True, "deleted": deleted}


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
