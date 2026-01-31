import sys
import asyncio
from datetime import date
from sqlalchemy import text

# allow imports from backend
sys.path.append("/app/backend")

from db import get_connection
from bot.bot import bot   # aiogram Bot instance


# ================== TRANSLATIONS ==================

MESSAGES = {
    "uz": {
        "title": "⚠️ Qarzdor bron bo‘yicha eslatma",
        "today": "⏰ Bugun eslatma kuni",
        "overdue": "⚠️ Qarzdorlik muddati o‘tgan",
        "checkout": "🚨 Bron muddati o‘tgan (checkout o‘tib ketgan)",
        "customer": "👤 Mijoz",
        "branch": "🏨 Filial",
        "debt": "💰 Qarzdorlik",
        "notify": "📅 Belgilangan sana",
        "checkout_date": "🚪 Chiqib ketish sanasi"
    },
    "ru": {
        "title": "⚠️ Напоминание о задолженности",
        "today": "⏰ Сегодня день напоминания",
        "overdue": "⚠️ Просроченная задолженность",
        "checkout": "🚨 Срок проживания истёк",
        "customer": "👤 Клиент",
        "branch": "🏨 Филиал",
        "debt": "💰 Задолженность",
        "notify": "📅 Назначенная дата",
        "checkout_date": "🚪 Выезд"
    }
}


# ================== MAIN LOGIC ==================

async def send_notifications(rows):
    today = date.today()

    for r in rows:
        # determine status
        if r["checkout_date"] < today:
            status_key = "checkout"
        elif r["notify_date"] < today:
            status_key = "overdue"
        else:
            status_key = "today"

        # get users for this branch
        with get_connection() as conn:
            users = conn.execute(text("""
                SELECT u.telegram_id, u.language
                FROM users u
                JOIN user_branches ub ON ub.user_id = u.id
                WHERE ub.branch_id = :bid
                  AND u.telegram_id IS NOT NULL
                  AND u.is_active = TRUE
            """), {"bid": r["branch_id"]}).mappings().all()

        if not users:
            continue

        for u in users:
            lang = u.get("language") or "ru"
            t = MESSAGES.get(lang, MESSAGES["ru"])

            msg = (
                f"{t['title']}\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"{t[status_key]}\n"
                f"{t['customer']}: {r['customer_name']}\n"
                f"{t['branch']}: {r['branch_id']}\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"{t['debt']}: `{r['remaining_amount']}` so‘m\n"
                f"{t['notify']}: {r['notify_date']}\n"
                f"{t['checkout_date']}: {r['checkout_date']}\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
            )

            try:
                await bot.send_message(
                    u["telegram_id"],
                    msg,
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"Telegram send failed ({u['telegram_id']}):", e)

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
