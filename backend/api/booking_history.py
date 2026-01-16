from fastapi import APIRouter, Depends
from datetime import date
from api.deps import get_current_user
from db import get_past_bookings

router = APIRouter(
    prefix="/booking-history",
    tags=["Booking History"]
)

@router.get("/")
def api_get_booking_history(
    branch_id: int,
    from_date: date | None = None,
    to_date: date | None = None,
    user=Depends(get_current_user)
):
    return get_past_bookings(
        branch_id=branch_id,
        from_date=from_date,
        to_date=to_date
    )
