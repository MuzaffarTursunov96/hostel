from fastapi import APIRouter, Depends, HTTPException
from api.deps import get_current_user, is_root_admin
from datetime import datetime
from db import (
    set_admin_branches_db,
    create_admin_from_root,
    reset_password_db,
    list_admins_db,
    set_admin_active_db,
    get_admin_db,
    delete_admin_db,
    create_branch_db,
    delete_branch_db,
    list_branches_db_root,
    list_branches_db,
    set_app_expiry_db,
    get_app_expiry_db,
    set_admin_expiry_db,
)


router = APIRouter(prefix="/root", tags=["Root Admin"])

@router.post("/admins")
def create_admin(
            data: dict,
            current_user=Depends(get_current_user)
        ):
    if not is_root_admin(current_user):
        raise HTTPException(403, "Root admin only")

    telegram_id = data.get("telegram_id")
    username = data.get("username")
    password = data.get("password")

    if not telegram_id or not password:
        raise HTTPException(400, "telegram_id and password required")


    user_stat = create_admin_from_root(telegram_id, username, password,True)
    
    if user_stat['status'] =='error':
        raise HTTPException(400, user_stat.get("message", "Admin already exists"))

    return {"ok": True}

@router.post("/admins/{user_id}/branches")
def set_admin_branches(
            user_id: int,
            data: dict,
            current_user=Depends(get_current_user)
        ):
    
    if not is_root_admin(current_user):
        raise HTTPException(403, "Root admin only")

    branch_ids = data.get("branch_ids", [])
    set_admin_branches_db(user_id, branch_ids)

    return {"ok": True}


@router.post("/admins/{user_id}/password")
def reset_password(
    user_id: int,
    data: dict,
    current_user=Depends(get_current_user)
):
    if not is_root_admin(current_user):
        raise HTTPException(403, "Root admin only")

    new_password = data.get("password")
    if not new_password:
        raise HTTPException(400, "password required")

    try:
        reset_password_db(new_password, user_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    return {"ok": True}



@router.get("/admins")
def list_admins(current_user=Depends(get_current_user)):
    if not is_root_admin(current_user):
        raise HTTPException(403, "Root admin only")

    return list_admins_db()


@router.post("/admins/{user_id}/set-active")
def set_admin_active(
    user_id: int,
    data: dict,
    current_user=Depends(get_current_user)
):
    if not is_root_admin(current_user):
        raise HTTPException(403, "Root admin only")

    is_active = int(bool(data.get("is_active", 0)))

    set_admin_active_db(user_id, is_active)

    return {"ok": True}


@router.get("/admins/{user_id}")
def get_admin(user_id: int, current_user=Depends(get_current_user)):
    if not is_root_admin(current_user):
        raise HTTPException(403, "Root admin only")

    admin_stat = get_admin_db(user_id)

    if admin_stat['status'] =='error':
        raise HTTPException(404, "Admin not found")

    

    return admin_stat


@router.delete("/admins/{user_id}")
def delete_admin(
    user_id: int,
    current_user=Depends(get_current_user)
):
    if not is_root_admin(current_user):
        raise HTTPException(403, "Root admin only")

    # prevent deleting yourself
    if user_id == current_user["user_id"]:
        raise HTTPException(400, "You cannot delete yourself")

    delete_admin_db(user_id)

    return {"ok": True}


@router.post("/branches")
def create_branch(data: dict, current_user=Depends(get_current_user)):
    if not is_root_admin(current_user):
        raise HTTPException(403)

    name = data.get("name")
    if not name:
        raise HTTPException(400, "name required")

    branch_id = create_branch_db(name , current_user["user_id"])

    return {"id": branch_id, "name": name}



@router.delete("/branches/{branch_id}")
def delete_branch(
    branch_id: int,
    current_user=Depends(get_current_user)
):
    if not is_root_admin(current_user):
        raise HTTPException(403)

    branch_stat = delete_branch_db(branch_id)
    if branch_stat['status'] =='error':
        raise HTTPException(400, "Branch has bookings")

    return {"ok": True}

@router.get("/branches")
def list_branches(user=Depends(get_current_user)):
    if is_root_admin(user):
        # 🔥 ROOT SEES ALL
        rows = list_branches_db_root()
    else:
        rows = list_branches_db(user["user_id"])

    

    return [{"id": r["id"], "name": r["name"]} for r in rows]


@router.get("/system-expiry")
def get_system_expiry(current_user=Depends(get_current_user)):
    if not is_root_admin(current_user):
        raise HTTPException(403, "Root admin only")

    expires_at = get_app_expiry_db()
    return {
        "expires_at": expires_at.isoformat() if expires_at else None
    }


@router.post("/system-expiry")
def set_system_expiry(data: dict, current_user=Depends(get_current_user)):
    if not is_root_admin(current_user):
        raise HTTPException(403, "Root admin only")

    raw = data.get("expires_at")
    if raw in (None, "", "null"):
        set_app_expiry_db(None)
        return {"ok": True, "expires_at": None}

    try:
        expires_at = datetime.fromisoformat(raw)
    except ValueError:
        raise HTTPException(400, "Invalid datetime format. Use ISO format.")

    set_app_expiry_db(expires_at)
    return {"ok": True, "expires_at": expires_at.isoformat()}


@router.post("/admins/{user_id}/expiry")
def set_admin_expiry(user_id: int, data: dict, current_user=Depends(get_current_user)):
    if not is_root_admin(current_user):
        raise HTTPException(403, "Root admin only")

    raw = data.get("expires_at")
    if raw in (None, "", "null"):
        set_admin_expiry_db(user_id, None)
        return {"ok": True, "expires_at": None}

    try:
        expires_at = datetime.fromisoformat(raw)
    except ValueError:
        raise HTTPException(400, "Invalid datetime format. Use ISO format.")

    set_admin_expiry_db(user_id, expires_at)
    return {"ok": True, "expires_at": expires_at.isoformat()}
