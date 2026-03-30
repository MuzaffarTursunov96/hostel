from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db import (
    list_public_branches_with_rating_db,
    add_branch_rating_db,
    list_branch_ratings_db,
    get_branch_rating_summary_db,
    list_public_branch_photos_db,
    get_public_branch_details_db,
)

router = APIRouter(prefix="/public", tags=["Public Catalog"])


@router.get("/branches")
def public_branches(min_rating: float | None = None, room_type: str | None = None, limit: int = 100):
    if min_rating is not None and (min_rating < 0 or min_rating > 5):
        raise HTTPException(400, "min_rating must be between 0 and 5")
    return list_public_branches_with_rating_db(min_rating=min_rating, room_type=room_type, limit=limit)


@router.get("/branches/{branch_id}/ratings")
def public_branch_ratings(branch_id: int, limit: int = 50):
    return {
        "summary": get_branch_rating_summary_db(branch_id),
        "items": list_branch_ratings_db(branch_id, limit=limit),
    }


@router.get("/branches/{branch_id}/photos")
def public_branch_photos(branch_id: int, limit: int = 50):
    return {
        "items": list_public_branch_photos_db(branch_id=branch_id, limit=limit),
    }


@router.get("/branches/{branch_id}/details")
def public_branch_details(branch_id: int):
    payload = get_public_branch_details_db(branch_id=branch_id)
    if not payload:
        raise HTTPException(404, "Branch not found")
    return payload


class RatingIn(BaseModel):
    rating: int
    comment: str | None = None
    telegram_id: int | None = None
    user_name: str | None = None


@router.post("/branches/{branch_id}/ratings")
def public_add_rating(branch_id: int, data: RatingIn):
    try:
        add_branch_rating_db(
            branch_id=branch_id,
            rating=data.rating,
            comment=data.comment,
            telegram_id=data.telegram_id,
            user_name=data.user_name,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    return {
        "ok": True,
        "summary": get_branch_rating_summary_db(branch_id),
    }
