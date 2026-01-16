from fastapi import APIRouter, Depends, HTTPException
from api.deps import get_current_user
from db import change_password_db, set_lang_db
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
