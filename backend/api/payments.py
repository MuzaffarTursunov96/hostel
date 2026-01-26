from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import date
from api.deps import get_current_user
from api.ws_manager import ws_manager

from db import (
    add_expense,
    get_expenses_by_month,
    get_monthly_finance
)

router = APIRouter(prefix="/payments", tags=["Payments"])


# ---------- SCHEMAS ----------
class ExpenseCreate(BaseModel):
    branch_id: int
    title: str
    category: str
    amount: float
    expense_date: date


# ---------- ADD EXPENSE ----------
@router.post("/expense")
async def api_add_expense(data: ExpenseCreate, user=Depends(get_current_user)):
    add_expense(
        branch_id=data.branch_id,
        title=data.title,
        category=data.category,
        amount=data.amount,
        expense_date=data.expense_date
    )
    await ws_manager.broadcast({
        "type": "payments_changed",
        "branch_id": data.branch_id,
        "category": data.category
    })

    await ws_manager.broadcast({
        "type": "dashboard_changed",
        "branch_id": data.branch_id,
        "category": data.category
    })

    return {"status": "ok"}


# ---------- MONTHLY FINANCE ----------
@router.get("/monthly-finance")
def api_monthly_finance(
    branch_id: int,
    year: int,
    month: int,
    user=Depends(get_current_user)
):
    return get_monthly_finance(branch_id, year, month)


# ---------- EXPENSES BY MONTH ----------
@router.get("/expenses")
def api_expenses_by_month(
    branch_id: int,
    year: int,
    month: int,
    user=Depends(get_current_user)
):
    return get_expenses_by_month(branch_id, year, month)
