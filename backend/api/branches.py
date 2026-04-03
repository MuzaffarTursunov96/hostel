from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List
import os
import uuid
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
                list_users_in_branch_db,
                list_branch_images_db,
                add_branch_image_path_db,
                set_branch_cover_image_db,
                delete_branch_image_db,
                )

from api.ws_manager import ws_manager

router = APIRouter(prefix="/branches", tags=["Branches"])
BRANCH_IMAGE_DIR = os.path.abspath(
    os.getenv("BRANCH_IMAGE_DIR", "/var/www/miniapp/static/branch_images")
)
os.makedirs(BRANCH_IMAGE_DIR, exist_ok=True)
ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".heic", ".heif", ".avif"
}

def require_admin(user):
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin only")


def _is_image_upload(file: UploadFile) -> bool:
    ctype = (file.content_type or "").strip().lower()
    ext = (os.path.splitext(file.filename or "")[1] or "").strip().lower()
    return ctype.startswith("image/") or ext in ALLOWED_IMAGE_EXTENSIONS


def _pick_extension(file: UploadFile) -> str:
    ext = (os.path.splitext(file.filename or "")[1] or "").strip().lower()
    if ext in ALLOWED_IMAGE_EXTENSIONS:
        return ext
    ctype = (file.content_type or "").strip().lower()
    if "png" in ctype:
        return ".png"
    if "webp" in ctype:
        return ".webp"
    if "gif" in ctype:
        return ".gif"
    if "bmp" in ctype:
        return ".bmp"
    if "heic" in ctype:
        return ".heic"
    if "heif" in ctype:
        return ".heif"
    if "avif" in ctype:
        return ".avif"
    return ".jpg"


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
    district_name = data.get("district_name", None)
    district_slug = data.get("district_slug", None)
    contact_phone = data.get("contact_phone", None)
    contact_telegram = data.get("contact_telegram", None)
    amenities = data.get("amenities", None)
    prepayment_enabled = data.get("prepayment_enabled", None)
    prepayment_mode = data.get("prepayment_mode", None)
    prepayment_value = data.get("prepayment_value", None)
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
        district_name=district_name,
        district_slug=district_slug,
        contact_phone=contact_phone,
        contact_telegram=contact_telegram,
        amenities=amenities,
        prepayment_enabled=prepayment_enabled,
        prepayment_mode=prepayment_mode,
        prepayment_value=prepayment_value,
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
    district_name = data.get("district_name", None)
    district_slug = data.get("district_slug", None)
    contact_phone = data.get("contact_phone", None)
    contact_telegram = data.get("contact_telegram", None)
    amenities = data.get("amenities", None)
    prepayment_enabled = data.get("prepayment_enabled", None)
    prepayment_mode = data.get("prepayment_mode", None)
    prepayment_value = data.get("prepayment_value", None)
    cover_image = data.get("cover_image", "__NO_CHANGE__")

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
        district_name=district_name,
        district_slug=district_slug,
        contact_phone=contact_phone,
        contact_telegram=contact_telegram,
        amenities=amenities,
        prepayment_enabled=prepayment_enabled,
        prepayment_mode=prepayment_mode,
        prepayment_value=prepayment_value,
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


@router.get("/admin/{branch_id}/images")
def list_branch_images(
    branch_id: int,
    current_user=Depends(get_current_user)
):
    require_admin(current_user)
    images = list_branch_images_db(
        admin_id=current_user["user_id"],
        branch_id=branch_id
    )
    if images is None:
        raise HTTPException(403, "Not your branch")
    return {"images": images}


@router.post("/admin/{branch_id}/images")
async def upload_branch_images(
    branch_id: int,
    files: List[UploadFile] = File(None),
    is_cover: bool = False,
    current_user=Depends(get_current_user)
):
    require_admin(current_user)
    if not files:
        raise HTTPException(400, "No files uploaded")

    saved = []
    skipped = 0
    for idx, file in enumerate(files):
        if not _is_image_upload(file):
            skipped += 1
            continue

        ext = _pick_extension(file)
        filename = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(BRANCH_IMAGE_DIR, filename)
        with open(path, "wb") as fp:
            fp.write(file.file.read())

        try:
            row = add_branch_image_path_db(
                admin_id=current_user["user_id"],
                branch_id=branch_id,
                filename=filename,
                is_cover=bool(is_cover and idx == 0),
                max_images=3
            )
        except ValueError as exc:
            if os.path.exists(path):
                os.remove(path)
            raise HTTPException(400, str(exc))

        saved.append(row)

    if not saved:
        if skipped > 0:
            raise HTTPException(
                400,
                "No valid image files (supported: jpg, jpeg, png, webp, gif, bmp, heic, heif, avif)"
            )
        raise HTTPException(400, "No valid image files")

    return {"ok": True, "saved": saved}


@router.put("/admin/{branch_id}/images/{image_id}/cover")
def set_branch_cover_image(
    branch_id: int,
    image_id: int,
    current_user=Depends(get_current_user)
):
    require_admin(current_user)
    ok = set_branch_cover_image_db(
        admin_id=current_user["user_id"],
        branch_id=branch_id,
        image_id=image_id
    )
    if not ok:
        raise HTTPException(404, "Image not found")
    return {"ok": True}


@router.delete("/admin/{branch_id}/images/{image_id}")
def delete_branch_image(
    branch_id: int,
    image_id: int,
    current_user=Depends(get_current_user)
):
    require_admin(current_user)
    row = delete_branch_image_db(
        admin_id=current_user["user_id"],
        branch_id=branch_id,
        image_id=image_id
    )
    if not row:
        raise HTTPException(404, "Image not found")

    image_path = str(row.get("image_path") or "").strip()
    abs_path = ""
    if image_path.startswith("/static/branch_images/"):
        filename = os.path.basename(image_path)
        abs_path = os.path.join(BRANCH_IMAGE_DIR, filename)
    elif image_path:
        abs_path = image_path
    if abs_path and os.path.exists(abs_path):
        os.remove(abs_path)

    return {"ok": True}
