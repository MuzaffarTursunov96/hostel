from fastapi import APIRouter, Depends, Query
from api.deps import get_current_user
from db import get_active_booking_now,bed_future_exists,get_future_bookings,is_bed_free_in_range,get_dashboard_rooms,get_dashboard_beds

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])



@router.get("/rooms")
def dashboard_rooms(
        branch_id: int,
        checkin_date: str | None = Query(None),
        checkout_date: str | None = Query(None),
        user=Depends(get_current_user),
    ):
    

    
    rooms = get_dashboard_rooms(branch_id)

    result = []

    for room in rooms:
        room_data = {
            "room_id": room["id"],
            "room_number": room["number"],
            "room_name": room["room_name"],
            "beds": []
        }

        # -------- BEDS --------
        
        beds = get_dashboard_beds(branch_id, room["id"])

        has_filter = checkin_date and checkout_date

        for bed in beds:
            if has_filter:
                is_free = is_bed_free_in_range(
                    branch_id,
                    bed["id"],
                    checkin_date,
                    checkout_date
                )
                if not is_free:
                    continue
                booking = None
            else:
                booking = get_active_booking_now(branch_id, bed["id"])

            room_data["beds"].append({
                "bed_id": bed["id"],
                "bed_number": bed["bed_number"],
                "is_busy": booking is not None,
                "checkout_date": booking["checkout_date"] if booking else None,
                "has_future": bed_future_exists(branch_id, bed["id"])
            })

        if room_data["beds"]:
            result.append(room_data)
    
    return result



@router.get("/beds/future-exists")
def future_exists(branch_id: int, bed_id: int):
    return {"exists": bed_future_exists(branch_id, bed_id)}


@router.get("/beds/future-bookings")
def future_bookings(branch_id: int, bed_id: int):
    return get_future_bookings(branch_id, bed_id)
