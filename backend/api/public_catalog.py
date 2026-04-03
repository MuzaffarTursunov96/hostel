from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db import (
    list_public_branches_with_rating_db,
    add_branch_rating_db,
    list_branch_ratings_db,
    get_branch_rating_summary_db,
    list_public_branch_photos_db,
    get_public_branch_details_db,
    has_completed_stay_for_contact_db,
    list_public_user_history_db,
    get_booking_prepayment_config_db,
)

router = APIRouter(prefix="/public", tags=["Public Catalog"])


@router.get("/branches")
def public_branches(
    min_rating: float | None = None,
    room_type: str | None = None,
    region_slug: str | None = None,
    city_name: str | None = None,
    district_name: str | None = None,
    price_mode: str | None = None,
    limit: int = 100,
    offset: int = 0,
    q: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    lat: float | None = None,
    lng: float | None = None,
    radius_km: float | None = None,
    include_total: bool | None = None,
    include_bounds: bool | None = None,
):
    if min_rating is not None and (min_rating < 0 or min_rating > 5):
        raise HTTPException(400, "min_rating must be between 0 and 5")
    result = list_public_branches_with_rating_db(
        min_rating=min_rating,
        room_type=room_type,
        region_slug=region_slug,
        city_name=city_name,
        district_name=district_name,
        price_mode=price_mode,
        limit=limit,
        offset=offset,
        q=q,
        min_price=min_price,
        max_price=max_price,
        lat=lat,
        lng=lng,
        radius_km=radius_km,
        return_total=bool(include_total),
        return_bounds=bool(include_bounds),
    )
    if include_total or include_bounds:
        if include_total and include_bounds:
            items, total, bounds = result
            return {"items": items, "total": total, "bounds": bounds or {"min": 0, "max": 0}}
        if include_total:
            items, total = result
            return {"items": items, "total": total}
        items, bounds = result
        return {"items": items, "bounds": bounds or {"min": 0, "max": 0}}
    return result


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
    contact: str | None = None
    source: str | None = None


@router.post("/branches/{branch_id}/ratings")
def public_add_rating(branch_id: int, data: RatingIn):
    contact = (data.contact or "").strip()
    if not contact:
        raise HTTPException(400, "contact required")
    if not has_completed_stay_for_contact_db(branch_id=branch_id, contact=contact):
        raise HTTPException(403, "Rating allowed only after completed stay (checkout)")

    try:
        add_branch_rating_db(
            branch_id=branch_id,
            rating=data.rating,
            comment=data.comment,
            telegram_id=data.telegram_id,
            user_name=data.user_name,
            contact=contact,
            source=data.source,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    return {
        "ok": True,
        "summary": get_branch_rating_summary_db(branch_id),
    }


@router.get("/user-history")
def public_user_history(contact: str | None = None, telegram_id: int | None = None, limit: int = 100):
    if not (contact or telegram_id):
        raise HTTPException(400, "contact or telegram_id required")
    return {
        "items": list_public_user_history_db(contact=contact, telegram_id=telegram_id, limit=limit)
    }


@router.get("/booking-prepayment")
def public_booking_prepayment():
    cfg = get_booking_prepayment_config_db()
    return {
        "enabled": bool(cfg.get("enabled")),
        "mode": str(cfg.get("mode") or "percent"),
        "value": float(cfg.get("value") or 0),
    }
