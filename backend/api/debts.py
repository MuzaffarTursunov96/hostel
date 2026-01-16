from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import date
from api.deps import get_current_user
from api.ws_manager import ws_manager

from db import (
    get_debt_summary,
    get_debts_by_range,
    pay_booking_amount
)

router = APIRouter(prefix="/debts", tags=["Debts"])


# ---------- SUMMARY ----------
@router.get("/summary")
def debt_summary(
    branch_id: int,
    from_date: date,
    to_date: date,
    user=Depends(get_current_user)
):
    return get_debt_summary(branch_id, from_date, to_date)


# ---------- LIST ----------
@router.get("/")
def debts_by_range(
    branch_id: int,
    from_date: date,
    to_date: date,
    user=Depends(get_current_user)
):
    return get_debts_by_range(branch_id, from_date, to_date)


# ---------- PAY ----------
class DebtPay(BaseModel):
    branch_id: int
    booking_id: int
    amount: float
    paid_by: str


@router.post("/pay")
async def pay_debt(data: DebtPay, user=Depends(get_current_user)):
    pay_booking_amount(
        data.branch_id,
        data.booking_id,
        data.amount,
        paid_by=data.paid_by
    )

    await ws_manager.broadcast({
        "type": "payments_changed",
        "branch_id": data.branch_id
    })

    await ws_manager.broadcast({
        "type": "dashboard_changed",
        "branch_id": data.branch_id
    })

    return {"status": "ok"}
