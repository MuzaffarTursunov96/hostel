from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List
import os
import uuid
from api.deps import get_current_user
from db import (
    get_rooms_with_beds,
    delete_room_db,
    check_room_had_booked,
    create_room_db,
    list_room_images_db,
    add_room_image_path_db,
    delete_room_image_db,
    set_room_cover_image_db,
    set_room_fixed_price_db,
    set_room_type_db,
)
from api.ws_manager import ws_manager

router = APIRouter(prefix="/rooms", tags=["Rooms"])
ROOM_IMAGE_DIR = os.path.abspath(
    os.getenv("ROOM_IMAGE_DIR", "/var/www/miniapp/static/room_images")
)
os.makedirs(ROOM_IMAGE_DIR, exist_ok=True)


# ================= SCHEMAS =================
class RoomCreate(BaseModel):
    room_name: str
    number: str
    branch_id: int
    fixed_price: float | None = None
    room_type: str | None = None


# ================= GET ROOMS =================
@router.get("/")
def rooms(branch_id: int, user=Depends(get_current_user)):
    return get_rooms_with_beds(branch_id)


# ================= CREATE ROOM =================
@router.post("/")
async def create_room(data: RoomCreate, user=Depends(get_current_user)):

    
    create_stat =create_room_db(
        data.number,
        data.room_name,
        data.branch_id,
        data.fixed_price,
        data.room_type
    )
    
    if create_stat['status'] =='success':
        await ws_manager.broadcast({
            "type": "rooms_changed",
            "branch_id": data.branch_id,
            "number":data.number
        })
    elif create_stat['status'] =='error':
        raise HTTPException(status_code=400, detail="Room already exists")

    return {"status": "ok"}


# ================= DELETE ROOM (AND BEDS) =================
@router.delete("/{room_id}")
async def delete_room(room_id: int, branch_id: int, user=Depends(get_current_user)):

    delete_stat =delete_room_db(room_id,branch_id)


    if delete_stat['status'] =='error':
        raise HTTPException(
            status_code=400,
            detail="Room has booked beds"
        )


    await ws_manager.broadcast({
        "type": "rooms_changed",
        "branch_id": branch_id,
        "room_id":room_id
    })

    await ws_manager.broadcast({
        "type": "beds_changed",
        "branch_id": branch_id,
        "room_id": room_id
    })


    return {"status": "ok"}



@router.get("/{room_id}/has-bookings")
def room_has_bookings(room_id: int, branch_id: int, user=Depends(get_current_user)):
    return check_room_had_booked(room_id,branch_id)


@router.put("/{room_id}/price")
async def set_room_price(
    room_id: int,
    branch_id: int,
    fixed_price: str | None = None,
    user=Depends(get_current_user),
):
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin only")

    val = None
    if fixed_price is not None:
        s = str(fixed_price).strip().lower()
        if s not in {"", "null", "none"}:
            try:
                val = float(s)
            except Exception:
                raise HTTPException(400, "Invalid fixed_price")
            if val < 0:
                raise HTTPException(400, "fixed_price must be >= 0")

    set_room_fixed_price_db(room_id=room_id, branch_id=branch_id, fixed_price=val)
    await ws_manager.broadcast({
        "type": "rooms_changed",
        "branch_id": branch_id,
        "room_id": room_id,
    })
    return {"ok": True, "fixed_price": val}


@router.put("/{room_id}/type")
async def set_room_type(
    room_id: int,
    branch_id: int,
    room_type: str | None = None,
    user=Depends(get_current_user),
):
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin only")

    set_room_type_db(room_id=room_id, branch_id=branch_id, room_type=room_type)
    await ws_manager.broadcast({
        "type": "rooms_changed",
        "branch_id": branch_id,
        "room_id": room_id,
    })
    return {"ok": True, "room_type": (room_type or "").strip() or None}


@router.get("/{room_id}/images")
def list_room_images(room_id: int, branch_id: int, user=Depends(get_current_user)):
    return {"images": list_room_images_db(room_id=room_id, branch_id=branch_id)}


@router.post("/{room_id}/images")
async def upload_room_images(
    room_id: int,
    branch_id: int,
    files: List[UploadFile] = File(None),
    is_cover: bool = False,
    user=Depends(get_current_user)
):
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin only")
    if not files:
        raise HTTPException(400, "No files uploaded")

    saved = []
    for idx, file in enumerate(files):
        if not file.content_type or not file.content_type.startswith("image/"):
            continue

        ext = (os.path.splitext(file.filename or "")[1] or ".jpg").lower()
        filename = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(ROOM_IMAGE_DIR, filename)

        with open(path, "wb") as fp:
            fp.write(file.file.read())

        try:
            row = add_room_image_path_db(
                room_id=room_id,
                branch_id=branch_id,
                filename=filename,
                is_cover=bool(is_cover and idx == 0),
                max_images=12
            )
        except ValueError as exc:
            if os.path.exists(path):
                os.remove(path)
            raise HTTPException(400, str(exc))

        saved.append(row)

    if not saved:
        raise HTTPException(400, "No valid image files")

    await ws_manager.broadcast({
        "type": "rooms_changed",
        "branch_id": branch_id,
        "room_id": room_id,
    })

    return {"ok": True, "saved": saved}


@router.put("/{room_id}/images/{image_id}/cover")
def set_room_cover_image(
    room_id: int,
    image_id: int,
    branch_id: int,
    user=Depends(get_current_user)
):
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin only")

    ok = set_room_cover_image_db(
        image_id=image_id,
        room_id=room_id,
        branch_id=branch_id
    )
    if not ok:
        raise HTTPException(404, "Image not found")
    return {"ok": True}


@router.delete("/{room_id}/images/{image_id}")
async def delete_room_image(
    room_id: int,
    image_id: int,
    branch_id: int,
    user=Depends(get_current_user)
):
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin only")

    row = delete_room_image_db(
        image_id=image_id,
        room_id=room_id,
        branch_id=branch_id
    )
    if not row:
        raise HTTPException(404, "Image not found")

    image_path = str(row.get("image_path") or "").strip()
    abs_path = ""
    if image_path.startswith("/static/room_images/"):
        filename = os.path.basename(image_path)
        abs_path = os.path.join(ROOM_IMAGE_DIR, filename)
    elif image_path:
        abs_path = image_path
    if abs_path and os.path.exists(abs_path):
        os.remove(abs_path)

    await ws_manager.broadcast({
        "type": "rooms_changed",
        "branch_id": branch_id,
        "room_id": room_id,
    })

    return {"ok": True}

