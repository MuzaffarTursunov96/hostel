from datetime import date
import sys
import os

sys.path.append("/app/backend")

from sqlalchemy import text
from db import get_connection
from bot.bot import bot
import asyncio

today = date.today()

def run():
    with get_connection() as conn:
        rows = conn.execute(text("""
            SELECT
                b.id,
                b.branch_id,
                b.customer_name,
                b.remaining_amount
            FROM bookings b
            WHERE b.remaining_amount > 0
              AND b.notify_date = :today
              AND b.status = 'active'
        """), {"today": today}).mappings().all()

        for r in rows:
            notify_branch(r)

def notify_branch(row):
    # get users + admins of branch
    with get_connection() as conn:
        users = conn.execute(text("""
            SELECT u.telegram_id
            FROM users u
            JOIN user_branches ub ON ub.user_id = u.id
            WHERE ub.branch_id = :bid
              AND u.telegram_id IS NOT NULL
              AND u.is_active = TRUE
        """), {"bid": row["branch_id"]}).fetchall()

    msg = (
        f"⚠️ Qarzdor bron!\n"
        f"👤 {row['customer_name']}\n"
        f"💰 Qarzdorlik: {row['remaining_amount']}"
    )

    for u in users:
        asyncio.run(bot.send_message(u.telegram_id, msg))


if __name__ == "__main__":
    run()
