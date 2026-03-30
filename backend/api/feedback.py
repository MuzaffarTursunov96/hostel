from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
import os
import uuid
from api.deps import get_current_user, is_root_admin
from db import (
    add_branch_feedback_db,
    list_branch_feedback_for_admin_db,
    update_feedback_status_db,
)

router = APIRouter(prefix="/feedback", tags=["Feedback"])
ROOM_REPORT_DIR = os.path.abspath(
    os.path.join(os.getcwd(), "miniapp", "static", "room_reports")
)
os.makedirs(ROOM_REPORT_DIR, exist_ok=True)


class FeedbackIn(BaseModel):
    branch_id: int
    message: str
    sentiment: str | None = None  # positive / neutral / negative
    telegram_id: int | None = None
    user_name: str | None = None
    contact: str | None = None
    source: str | None = None


class BookingRequestIn(BaseModel):
    branch_id: int
    full_name: str | None = None
    phone: str
    telegram_id: int | None = None
    user_name: str | None = None
    room_or_bed: str | None = None
    checkin: str | None = None
    checkout: str | None = None
    message: str | None = None
    source: str | None = None


@router.post("/public")
def submit_feedback(data: FeedbackIn):
    src = (data.source or "web_app").strip().lower()
    if src not in {"web_app", "mobile_app", "desktop_app"}:
        src = "web_app"
    try:
        add_branch_feedback_db(
            branch_id=data.branch_id,
            message=f"[{src}] {data.message}",
            sentiment=data.sentiment,
            telegram_id=data.telegram_id,
            user_name=data.user_name,
            contact=data.contact,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    return {"ok": True}


@router.post("/public-booking-request")
def submit_booking_request(data: BookingRequestIn):
    phone = (data.phone or "").strip()
    if not phone:
        raise HTTPException(400, "phone required")

    src = (data.source or "web_app").strip().lower()
    if src not in {"web_app", "mobile_app", "desktop_app"}:
        src = "web_app"

    parts = []
    full_name = (data.full_name or "").strip()
    if full_name:
        parts.append(f"Client: {full_name}")
    parts.append(f"Phone: {phone}")
    parts.append(f"Source: {src}")
    room_or_bed = (data.room_or_bed or "").strip()
    if room_or_bed:
        parts.append(f"Room/Bed: {room_or_bed}")
    checkin = (data.checkin or "").strip()
    if checkin:
        parts.append(f"Check-in: {checkin}")
    checkout = (data.checkout or "").strip()
    if checkout:
        parts.append(f"Check-out: {checkout}")
    user_msg = (data.message or "").strip()
    if user_msg:
        parts.append(f"Message: {user_msg}")

    summary = " | ".join(parts)

    try:
        add_branch_feedback_db(
            branch_id=data.branch_id,
            message=summary,
            sentiment=None,
            telegram_id=data.telegram_id,
            user_name=data.user_name or full_name or None,
            contact=phone,
            report_type="booking_request",
            room_label=room_or_bed or None,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    return {"ok": True}


@router.post("/public-room-report")
def submit_room_report(
    branch_id: int = Form(...),
    message: str = Form(...),
    room_label: str | None = Form(None),
    telegram_id: int | None = Form(None),
    user_name: str | None = Form(None),
    contact: str | None = Form(None),
    source: str | None = Form("web_app"),
    file: UploadFile | None = File(None),
):
    saved_image_path = None
    if file is not None and file.filename:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(400, "Only image files allowed")
        ext = (os.path.splitext(file.filename)[1] or ".jpg").lower()
        filename = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(ROOM_REPORT_DIR, filename)
        with open(path, "wb") as fp:
            fp.write(file.file.read())
        saved_image_path = f"/static/room_reports/{filename}"

    src = (source or "web_app").strip().lower()
    if src not in {"web_app", "mobile_app", "desktop_app"}:
        src = "web_app"

    try:
        add_branch_feedback_db(
            branch_id=branch_id,
            message=f"[{src}] {message}",
            sentiment=None,
            telegram_id=telegram_id,
            user_name=user_name,
            contact=contact,
            report_type="room_state",
            room_label=room_label,
            image_path=saved_image_path,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    return {"ok": True}


@router.get("/admin")
def list_feedback(
    branch_id: int | None = None,
    limit: int = 200,
    user=Depends(get_current_user)
):
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin only")

    return list_branch_feedback_for_admin_db(
        admin_id=int(user["user_id"]),
        is_root=is_root_admin(user),
        branch_id=branch_id,
        limit=limit,
    )


@router.put("/admin/{feedback_id}")
def update_feedback(
    feedback_id: int,
    status: str | None = None,
    is_read: bool | None = None,
    admin_note: str | None = None,
    user=Depends(get_current_user)
):
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin only")

    try:
        ok = update_feedback_status_db(
            admin_id=int(user["user_id"]),
            feedback_id=feedback_id,
            status=status,
            is_read=is_read,
            admin_note=admin_note,
            is_root=is_root_admin(user),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    if not ok:
        raise HTTPException(403, "Not allowed")

    return {"ok": True}
