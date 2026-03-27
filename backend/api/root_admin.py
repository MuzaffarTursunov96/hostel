from fastapi import APIRouter, Depends, HTTPException
from api.deps import get_current_user, is_root_admin
from datetime import datetime
import importlib.util
import pathlib
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
    get_system_setting_db,
    set_system_setting_db,
)


router = APIRouter(prefix="/root", tags=["Root Admin"])


def _load_debt_cron_run():
    cron_path = pathlib.Path(__file__).resolve().parents[2] / "cron" / "notify_debts.py"
    if not cron_path.exists():
        raise RuntimeError(f"Cron script not found: {cron_path}")

    spec = importlib.util.spec_from_file_location("hostel_cron_notify_debts", str(cron_path))
    if not spec or not spec.loader:
        raise RuntimeError("Failed to load cron module spec")

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "run"):
        raise RuntimeError("Cron script missing run()")
    return mod.run

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


@router.get("/cron/debt-notify")
def get_debt_notify_cron_config(current_user=Depends(get_current_user)):
    if not is_root_admin(current_user):
        raise HTTPException(403, "Root admin only")

    enabled = str(get_system_setting_db("debt_notify_enabled", "1")).strip().lower() in {"1", "true", "yes", "on"}
    force = str(get_system_setting_db("debt_notify_force", "0")).strip().lower() in {"1", "true", "yes", "on"}
    return {
        "enabled": enabled,
        "force_next_run": force,
    }


@router.post("/cron/debt-notify")
def set_debt_notify_cron_config(data: dict, current_user=Depends(get_current_user)):
    if not is_root_admin(current_user):
        raise HTTPException(403, "Root admin only")

    if "enabled" in data:
        set_system_setting_db("debt_notify_enabled", "1" if bool(data.get("enabled")) else "0")
    if "force_next_run" in data:
        set_system_setting_db("debt_notify_force", "1" if bool(data.get("force_next_run")) else "0")

    enabled = str(get_system_setting_db("debt_notify_enabled", "1")).strip().lower() in {"1", "true", "yes", "on"}
    force = str(get_system_setting_db("debt_notify_force", "0")).strip().lower() in {"1", "true", "yes", "on"}
    return {"ok": True, "enabled": enabled, "force_next_run": force}


@router.post("/cron/debt-notify/test")
def test_run_debt_notify_cron(data: dict | None = None, current_user=Depends(get_current_user)):
    if not is_root_admin(current_user):
        raise HTTPException(403, "Root admin only")

    payload = data or {}
    force = bool(payload.get("force", True))
    try:
        run_fn = _load_debt_cron_run()
        result = run_fn(force=force)
    except Exception as e:
        raise HTTPException(500, f"Cron test failed: {e}")

    return {"ok": True, "result": result or {}}
