from fastapi import APIRouter, Depends, HTTPException
from api.deps import get_current_user
from db import get_branches, add_branch, update_branch
from api.ws_manager import ws_manager

router = APIRouter(prefix="/branches", tags=["Branches"])


@router.get("/")
def list_branches(user=Depends(get_current_user)):
    """
    Used by WEB + DESKTOP (via API)
    """
    return get_branches(user["user_id"])


@router.post("/")
def create_branch(data: dict, user=Depends(get_current_user)):
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(400, "Branch name required")

    branch_id = add_branch(name, user["user_id"])
    return {
        "id": branch_id,
        "name": name
    }


@router.post("/update")
async def rename_branch(data: dict, user=Depends(get_current_user)):
    branch_id = data.get("branch_id")
    name = data.get("name", "").strip()

    if not branch_id or not name:
        raise HTTPException(400, "Invalid data")

    update_branch(branch_id, name, user["user_id"])

    await ws_manager.broadcast({
        "type": "branches_changed",
        "branch_id": branch_id
    })

    return {"success": True}

