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
    set_room_pricing_db,
    set_room_booking_mode_db,
    set_room_type_db,
)
from api.ws_manager import ws_manager

router = APIRouter(prefix="/rooms", tags=["Rooms"])
ROOM_IMAGE_DIR = os.path.abspath(
    os.getenv("ROOM_IMAGE_DIR", "/var/www/miniapp/static/room_images")
)
os.makedirs(ROOM_IMAGE_DIR, exist_ok=True)
ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".heic", ".heif", ".avif"
}


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


# ================= SCHEMAS =================
class RoomCreate(BaseModel):
    room_name: str
    number: str
    branch_id: int
    fixed_price: float | None = None
    price_hourly: float | None = None
    price_daily: float | None = None
    price_monthly: float | None = None
    booking_mode: str | None = None
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
        data.room_type,
        data.price_hourly,
        data.price_daily,
        data.price_monthly,
        data.booking_mode,
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
    price_hourly: str | None = None,
    price_daily: str | None = None,
    price_monthly: str | None = None,
    user=Depends(get_current_user),
):
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin only")

    def _parse_num(raw: str | None, field_name: str):
        if raw is None:
            return None
        s = str(raw).strip().lower()
        if s in {"", "null", "none"}:
            return None
        try:
            v = float(s)
        except Exception:
            raise HTTPException(400, f"Invalid {field_name}")
        if v < 0:
            raise HTTPException(400, f"{field_name} must be >= 0")
        return v

    fixed_val = _parse_num(fixed_price, "fixed_price")
    daily_val = _parse_num(price_daily, "price_daily")
    hourly_val = _parse_num(price_hourly, "price_hourly")
    monthly_val = _parse_num(price_monthly, "price_monthly")
    if daily_val is None and fixed_val is not None:
        daily_val = fixed_val

    if price_hourly is None and price_daily is None and price_monthly is None:
        set_room_fixed_price_db(room_id=room_id, branch_id=branch_id, fixed_price=fixed_val)
    else:
        set_room_pricing_db(
            room_id=room_id,
            branch_id=branch_id,
            price_hourly=hourly_val,
            price_daily=daily_val,
            price_monthly=monthly_val,
        )
    await ws_manager.broadcast({
        "type": "rooms_changed",
        "branch_id": branch_id,
        "room_id": room_id,
    })
    return {
        "ok": True,
        "fixed_price": daily_val,
        "price_hourly": hourly_val,
        "price_daily": daily_val,
        "price_monthly": monthly_val,
    }


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


@router.put("/{room_id}/booking-mode")
async def set_room_booking_mode(
    room_id: int,
    branch_id: int,
    booking_mode: str | None = None,
    user=Depends(get_current_user),
):
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin only")

    mode = "full" if str(booking_mode or "").strip().lower() in {"full", "room_full", "full_room"} else "bed"
    set_room_booking_mode_db(room_id=room_id, branch_id=branch_id, booking_mode=mode)
    await ws_manager.broadcast({
        "type": "rooms_changed",
        "branch_id": branch_id,
        "room_id": room_id,
    })
    return {"ok": True, "booking_mode": mode}


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
    skipped = 0
    for idx, file in enumerate(files):
        if not _is_image_upload(file):
            skipped += 1
            continue

        ext = _pick_extension(file)
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
        if skipped > 0:
            raise HTTPException(
                400,
                "No valid image files (supported: jpg, jpeg, png, webp, gif, bmp, heic, heif, avif)"
            )
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

