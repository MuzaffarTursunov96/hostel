import sys
import os
import asyncio
from datetime import date
from sqlalchemy import text

# allow imports from backend
sys.path.append("/app/backend")

from db import get_connection
from bot.bot import bot  # aiogram Bot instance


async def send_notifications(rows):
    today = date.today()

    for r in rows:
        # determine status text
        if r["checkout_date"] < today:
            status_text = "🚨 *Bron muddati o‘tgan (checkout o‘tib ketgan)*"
        elif r["notify_date"] < today:
            status_text = "⚠️ *Qarzdorlik muddati o‘tgan*"
        else:
            status_text = "⏰ *Bugun eslatma kuni*"

        # get users for this branch
        with get_connection() as conn:
            users = conn.execute(text("""
                SELECT u.telegram_id
                FROM users u
                JOIN user_branches ub ON ub.user_id = u.id
                WHERE ub.branch_id = :bid
                  AND u.telegram_id IS NOT NULL
                  AND u.is_active = TRUE
            """), {"bid": r["branch_id"]}).fetchall()

        if not users:
            continue

        # telegram message (table-style)
        msg = (
            "⚠️ *Qarzdor bron bo‘yicha eslatma*\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"{status_text}\n"
            f"👤 *Mijoz:* {r['customer_name']}\n"
            f"🏨 *Filial ID:* {r['branch_id']}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 *Qarzdorlik:* `{r['remaining_amount']}` so‘m\n"
            f"📅 *Belgilangan sana:* {r['notify_date']}\n"
            f"🚪 *Checkout:* {r['checkout_date']}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "❗ Iltimos, to‘lovni amalga oshiring"
        )

        # send to all users of branch
        for u in users:
            try:
                await bot.send_message(
                    u.telegram_id,
                    msg,
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"Telegram send failed ({u.telegram_id}):", e)

        # mark booking as notified today (ANTI-SPAM)
        with get_connection() as conn:
            conn.execute(text("""
                UPDATE bookings
                SET last_notified = CURRENT_DATE
                WHERE id = :id
            """), {"id": r["id"]})


def run():
    with get_connection() as conn:
        rows = conn.execute(text("""
            SELECT
                id,
                branch_id,
                customer_name,
                remaining_amount,
                notify_date,
                checkout_date
            FROM bookings
            WHERE remaining_amount > 0
              AND status = 'active'
              AND (
                  notify_date <= CURRENT_DATE
                  OR checkout_date < CURRENT_DATE
              )
              AND (
                  last_notified IS NULL
                  OR last_notified < CURRENT_DATE
              )
        """)).mappings().all()

    if not rows:
        print("No debt notifications today")
        return

    asyncio.run(send_notifications(rows))


if __name__ == "__main__":
    run()
