from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from api.deps import get_current_user, is_root_admin
from db import get_admin_finance_report_db

router = APIRouter(prefix="/admin-reports", tags=["Admin Reports"])


@router.get("/finance")
def admin_finance_report(
    scope: str = "month",
    year: int | None = None,
    month: int | None = None,
    user=Depends(get_current_user)
):
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin only")

    now = datetime.utcnow()
    scope_norm = (scope or "month").strip().lower()
    if scope_norm not in ("month", "year", "total"):
        raise HTTPException(400, "scope must be month, year or total")

    q_year = year
    q_month = month

    if scope_norm == "month":
        q_year = q_year or now.year
        q_month = q_month or now.month
    elif scope_norm == "year":
        q_year = q_year or now.year
        q_month = None
    else:
        q_year = None
        q_month = None

    if q_month is not None and (q_month < 1 or q_month > 12):
        raise HTTPException(400, "month must be 1..12")

    payload = get_admin_finance_report_db(
        admin_id=int(user["user_id"]),
        year=q_year,
        month=q_month,
        is_root=is_root_admin(user)
    )

    return {
        "scope": scope_norm,
        "year": q_year,
        "month": q_month,
        "branches": payload["branches"],
        "totals": payload["totals"],
    }
