from fastapi import APIRouter, Depends
from api.deps import get_current_user

from db import get_payment_history_by_month

router = APIRouter(prefix="/payment-history", tags=["Payment History"])


@router.get("/")
def payment_history(
    branch_id: int,
    year: int,
    month: int,
    user=Depends(get_current_user)
):
    return get_payment_history_by_month(branch_id, year, month)
