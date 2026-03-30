from fastapi import APIRouter, Depends,HTTPException
from pydantic import BaseModel
from api.deps import get_current_user
from datetime import date
from api.ws_manager import ws_manager
from time_utils import app_today
from db import (
    get_beds,
    add_bed,
    delete_bed,
    is_bed_busy_today,
    get_beds_with_booking_status,
    get_busy_beds_from_db,
    check_bed_has_booked,
    remove_bed_db,
    busy_beds_now,
    update_bed_db
)

router = APIRouter(prefix="/beds", tags=["Beds"])


class BedCreate(BaseModel):
    branch_id: int
    room_id: int


# ---------- LIST BEDS ----------
@router.get("/")
def list_beds(branch_id: int, room_id: int, user=Depends(get_current_user)):
    rows = get_beds(branch_id, room_id)
    return [
                {
                    "id": r["id"],
                    "bed_number": r["bed_number"],
                    "bed_type": r["bed_type"],
                    "fixed_price": float(r["fixed_price"]) if r.get("fixed_price") is not None else None,
                    "price_hourly": float(r["price_hourly"]) if r.get("price_hourly") is not None else None,
                    "price_daily": float(r["price_daily"]) if r.get("price_daily") is not None else (float(r["fixed_price"]) if r.get("fixed_price") is not None else None),
                    "price_monthly": float(r["price_monthly"]) if r.get("price_monthly") is not None else None,
                }
                for r in rows
            ]



# ---------- ADD BED ----------
@router.post("/")
async def create_bed(data: BedCreate, user=Depends(get_current_user)):
    add_bed(data.branch_id, data.room_id)
    await ws_manager.broadcast({
        "type": "beds_changed",
        "branch_id": data.branch_id,
        "room_id": data.room_id
    })

    return {"status": "ok"}


# ---------- DELETE BED ----------
@router.delete("/{bed_id}")
async def remove_bed(bed_id: int, user=Depends(get_current_user)):
    
    row = remove_bed_db(bed_id, user["branch_id"])
    
    if not row:
        raise HTTPException(404, "Bed not found")

    room_id = row["room_id"]

    status_del = delete_bed(bed_id)

    await ws_manager.broadcast({
        "type": "beds_changed",
        "branch_id": user["branch_id"],
        "room_id": room_id
    })

    return status_del



# ---------- BED BUSY (REUSE EXISTING LOGIC) ----------
@router.get("/{bed_id}/busy")
def bed_busy(bed_id: int, branch_id: int, user=Depends(get_current_user)):
    return {"busy": is_bed_busy_today(branch_id, bed_id)}


@router.get("/busy-now")
def busy_beds_now_new(
            branch_id: int,
            room_id: int,
            user=Depends(get_current_user)
        ):
    

    return busy_beds_now(branch_id, room_id)



@router.get("/status")
def beds_with_status(
    room_id: int,
    branch_id: int,
    user=Depends(get_current_user)
):
    return get_beds_with_booking_status(room_id, branch_id)


@router.get("/busy")
def get_busy_beds(
        branch_id: int,
        room_id: int,
        checkin: date,
        checkout: date,
        exclude_booking_id: int | None = None
    ):
    
    return get_busy_beds_from_db(branch_id,room_id,checkin,checkout,exclude_booking_id)


@router.get("/{bed_id}/has-bookings")
def bed_has_bookings(bed_id: int, branch_id: int, user=Depends(get_current_user)):
    return check_bed_has_booked(bed_id,branch_id)


@router.get("/busy-beds")
def busy_beds(
    branch_id: int,
    room_id: int,
    user=Depends(get_current_user)
):
    today = app_today()

    return get_busy_beds_from_db(
        branch_id=branch_id,
        room_id=room_id,
        checkin=today,
        checkout=today
    )


@router.put("/{bed_id}")
def update_bed(
        bed_id: int,
        bed_number: int,
        bed_type: str,
        fixed_price: str | None = None,
        price_hourly: str | None = None,
        price_daily: str | None = None,
        price_monthly: str | None = None,
        user=Depends(get_current_user)
    ):
    if bed_type not in ("single", "double", "child"):
        raise HTTPException(400, "Invalid bed type")

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

    update_bed_db(
        bed_id,
        bed_number,
        bed_type,
        user["branch_id"],
        fixed_price=fixed_val,
        price_hourly=hourly_val,
        price_daily=daily_val,
        price_monthly=monthly_val,
    )

    return {"ok": True}
