from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date, timedelta
from api.deps import get_current_user
from api.ws_manager import ws_manager

from db import (
    get_rooms_with_beds,
    get_available_beds,
    add_booking,
    add_or_get_customer,
    update_future_booking_admin,
    cancel_future_booking,
    add_booking_guest,
    get_branch_prepayment_config_db,
)

router = APIRouter(prefix="/booking", tags=["Booking"])


# ---------- ROOMS ----------
@router.get("/rooms")
def booking_rooms(branch_id: int, user=Depends(get_current_user)):
    return get_rooms_with_beds(branch_id)


# ---------- AVAILABLE BEDS ----------
@router.get("/available-beds")
def booking_available_beds(
    branch_id: int,
    room_id: int,
    checkin: date,
    checkout: date,
    is_hourly: bool = False,
    user=Depends(get_current_user)
):
    if (not is_hourly and checkout <= checkin) or (is_hourly and checkout < checkin):
        raise HTTPException(
            status_code=400,
            detail="For same-day booking, enable hourly booking."
        )
    if is_hourly and checkout <= checkin:
        checkout = checkin + timedelta(days=1)
    return get_available_beds(branch_id, room_id, checkin, checkout)


# ---------- ADD BOOKING ----------
class SecondGuest(BaseModel):
    name: str
    passport_id: str
    contact: str


class BookingCreate(BaseModel):
    branch_id: int

    # primary guest
    name: str
    passport_id: str
    contact: str

    # optional second guest
    second_guest: Optional[SecondGuest] = None

    room_id: int
    bed_id: int
    total: float
    paid: float
    checkin: date
    checkout: date
    notify_date: date | None = None
    is_hourly: bool = False


@router.post("/")
async def create_booking(data: BookingCreate, user=Depends(get_current_user)):
    cfg = get_branch_prepayment_config_db(data.branch_id)
    if cfg.get("enabled"):
        mode = cfg.get("mode", "percent")
        value = float(cfg.get("value", 0) or 0)
        total = float(data.total or 0)
        paid = float(data.paid or 0)
        required = (total * value / 100.0) if mode == "percent" else value
        if required > total:
            required = total
        if paid + 1e-9 < required:
            if mode == "percent":
                raise HTTPException(400, f"Prepayment required: minimum {value:.2f}% ({required:.2f})")
            raise HTTPException(400, f"Prepayment required: minimum {required:.2f}")

    booking_id = add_booking(
        data.branch_id,
        data.name,
        data.passport_id,
        data.contact,
        data.room_id,
        data.bed_id,
        data.total,
        data.paid,
        data.checkin,
        data.checkout,
        data.notify_date or data.checkout,
        data.is_hourly,
    )

    add_or_get_customer(
        branch_id=data.branch_id,
        name=data.name,
        passport_id=data.passport_id,
        contact=data.contact,
    )

    if data.second_guest:
        customer_id = add_or_get_customer(
            branch_id=data.branch_id,
            name=data.second_guest.name,
            passport_id=data.second_guest.passport_id,
            contact=data.second_guest.contact,
        )

        add_booking_guest(
            booking_id=booking_id,
            customer_id=customer_id,
        )

    await ws_manager.broadcast({
        "type": "beds_changed",
        "branch_id": data.branch_id,
        "room_id": data.room_id,
    })

    await ws_manager.broadcast({
        "type": "booking_changed",
        "branch_id": data.branch_id,
        "room_id": data.room_id,
    })

    await ws_manager.broadcast({
        "type": "dashboard_changed",
        "branch_id": data.branch_id,
        "room_id": data.room_id,
    })

    return {"status": "ok"}


class AdminBookingUpdateFuture(BaseModel):
    booking_id: int
    room_id: int
    bed_id: int
    checkin_date: date
    checkout_date: date
    total_amount: float


@router.post("/update-future-booking")
async def admin_update_booking(data: AdminBookingUpdateFuture, user=Depends(get_current_user)):
    update_future_booking_admin(
        data.booking_id,
        data.room_id,
        data.bed_id,
        data.checkin_date,
        data.checkout_date,
        data.total_amount,
    )

    await ws_manager.broadcast({
        "type": "beds_changed",
        "booking_id": data.booking_id,
        "branch_id": user["branch_id"],
    })

    await ws_manager.broadcast({
        "type": "booking_changed",
        "booking_id": data.booking_id,
        "branch_id": user["branch_id"],
    })

    await ws_manager.broadcast({
        "type": "dashboard_changed",
        "booking_id": data.booking_id,
        "branch_id": user["branch_id"],
    })

    return {"status": "ok"}


class BookingCancelFuture(BaseModel):
    booking_id: int
    branch_id: int
    refund_amount: int
    refund_title: str


@router.post("/future-bookings/cancel")
async def cancel_future_booking_api(data: BookingCancelFuture, user=Depends(get_current_user)):
    cancel_future_booking(
        booking_id=data.booking_id,
        branch_id=data.branch_id,
        refund_amount=float(data.refund_amount),
        refund_title=data.refund_title,
    )

    await ws_manager.broadcast({
        "type": "beds_changed",
        "booking_id": data.booking_id,
        "branch_id": user["branch_id"],
    })

    await ws_manager.broadcast({
        "type": "booking_changed",
        "booking_id": data.booking_id,
        "branch_id": user["branch_id"],
    })

    await ws_manager.broadcast({
        "type": "dashboard_changed",
        "booking_id": data.booking_id,
        "branch_id": user["branch_id"],
    })

    return {"status": "ok"}
