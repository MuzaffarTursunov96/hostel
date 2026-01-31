import sys
import os
import asyncio
from sqlalchemy import text

sys.path.append("/app/backend")

from db import get_connection
from bot.bot import bot   # aiogram Bot instance

async def send_notifications(rows):
    for r in rows:
        with get_connection() as conn:
            users = conn.execute(text("""
                SELECT u.telegram_id
                FROM users u
                JOIN user_branches ub ON ub.user_id = u.id
                WHERE ub.branch_id = :bid
                  AND u.telegram_id IS NOT NULL
                  AND u.is_active = TRUE
            """), {"bid": r["branch_id"]}).fetchall()

        msg = (
            "⚠️ *Qarzdor bron bo‘yicha eslatma*\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Mijoz:* {r['customer_name']}\n"
            f"🏨 *Filial ID:* {r['branch_id']}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 *Qarzdorlik:* `{r['remaining_amount']}` so‘m\n"
            f"📅 *Bugungi sana:* {r.get('notify_date', '')}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "❗ Iltimos, to‘lovni amalga oshiring"
        )


        for u in users:
            try:
                await bot.send_message(
                    u.telegram_id,
                    msg,
                    parse_mode="Markdown"
                )

            except Exception as e:
                print("Telegram send failed:", e)


def run():
    with get_connection() as conn:
        rows = conn.execute(text("""
            SELECT
                id,
                branch_id,
                customer_name,
                remaining_amount
            FROM bookings
            WHERE remaining_amount > 0
              AND notify_date = CURRENT_DATE
              AND status = 'active'
        """)).mappings().all()

    if not rows:
        print("No debt notifications today")
        return

    asyncio.run(send_notifications(rows))


if __name__ == "__main__":
    run()
