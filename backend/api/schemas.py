from pydantic import BaseModel
from datetime import date

class LoginIn(BaseModel):
    username: str
    password: str

class BookingIn(BaseModel):
    branch_id: int
    customer_name: str
    contact: str | None
    room_id: int
    bed_id: int
    total_amount: float
    paid_amount: float
    checkin_date: date
    checkout_date: date

class PayDebtIn(BaseModel):
    pay_amount: float

class TelegramLoginIn(BaseModel):
    telegram_id: int
    username: str | None = None


class EmailStatusIn(BaseModel):
    email: str


class EmailRegisterIn(BaseModel):
    email: str
    password: str


class EmailPasswordIn(BaseModel):
    email: str
    password: str
