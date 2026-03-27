import os
import sys
import asyncio
from datetime import date
from sqlalchemy import text

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.append(BACKEND_DIR)

from db import (  # noqa: E402
    get_connection,
    list_active_device_tokens_db,
    deactivate_device_token_db,
    create_user_notification_db,
    get_system_setting_db,
    set_system_setting_db,
)
from bot.bot import bot  # noqa: E402
from push.fcm_sender import send_push_to_tokens  # noqa: E402


MESSAGES = {
    "uz": {
        "title": "Qarzdor bron bo'yicha eslatma",
        "today": "Bugun eslatma kuni",
        "overdue": "Qarzdorlik muddati o'tgan",
        "checkout": "Bron muddati o'tgan",
        "customer": "Mijoz",
        "contact": "Aloqa",
        "branch": "Filial",
        "debt": "Qarzdorlik",
        "notify": "Belgilangan sana",
        "checkout_date": "Chiqib ketish sanasi",
        "push_title": "Qarz eslatmasi",
        "push_body": "{customer} bo'yicha {debt} so'm qarzdorlik",
        "currency": "so'm",
    },
    "ru": {
        "title": "Напоминание о задолженности",
        "today": "Сегодня день напоминания",
        "overdue": "Просроченная задолженность",
        "checkout": "Срок проживания истек",
        "customer": "Клиент",
        "contact": "Контакт",
        "branch": "Филиал",
        "debt": "Задолженность",
        "notify": "Назначенная дата",
        "checkout_date": "Выезд",
        "push_title": "Напоминание о долге",
        "push_body": "По клиенту {customer} долг {debt} сум",
        "currency": "сум",
    },
}


async def send_notifications(rows):
    today = date.today()
    sent_users = 0
    sent_rows = 0

    for r in rows:
        if r["checkout_date"] < today:
            status_key = "checkout"
        elif r["notify_date"] < today:
            status_key = "overdue"
        else:
            status_key = "today"

        with get_connection() as conn:
            users = conn.execute(text("""
                SELECT u.id, u.telegram_id, u.language
                FROM users u
                JOIN user_branches ub ON ub.user_id = u.id
                WHERE ub.branch_id = :bid
                  AND u.is_active = TRUE
                  AND u.notify_enabled = TRUE
            """), {"bid": r["branch_id"]}).mappings().all()

        if not users:
            continue

        for u in users:
            lang = u.get("language") or "ru"
            t = MESSAGES.get(lang, MESSAGES["ru"])

            dedupe_key = f"debt:{u['id']}:{r['id']}:{today.isoformat()}"
            create_user_notification_db(
                user_id=int(u["id"]),
                notif_type="debt_reminder",
                title=t["push_title"],
                body=t["push_body"].format(
                    customer=r["customer_name"],
                    debt=r["remaining_amount"],
                ),
                payload={
                    "booking_id": r["id"],
                    "branch_id": r["branch_id"],
                    "branch_name": r["branch_name"],
                    "customer_name": r["customer_name"],
                    "remaining_amount": str(r["remaining_amount"]),
                    "notify_date": str(r["notify_date"]),
                    "checkout_date": str(r["checkout_date"]),
                    "status_key": status_key,
                },
                dedupe_key=dedupe_key,
            )

            if u.get("telegram_id"):
                msg = (
                    f"{t['title']}\n\n"
                    f"{t[status_key]}\n"
                    f"{t['customer']}: {r['customer_name']}\n"
                    f"{t['contact']}: {r['contact'] or '-'}\n"
                    f"{t['branch']}: {r['branch_name']}\n"
                    f"{t['debt']}: {r['remaining_amount']} {t['currency']}\n"
                    f"{t['notify']}: {r['notify_date']}\n"
                    f"{t['checkout_date']}: {r['checkout_date']}"
                )

                try:
                    await bot.send_message(u["telegram_id"], msg)
                except Exception as e:
                    print(f"Telegram send failed ({u['telegram_id']}):", e)

            tokens = list_active_device_tokens_db(int(u["id"]))
            if tokens:
                push_result = send_push_to_tokens(
                    tokens=tokens,
                    title=t["push_title"],
                    body=t["push_body"].format(
                        customer=r["customer_name"],
                        debt=r["remaining_amount"],
                    ),
                    data={
                        "type": "debt_reminder",
                        "booking_id": str(r["id"]),
                        "branch_id": str(r["branch_id"]),
                        "customer_name": str(r["customer_name"]),
                        "remaining_amount": str(r["remaining_amount"]),
                        "notify_date": str(r["notify_date"]),
                        "checkout_date": str(r["checkout_date"]),
                    },
                )

                for bad_token in push_result.get("invalid_tokens", []):
                    try:
                        deactivate_device_token_db(bad_token)
                    except Exception as e:
                        print(f"Failed to deactivate bad token: {e}")

                if push_result.get("disabled"):
                    print("Push disabled:", push_result.get("errors"))
            sent_users += 1

        with get_connection() as conn:
            conn.execute(text("""
                UPDATE bookings
                SET last_notified = CURRENT_DATE
                WHERE id = :id
            """), {"id": r["id"]})
        sent_rows += 1

    await bot.session.close()
    return {"processed_bookings": sent_rows, "processed_users": sent_users}


def _is_true(value) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def run(force: bool = False):
    enabled = _is_true(get_system_setting_db("debt_notify_enabled", "1"))
    force_from_db = _is_true(get_system_setting_db("debt_notify_force", "0"))
    force_run = bool(force or force_from_db)

    if not enabled and not force_run:
        print("Debt notify cron is disabled by system_settings")
        return {"ok": True, "disabled": True, "rows": 0}

    with get_connection() as conn:
        sql = """
            SELECT
                b.id,
                b.branch_id,
                br.name AS branch_name,
                b.customer_name,
                b.contact,
                b.remaining_amount,
                b.notify_date,
                b.checkout_date
            FROM bookings b
            JOIN branches br ON br.id = b.branch_id
            WHERE b.remaining_amount > 0
              AND b.status = 'active'
              AND (
                    b.notify_date <= CURRENT_DATE
                    OR b.checkout_date < CURRENT_DATE
                  )
        """
        if not force_run:
            sql += """
              AND (
                    b.last_notified IS NULL
                    OR b.last_notified < CURRENT_DATE
                  )
            """
        rows = conn.execute(text(sql)).mappings().all()

    if not rows:
        print("No debt notifications today")
        if force_from_db:
            set_system_setting_db("debt_notify_force", "0")
        return {"ok": True, "rows": 0, "forced": force_run}

    result = asyncio.run(send_notifications(rows))

    if force_from_db:
        set_system_setting_db("debt_notify_force", "0")

    return {
        "ok": True,
        "rows": len(rows),
        "forced": force_run,
        **(result or {}),
    }


if __name__ == "__main__":
    run()
