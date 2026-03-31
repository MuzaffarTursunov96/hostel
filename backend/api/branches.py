from fastapi import APIRouter, Depends, HTTPException
from api.deps import get_current_user
from db import (get_branches, 
                add_branch,
                update_branch,
                create_branch_db,
                assign_user_to_branch_db,
                list_branches_by_admin_db,
                update_branch_by_admin_db,
                delete_branch_by_admin_db,
                remove_user_from_branch_db,
                list_users_in_branch_db
                )

from api.ws_manager import ws_manager

router = APIRouter(prefix="/branches", tags=["Branches"])

def require_admin(user):
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin only")


@router.get("/")
def list_branches_user(user=Depends(get_current_user)):
    """
    Used by WEB + DESKTOP (via API)
    """
    return get_branches(user["user_id"])


@router.post("/")
def create_branch_root(data: dict, user=Depends(get_current_user)):
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








@router.post("/branches-admin")
def create_branch_admin(data: dict, current_user=Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(403, "Admin only")

    name = data.get("name")
    address = data.get("address", None)
    latitude = data.get("latitude", None)
    longitude = data.get("longitude", None)
    region_name = data.get("region_name", None)
    region_slug = data.get("region_slug", None)
    city_name = data.get("city_name", None)
    city_slug = data.get("city_slug", None)
    contact_phone = data.get("contact_phone", None)
    contact_telegram = data.get("contact_telegram", None)
    cover_image = data.get("cover_image", None)

    if not name:
        raise HTTPException(400, "name required")
    if not str(region_slug or "").strip() or not str(region_name or "").strip():
        raise HTTPException(400, "region required")
    if not str(city_name or "").strip() or not str(city_slug or "").strip():
        raise HTTPException(400, "city required")

    if latitude is None or longitude is None:
        raise HTTPException(400, "location required: latitude and longitude")
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        raise HTTPException(400, "invalid location: latitude/longitude must be numbers")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise HTTPException(400, "invalid location range")

    branch_id = create_branch_db(
        name=name,
        address=address,
        latitude=latitude,
        longitude=longitude,
        region_name=region_name,
        region_slug=region_slug,
        city_name=city_name,
        city_slug=city_slug,
        contact_phone=contact_phone,
        contact_telegram=contact_telegram,
        cover_image=cover_image,
        created_by=current_user["user_id"]
    )


    if branch_id is None:
        raise HTTPException(
            status_code=400,
            detail="Branch with this name already exists"
        )

    return {
        "ok": True,
        "branch_id": branch_id
    }


@router.post("/{branch_id}/assign-user")
def assign_user_to_branch(
    branch_id: int,
    data: dict,
    current_user=Depends(get_current_user)
):
    if not current_user.get("is_admin"):
        raise HTTPException(403, "Admin only")

    user_id = data.get("user_id")
    if not user_id:
        raise HTTPException(400, "user_id required")

    ok = assign_user_to_branch_db(
        admin_id=current_user["user_id"],
        user_id=user_id,
        branch_id=branch_id
    )

    if not ok:
        raise HTTPException(
            403,
            "You can assign only your users to your branches"
        )

    return {"ok": True}


@router.get("/admin")
def list_branches_admin(current_user=Depends(get_current_user)):
    require_admin(current_user)
    return list_branches_by_admin_db(current_user["user_id"])

@router.put("/admin/{branch_id}")
def update_branch(
        branch_id: int,
        data: dict,
        current_user=Depends(get_current_user)
    ):
    require_admin(current_user)

    name = data.get("name")
    address = data.get("address", None)
    latitude = data.get("latitude", None)
    longitude = data.get("longitude", None)
    region_name = data.get("region_name", None)
    region_slug = data.get("region_slug", None)
    city_name = data.get("city_name", None)
    city_slug = data.get("city_slug", None)
    contact_phone = data.get("contact_phone", None)
    contact_telegram = data.get("contact_telegram", None)
    cover_image = data.get("cover_image", None)

    if not name:
        raise HTTPException(400, "name required")
    if not str(region_slug or "").strip() or not str(region_name or "").strip():
        raise HTTPException(400, "region required")
    if not str(city_name or "").strip() or not str(city_slug or "").strip():
        raise HTTPException(400, "city required")

    ok = update_branch_by_admin_db(
        admin_id=current_user["user_id"],
        branch_id=branch_id,
        name=name,
        address=address,
        latitude=latitude,
        longitude=longitude,
        region_name=region_name,
        region_slug=region_slug,
        city_name=city_name,
        city_slug=city_slug,
        contact_phone=contact_phone,
        contact_telegram=contact_telegram,
        cover_image=cover_image
    )


    if not ok:
        raise HTTPException(403, "Not your branch")

    return {"ok": True}

@router.delete("/admin/{branch_id}")
def delete_branch(
    branch_id: int,
    current_user=Depends(get_current_user)
):
    require_admin(current_user)

    ok = delete_branch_by_admin_db(
        admin_id=current_user["user_id"],
        branch_id=branch_id
    )

    if not ok:
        raise HTTPException(403, "Not your branch or branch in use")

    return {"ok": True}

@router.delete("/{branch_id}/users/{user_id}")
def remove_user_from_branch(
    branch_id: int,
    user_id: int,
    current_user=Depends(get_current_user)
):
    require_admin(current_user)

    ok = remove_user_from_branch_db(
        admin_id=current_user["user_id"],
        user_id=user_id,
        branch_id=branch_id
    )

    if not ok:
        raise HTTPException(403, "Not your user or branch")

    return {"ok": True}

@router.get("/{branch_id}/users")
def list_branch_users(
    branch_id: int,
    current_user=Depends(get_current_user)
):
    require_admin(current_user)
    return list_users_in_branch_db(
        admin_id=current_user["user_id"],
        branch_id=branch_id
    )
