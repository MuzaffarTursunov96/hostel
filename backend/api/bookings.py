from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import date
from api.deps import get_current_user
from api.ws_manager import ws_manager

from db import (
    get_rooms_with_beds,
    get_available_beds,
    add_booking,
    add_or_get_customer
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
    user=Depends(get_current_user)
):
    return get_available_beds(branch_id, room_id, checkin, checkout)


# ---------- ADD BOOKING ----------
class BookingCreate(BaseModel):
    branch_id: int
    name: str
    passport_id: str
    contact: str
    room_id: int
    bed_id: int
    total: float
    paid: float
    checkin: date
    checkout: date


@router.post("/")
async def create_booking(data: BookingCreate, user=Depends(get_current_user)):
    add_booking(
        data.branch_id,
        data.name,
        data.passport_id,
        data.contact,
        data.room_id,
        data.bed_id,
        data.total,
        data.paid,
        data.checkin,
        data.checkout
    )

    add_or_get_customer(
    branch_id=data.branch_id,
    name=data.name,
    passport_id=data.passport_id,
    contact=data.contact
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
