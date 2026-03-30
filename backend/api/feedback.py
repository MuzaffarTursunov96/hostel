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


@router.post("/public")
def submit_feedback(data: FeedbackIn):
    try:
        add_branch_feedback_db(
            branch_id=data.branch_id,
            message=data.message,
            sentiment=data.sentiment,
            telegram_id=data.telegram_id,
            user_name=data.user_name,
            contact=data.contact,
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

    try:
        add_branch_feedback_db(
            branch_id=branch_id,
            message=message,
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
