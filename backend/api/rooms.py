from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from api.deps import get_current_user
from db import get_rooms_with_beds, delete_room_db,check_room_had_booked,create_room_db
from api.ws_manager import ws_manager

router = APIRouter(prefix="/rooms", tags=["Rooms"])


# ================= SCHEMAS =================
class RoomCreate(BaseModel):
    number: str
    branch_id: int


# ================= GET ROOMS =================
@router.get("/")
def rooms(branch_id: int, user=Depends(get_current_user)):
    return get_rooms_with_beds(branch_id)


# ================= CREATE ROOM =================
@router.post("/")
async def create_room(data: RoomCreate, user=Depends(get_current_user)):

    
    create_stat =create_room_db(data.number,data.branch_id)
    
    if create_stat['status'] =='success':
        await ws_manager.broadcast({
            "type": "rooms_changed",
            "branch_id": data.branch_id
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
        "branch_id": branch_id
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



