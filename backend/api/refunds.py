from datetime import date
from fastapi import Depends, HTTPException
from fastapi import APIRouter, Depends
from datetime import date
from api.deps import get_current_user

from db import get_refund_list

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.get("/refunds")
def get_refunds(
    branch_id: int,
    from_date: date,
    to_date: date,
    user=Depends(get_current_user)
):
    # 🔐 Security: user can only access own branch
    if branch_id != user["branch_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    refunds = get_refund_list(
        branch_id=branch_id,
        from_date=from_date,
        to_date=to_date
    )

    return refunds
