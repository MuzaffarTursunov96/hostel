from fastapi import APIRouter, Depends, HTTPException
from api.deps import get_current_user
from db import (
    change_password_db,
    set_lang_db,
    set_user_branch_db,
    get_booking_prepayment_config_db,
    set_booking_prepayment_config_db,
)
from security import create_token

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.post("/change-password")
def change_password(data: dict, user=Depends(get_current_user)):
    current_password = data.get("current_password")
    new_password = data.get("new_password")


    if not current_password or not new_password:
        raise HTTPException(status_code=400, detail="Invalid data")

    user_pass_change_stats = change_password_db(user["user_id"], current_password, new_password)
   

    if user_pass_change_stats['status'] =='error':
        raise HTTPException(status_code=400, detail=user_pass_change_stats['message'])

    return {"ok": True}


@router.post("/set-branch")
def set_branch(
    data: dict,
    user=Depends(get_current_user)
):
    branch_id = data.get("branch_id")
    if not branch_id:
        raise HTTPException(400, "branch_id required")

    set_user_branch_db(user["user_id"], int(branch_id))
    # 🔐 issue new token with updated branch
    new_token = create_token({
        "user_id": user["user_id"],
        "is_admin": user["is_admin"],
        "branch_id": int(branch_id),
        "language": user.get("language", "ru")
    })

    return {"access_token": new_token}

@router.post("/language")
def set_language(data: dict, user=Depends(get_current_user)):
    lang = data.get("language", "ru")

    set_lang_db(user["user_id"], lang)

    # 🔥 ISSUE NEW TOKEN WITH UPDATED LANGUAGE
    new_token = create_token({
        "user_id": user["user_id"],
        "is_admin": user["is_admin"],
        "branch_id": user.get("branch_id"),
        "language": lang
    })

    return {
        "access_token": new_token,
        "language": lang
    }


@router.get("/me")
def me(user=Depends(get_current_user)):
    return {
        "branch_id": user.get("branch_id") or 1,
        "language": user.get("language") or "ru"
    }


@router.get("/booking-prepayment")
def get_booking_prepayment(user=Depends(get_current_user)):
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin only")
    return get_booking_prepayment_config_db()


@router.post("/booking-prepayment")
def set_booking_prepayment(data: dict, user=Depends(get_current_user)):
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin only")

    enabled = bool(data.get("enabled", False))
    mode = str(data.get("mode", "percent"))
    value = data.get("value", 0)

    try:
        set_booking_prepayment_config_db(enabled, mode, float(value))
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    return {"ok": True, **get_booking_prepayment_config_db()}
