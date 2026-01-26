from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import date
from api.deps import get_current_user
from api.ws_manager import ws_manager

from db import (
    get_active_bookings,
    cancel_booking,
    update_booking,
    update_booking_admin
)

router = APIRouter(prefix="/active-bookings", tags=["Active Bookings"])


# ---------- LIST ----------
@router.get("/")
def api_get_active_bookings(
    branch_id: int,
    user=Depends(get_current_user)
):
    return get_active_bookings(branch_id)


class CancelBookingRequest(BaseModel):
    booking_id: int
    branch_id: int

# ---------- CANCEL ----------
@router.post("/cancel")
async def api_cancel_booking(
    data: CancelBookingRequest,
    user=Depends(get_current_user)
):
    print("Cancelling booking:", data.booking_id, "branch:", data.branch_id)
    cancel_booking(data.booking_id, data.branch_id)

    await ws_manager.broadcast({
        "type": "beds_changed",
        "booking_id": data.booking_id,
        "branch_id": data.branch_id
    })

    await ws_manager.broadcast({
        "type": "booking_changed",
        "booking_id": data.booking_id,
        "branch_id": data.branch_id
    })

    await ws_manager.broadcast({
        "type": "dashboard_changed",
        "booking_id": data.booking_id,
        "branch_id": data.branch_id
    })

    return {"status": "ok"}



# ---------- UPDATE ----------
class BookingUpdate(BaseModel):
    booking_id: int
    bed_id: int
    checkin_date: str   # YYYY-MM-DD
    checkout_date: str # YYYY-MM-DD
    total_amount: float



@router.post("/update")
async def api_update_booking(
    data: BookingUpdate,
    user=Depends(get_current_user)
):
    update_booking(
        data.booking_id,
        data.bed_id,
        data.checkin_date,
        data.checkout_date,
        data.total_amount
    )
    await ws_manager.broadcast({
        "type": "beds_changed",
        "branch_id": user["branch_id"],
        "booking_id": data.booking_id
    })

    await ws_manager.broadcast({
        "type": "booking_changed",
        "branch_id": user["branch_id"],
        "booking_id": data.booking_id
    })

    await ws_manager.broadcast({
        "type": "dashboard_changed",
        "branch_id": user["branch_id"],
        "booking_id": data.booking_id
    })

    return {"status": "ok"}

class AdminBookingUpdate(BaseModel):
    booking_id: int
    room_id: int
    bed_id: int
    checkout_date: date
    total_amount: float


@router.post("/update-admin")
async def admin_update_booking(
    data: AdminBookingUpdate,
    user=Depends(get_current_user)
):
    update_booking_admin(
        data.booking_id,
        data.room_id,
        data.bed_id,
        data.checkout_date,
        data.total_amount
    )
    await ws_manager.broadcast({
        "type": "beds_changed",
        "booking_id": data.booking_id,
        "branch_id": user["branch_id"]
    })

    await ws_manager.broadcast({
        "type": "booking_changed",
        "booking_id": data.booking_id,
        "branch_id": user["branch_id"]
    })

    await ws_manager.broadcast({
        "type": "dashboard_changed",
        "booking_id": data.booking_id,
        "branch_id": user["branch_id"]
    })

    return {"status": "ok"}
