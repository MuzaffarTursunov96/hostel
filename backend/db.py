from datetime import date, timedelta
import json
from security import hash_password, verify_password
from database import engine
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from time_utils import app_today, app_now_naive

_hourly_column_checked = False
_pricing_columns_checked = False
_branch_contact_columns_checked = False

def get_connection():
    return engine.begin()


def _credentials_match(username, password) -> bool:
    """Case-insensitive, trim-safe comparison for weak credentials."""
    if username is None or password is None:
        return False
    return str(username).strip().casefold() == str(password).strip().casefold()


def _username_exists(conn, username, exclude_user_id=None) -> bool:
    username_value = str(username or "").strip()
    if not username_value:
        return False

    if exclude_user_id is None:
        row = conn.execute(text("""
            SELECT 1
            FROM users
            WHERE lower(username) = lower(:u)
            LIMIT 1
        """), {"u": username_value}).fetchone()
    else:
        row = conn.execute(text("""
            SELECT 1
            FROM users
            WHERE lower(username) = lower(:u)
              AND id <> :exclude_user_id
            LIMIT 1
        """), {
            "u": username_value,
            "exclude_user_id": exclude_user_id
        }).fetchone()

    return row is not None


def init_db():
    with get_connection() as conn:

        # ---------- BRANCHES ----------
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS branches (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            address TEXT,
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            contact_phone TEXT,
            contact_telegram TEXT,
            created_by INTEGER
        )
        """))

        # ---------- ROOMS ----------
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS rooms (
            id SERIAL PRIMARY KEY,
            room_name TEXT,
            number TEXT NOT NULL,
            description TEXT,
            branch_id INTEGER NOT NULL,
            UNIQUE(number, branch_id),
            FOREIGN KEY(branch_id) REFERENCES branches(id) ON DELETE CASCADE
        )
        """))

        # ---------- GUESTS ----------
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS booking_guests (
            id SERIAL PRIMARY KEY,
            booking_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,
            role TEXT DEFAULT 'secondary',

            FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
            FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
        );

        """))






        # ---------- CUSTOMERS ----------
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY,
            branch_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            passport_id TEXT,
            contact TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))

        # ---------- LICENSES ----------
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS licenses (
                id SERIAL PRIMARY KEY,
                license_key VARCHAR(64) UNIQUE NOT NULL,
                device_id VARCHAR(128),
                is_active BOOLEAN DEFAULT TRUE,
                expires_at TIMESTAMP NULL,
                is_trial BOOLEAN DEFAULT FALSE,
                trial_days INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))

        # ---------- CUSTOMER PASSPORT IMAGES ----------
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS customer_passport_images (
            id SERIAL PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
        )
        """))

        # ---------- ROOM IMAGES ----------
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS room_images (
            id SERIAL PRIMARY KEY,
            room_id INTEGER NOT NULL,
            branch_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            is_cover BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
            FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE CASCADE
        )
        """))

        # ---------- BEDS ----------
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS beds (
            id SERIAL PRIMARY KEY,
            room_id INTEGER NOT NULL,
            status TEXT DEFAULT 'free',
            branch_id INTEGER NOT NULL,
            bed_number INTEGER,
            bed_type TEXT NOT NULL DEFAULT 'single',
            FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE,
            FOREIGN KEY(branch_id) REFERENCES branches(id) ON DELETE CASCADE
        )
        """))

        # ---------- BOOKINGS ----------
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS bookings (
            id SERIAL PRIMARY KEY,
            branch_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            contact TEXT,
            passport_id TEXT,
            room_id INTEGER NOT NULL,
            bed_id INTEGER NOT NULL,

            total_amount NUMERIC NOT NULL,
            paid_amount NUMERIC NOT NULL DEFAULT 0,
            remaining_amount NUMERIC NOT NULL,
            payment_status TEXT NOT NULL,

            checkin_date DATE NOT NULL,
            checkout_date DATE NOT NULL,
            is_hourly BOOLEAN NOT NULL DEFAULT FALSE,
            status TEXT DEFAULT 'active',
            booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notify_date DATE,
            last_notified DATE,

            FOREIGN KEY(branch_id) REFERENCES branches(id),
            FOREIGN KEY(room_id) REFERENCES rooms(id),
            FOREIGN KEY(bed_id) REFERENCES beds(id)
        )
        """))

        # ---------- BOOKING REFUNDS ----------
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS booking_refunds (
            id SERIAL PRIMARY KEY,
            booking_id INTEGER NOT NULL,
            branch_id INTEGER NOT NULL,
            refunded_amount NUMERIC NOT NULL,
            refunded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            refunded_by TEXT DEFAULT 'admin',
            note TEXT,

            FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
            FOREIGN KEY (branch_id) REFERENCES branches(id)
        )
        """))

        # ---------- EXPENSES ----------
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
            branch_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            amount NUMERIC NOT NULL,
            expense_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(branch_id) REFERENCES branches(id)
        )
        """))

        # ---------- BOOKING PAYMENTS ----------
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS booking_payments (
            id SERIAL PRIMARY KEY,
            booking_id INTEGER NOT NULL,
            branch_id INTEGER NOT NULL,
            paid_amount NUMERIC NOT NULL,
            paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            paid_by TEXT DEFAULT 'customer',

            FOREIGN KEY(booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
            FOREIGN KEY(branch_id) REFERENCES branches(id)
        )
        """))

        # ---------- USERS ----------
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL DEFAULT 'USER',
            password_hash TEXT NOT NULL,
            telegram_id BIGINT UNIQUE,
            is_admin BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE,
            admin_expires_at TIMESTAMP NULL,
            branch_id INTEGER,
            created_by INTEGER,
            language TEXT DEFAULT 'ru',
            notify_enabled BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))

        # ---------- USER BRANCHES ----------
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_branches (
            user_id INTEGER NOT NULL,
            branch_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, branch_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (branch_id) REFERENCES branches(id)
        )
        """))

        # ---------- USER DEVICES (MOBILE PUSH TOKENS) ----------
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_devices (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            fcm_token TEXT UNIQUE NOT NULL,
            platform TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """))

        # ---------- USER IN-APP NOTIFICATIONS ----------
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_notifications (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            notif_type TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            payload TEXT,
            dedupe_key TEXT UNIQUE,
            is_read BOOLEAN DEFAULT FALSE,
            read_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """))

        # ---------- SYSTEM SETTINGS ----------
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))

        # ---------- DEFAULT BRANCH ----------
        conn.execute(text("""
        INSERT INTO branches (name)
        SELECT 'Main Branch'
        WHERE NOT EXISTS (SELECT 1 FROM branches)
        """))
    print("✅ Database initialized successfully.")


def set_app_expiry_db(expires_at):
    ensure_system_settings_table()
    with get_connection() as conn:
        conn.execute(text("""
            INSERT INTO system_settings (key, value, updated_at)
            VALUES ('app_expires_at', :value, CURRENT_TIMESTAMP)
            ON CONFLICT (key)
            DO UPDATE SET
                value = EXCLUDED.value,
                updated_at = CURRENT_TIMESTAMP
        """), {
            "value": expires_at.isoformat() if expires_at else None
        })


def get_app_expiry_db():
    from datetime import datetime

    ensure_system_settings_table()
    with get_connection() as conn:
        row = conn.execute(text("""
            SELECT value
            FROM system_settings
            WHERE key = 'app_expires_at'
        """)).mappings().fetchone()

    raw = row["value"] if row else None
    if not raw:
        return None

    try:
        return datetime.fromisoformat(raw)
    except Exception:
        return None


def set_system_setting_db(key: str, value: str | None):
    ensure_system_settings_table()
    k = str(key or "").strip()
    if not k:
        raise ValueError("key required")
    with get_connection() as conn:
        conn.execute(text("""
            INSERT INTO system_settings (key, value, updated_at)
            VALUES (:key, :value, CURRENT_TIMESTAMP)
            ON CONFLICT (key)
            DO UPDATE SET
                value = EXCLUDED.value,
                updated_at = CURRENT_TIMESTAMP
        """), {
            "key": k,
            "value": None if value is None else str(value),
        })


def get_system_setting_db(key: str, default: str | None = None):
    ensure_system_settings_table()
    k = str(key or "").strip()
    if not k:
        return default
    with get_connection() as conn:
        row = conn.execute(text("""
            SELECT value
            FROM system_settings
            WHERE key = :key
        """), {"key": k}).mappings().fetchone()
    if not row:
        return default
    return row.get("value") if row.get("value") is not None else default


def get_booking_prepayment_config_db():
    enabled_raw = str(get_system_setting_db("booking_prepayment_enabled", "0") or "0").strip().lower()
    enabled = enabled_raw in {"1", "true", "yes", "on"}

    mode = str(get_system_setting_db("booking_prepayment_mode", "percent") or "percent").strip().lower()
    if mode not in {"percent", "fixed"}:
        mode = "percent"

    try:
        value = float(get_system_setting_db("booking_prepayment_value", "0") or 0)
    except Exception:
        value = 0.0

    if value < 0:
        value = 0.0

    return {
        "enabled": enabled,
        "mode": mode,
        "value": value,
    }


def set_booking_prepayment_config_db(enabled: bool, mode: str, value: float):
    mode_norm = str(mode or "").strip().lower()
    if mode_norm not in {"percent", "fixed"}:
        raise ValueError("mode must be percent or fixed")

    value_num = float(value)
    if value_num < 0:
        raise ValueError("value must be >= 0")
    if mode_norm == "percent" and value_num > 100:
        raise ValueError("percent must be <= 100")

    set_system_setting_db("booking_prepayment_enabled", "1" if bool(enabled) else "0")
    set_system_setting_db("booking_prepayment_mode", mode_norm)
    set_system_setting_db("booking_prepayment_value", str(value_num))


def is_app_expired_db(now_utc=None):
    from datetime import datetime

    expires_at = get_app_expiry_db()
    if not expires_at:
        return False

    if now_utc is None:
        now_utc = app_now_naive()

    return now_utc > expires_at


def ensure_system_settings_table():
    with get_connection() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))


def ensure_user_devices_table():
    with get_connection() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_devices (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                fcm_token TEXT UNIQUE NOT NULL,
                platform TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """))


def ensure_user_notifications_table():
    with get_connection() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_notifications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                notif_type TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                payload TEXT,
                dedupe_key TEXT UNIQUE,
                is_read BOOLEAN DEFAULT FALSE,
                read_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """))


def ensure_admin_expiry_column():
    with get_connection() as conn:
        conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS admin_expires_at TIMESTAMP NULL
        """))


def ensure_bookings_hourly_column():
    global _hourly_column_checked
    if _hourly_column_checked:
        return
    with get_connection() as conn:
        conn.execute(text("""
            ALTER TABLE bookings
            ADD COLUMN IF NOT EXISTS is_hourly BOOLEAN NOT NULL DEFAULT FALSE
        """))
    _hourly_column_checked = True


def ensure_pricing_columns():
    global _pricing_columns_checked
    if _pricing_columns_checked:
        return
    with get_connection() as conn:
        conn.execute(text("""
            ALTER TABLE rooms
            ADD COLUMN IF NOT EXISTS fixed_price NUMERIC NULL
        """))
        conn.execute(text("""
            ALTER TABLE beds
            ADD COLUMN IF NOT EXISTS fixed_price NUMERIC NULL
        """))
        conn.execute(text("""
            ALTER TABLE rooms
            ADD COLUMN IF NOT EXISTS room_type TEXT NULL
        """))
    _pricing_columns_checked = True


def ensure_branch_contact_columns():
    global _branch_contact_columns_checked
    if _branch_contact_columns_checked:
        return
    with get_connection() as conn:
        conn.execute(text("""
            ALTER TABLE branches
            ADD COLUMN IF NOT EXISTS contact_phone TEXT
        """))
        conn.execute(text("""
            ALTER TABLE branches
            ADD COLUMN IF NOT EXISTS contact_telegram TEXT
        """))
    _branch_contact_columns_checked = True

def get_rooms_with_beds(branch_id):
    ensure_pricing_columns()
    today = app_today().isoformat()
    with get_connection() as conn:
        result = conn.execute(text("""
            SELECT 
                rooms.id,
                rooms.number AS room_number,
                COALESCE(rooms.room_name, rooms.number) AS room_name,
                COUNT(beds.id) AS bed_count,
                COUNT(DISTINCT CASE WHEN bk_active.id IS NOT NULL THEN beds.id END) AS busy_beds,
                rooms.fixed_price,
                rooms.room_type
            FROM rooms
            LEFT JOIN beds 
                ON beds.room_id = rooms.id
               AND beds.branch_id = rooms.branch_id
            LEFT JOIN bookings bk_active
                ON bk_active.bed_id = beds.id
               AND bk_active.branch_id = rooms.branch_id
               AND bk_active.status = 'active'
               AND bk_active.checkin_date <= :today
               AND bk_active.checkout_date > :today
            WHERE rooms.branch_id = :branch_id
            GROUP BY rooms.id, rooms.number, rooms.room_name, rooms.fixed_price, rooms.room_type
            ORDER BY rooms.id ASC
        """), {"branch_id": branch_id, "today": today})

        rows = result.mappings().all()

    return [
        (lambda r: {
            "id": r["id"],
            "room_number": r["room_number"],
            "room_name": r["room_name"],
            "bed_count": r["bed_count"],
            "busy_beds": int(r["busy_beds"] or 0),
            "available_beds": (0 if (
                ("oilav" in str((r["room_type"] or "")).strip().lower())
                or ("family" in str((r["room_type"] or "")).strip().lower())
                or ("сем" in str((r["room_type"] or "")).strip().lower())
            ) and int(r["busy_beds"] or 0) > 0 else max(int(r["bed_count"] or 0) - int(r["busy_beds"] or 0), 0)),
            "occupancy_status": (
                "full" if (
                    int(r["bed_count"] or 0) <= 0
                    or (
                        (
                            ("oilav" in str((r["room_type"] or "")).strip().lower())
                            or ("family" in str((r["room_type"] or "")).strip().lower())
                            or ("сем" in str((r["room_type"] or "")).strip().lower())
                        ) and int(r["busy_beds"] or 0) > 0
                    )
                    or max(int(r["bed_count"] or 0) - int(r["busy_beds"] or 0), 0) <= 0
                ) else (
                    "partial" if int(r["busy_beds"] or 0) > 0 else "free"
                )
            ),
            "fixed_price": float(r["fixed_price"]) if r["fixed_price"] is not None else None,
            "room_type": (r["room_type"] or "").strip() or None,
        })(r)
        for r in rows
    ]


def get_available_beds(branch_id, room_id, checkin_date, checkout_date):
    ensure_pricing_columns()
    with get_connection() as conn:
        result = conn.execute(text("""
            SELECT 
                b.id,
                b.bed_number,
                b.room_id,
                b.bed_type,
                b.fixed_price,
                r.fixed_price AS room_fixed_price,
                COALESCE(b.fixed_price, r.fixed_price) AS effective_price
            FROM beds b
            JOIN rooms r ON r.id = b.room_id
            WHERE b.branch_id = :branch_id
              AND b.room_id = :room_id
              AND NOT EXISTS (
                  SELECT 1
                  FROM bookings bk
                  WHERE bk.branch_id = b.branch_id
                    AND bk.bed_id = b.id
                    AND bk.status = 'active'
                    AND bk.checkin_date < :checkout_date
                    AND bk.checkout_date > :checkin_date
              )
            ORDER BY b.id
        """), {
            "branch_id": branch_id,
            "room_id": room_id,
            "checkout_date": checkout_date,
            "checkin_date": checkin_date
        })

        return result.mappings().all()



def add_booking_guest(booking_id, customer_id):
    with get_connection() as conn:
        conn.execute(text("""
            INSERT INTO booking_guests (booking_id, customer_id)
            VALUES (:booking_id, :customer_id)
        """), {
            "booking_id": booking_id,
            "customer_id": customer_id
        })



def add_booking(
            branch_id,
            customer_name,
            passport_id,
            contact,
            room_id,
            bed_id,
            total_amount,
            paid_amount,
            checkin_date,
            checkout_date,
            notify_date,
            is_hourly=False,
        ):
    ensure_bookings_hourly_column()

    if (not is_hourly and checkout_date <= checkin_date) or (is_hourly and checkout_date < checkin_date):
        raise HTTPException(
            status_code=400,
            detail="For same-day booking, enable hourly booking."
        )
    if is_hourly and checkout_date == checkin_date:
        checkout_date = checkin_date + timedelta(days=1)

    with get_connection() as conn:

        # -----------------------------
        # 1️⃣ Check bed availability
        # -----------------------------
        res = conn.execute(text("""
            SELECT COUNT(*) AS cnt
            FROM bookings
            WHERE branch_id = :branch_id
              AND bed_id = :bed_id
              AND status = 'active'
              AND NOT (
                  checkout_date <= :checkin_date
                  OR checkin_date >= :checkout_date
              )
        """), {
            "branch_id": branch_id,
            "bed_id": bed_id,
            "checkin_date": checkin_date,
            "checkout_date": checkout_date
        }).mappings().fetchone()

        if res["cnt"] > 0:
            raise Exception("❌ Bed is already booked for this period")

        # -----------------------------
        # 2️⃣ Calculate payment fields
        # -----------------------------
        paid_amount = float(paid_amount)
        total_amount = float(total_amount)
        remaining_amount = total_amount - paid_amount

        if remaining_amount <= 0:
            payment_status = "paid"
            remaining_amount = 0
        elif paid_amount > 0:
            payment_status = "partial"
        else:
            payment_status = "unpaid"

        # -----------------------------
        # 3️⃣ Insert booking
        # -----------------------------
        booking_id = conn.execute(text("""
                INSERT INTO bookings (
                    branch_id,
                    customer_name,
                    passport_id,
                    contact,
                    room_id,
                    bed_id,
                    total_amount,
                    paid_amount,
                    remaining_amount,
                    payment_status,
                    checkin_date,
                    checkout_date,
                    notify_date,
                    is_hourly,
                    status
                )
                VALUES (
                    :branch_id,
                    :customer_name,
                    :passport_id,
                    :contact,
                    :room_id,
                    :bed_id,
                    :total_amount,
                    :paid_amount,
                    :remaining_amount,
                    :payment_status,
                    :checkin_date,
                    :checkout_date,
                    :notify_date,
                    :is_hourly,
                    'active'
                )
                RETURNING id
            """), {
                "branch_id": branch_id,
                "customer_name": customer_name,
                "passport_id": passport_id,
                "contact": contact,
                "room_id": room_id,
                "bed_id": bed_id,
                "total_amount": total_amount,
                "paid_amount": paid_amount,
                "remaining_amount": remaining_amount,
                "payment_status": payment_status,
                "checkin_date": checkin_date,
                "checkout_date": checkout_date,
                "notify_date": notify_date,
                "is_hourly": bool(is_hourly),
            }).scalar()


        if paid_amount > 0:
            conn.execute(text("""
                INSERT INTO booking_payments (
                    booking_id,
                    branch_id,
                    paid_amount,
                    paid_by
                )
                VALUES (
                    :booking_id,
                    :branch_id,
                    :paid_amount,
                    :paid_by
                )
            """), {
                "booking_id": booking_id,
                "branch_id": branch_id,
                "paid_amount": paid_amount,
                "paid_by": "customer"
            })
        return booking_id

def get_default_branch_id(user_id: int):
    with get_connection() as conn:

        # 1️⃣ try user default
        row = conn.execute(text("""
            SELECT branch_id
            FROM users
            WHERE id = :user_id
        """), {"user_id": user_id}).mappings().fetchone()

        if row and row["branch_id"]:
            return row["branch_id"]

        # 2️⃣ fallback to first assigned branch
        row = conn.execute(text("""
            SELECT branch_id
            FROM user_branches
            WHERE user_id = :user_id
            ORDER BY branch_id
            LIMIT 1
        """), {"user_id": user_id}).mappings().fetchone()

        return row["branch_id"] if row else None


def is_bed_busy_today(branch_id, bed_id):
    today = app_today()

    with get_connection() as conn:
        row = conn.execute(text("""
            SELECT 1
            FROM bookings
            WHERE branch_id = :branch_id
              AND bed_id = :bed_id
              AND status = 'active'
              AND checkin_date <= :today
              AND checkout_date > :today
            LIMIT 1
        """), {
            "branch_id": branch_id,
            "bed_id": bed_id,
            "today": today
        }).mappings().fetchone()

        return row is not None


def get_active_booking_now(branch_id, bed_id):
    ensure_bookings_hourly_column()
    with get_connection() as conn:
        row = conn.execute(text("""
            SELECT *
            FROM bookings
            WHERE branch_id = :branch_id
              AND bed_id = :bed_id
              AND status = 'active'
              AND checkin_date <= CURRENT_DATE
              AND checkout_date > CURRENT_DATE
            LIMIT 1
        """), {
            "branch_id": branch_id,
            "bed_id": bed_id
        }).mappings().fetchone()

        return row


def migrate_payments():
    """
    PostgreSQL NOTE:
    This function existed for SQLite migrations.
    PostgreSQL schema is created upfront in init_db().
    Keeping function to avoid breaking imports.
    """
    return


def get_debt_summary(branch_id, from_date, to_date):
    """
    Returns total paid vs remaining debt
    for bookings whose checkout is in the given range
    """
    with get_connection() as conn:
        row = conn.execute(text("""
            SELECT
                COALESCE(SUM(paid_amount), 0) AS paid,
                COALESCE(SUM(remaining_amount), 0) AS remaining
            FROM bookings
            WHERE branch_id = :branch_id
              AND checkout_date BETWEEN :from_date AND :to_date
              AND status IN ('active', 'completed')
        """), {
            "branch_id": branch_id,
            "from_date": from_date,
            "to_date": to_date
        }).mappings().fetchone()

        return {
            "paid": row["paid"],
            "remaining": row["remaining"]
        }


def get_debts_by_range(branch_id, from_date, to_date):
    with get_connection() as conn:
        result = conn.execute(text("""
            SELECT
                b.id,
                b.room_id,
                b.customer_name,
                b.passport_id,
                b.contact,

                r.number AS room_number,
                COALESCE(r.room_name, r.number) AS room_name,
                beds.bed_number,
                beds.bed_type,

                b.total_amount,
                b.paid_amount,
                b.remaining_amount,
                b.checkin_date,
                b.checkout_date,

                -- 👇 second guests
                json_agg(
                    json_build_object(
                        'id', c.id,
                        'name', c.name
                    )
                ) FILTER (WHERE bg.id IS NOT NULL) AS second_guests

            FROM bookings b
            JOIN rooms r
                ON r.id = b.room_id
               AND r.branch_id = b.branch_id
            JOIN beds
                ON beds.id = b.bed_id

            LEFT JOIN booking_guests bg ON bg.booking_id = b.id
            LEFT JOIN customers c ON c.id = bg.customer_id

            WHERE b.branch_id = :branch_id
              AND b.remaining_amount > 0
              AND b.checkin_date >= :from_date
              AND b.checkin_date <= :to_date

            GROUP BY
                b.id,
                b.room_id,
                r.number,
                r.room_name,
                beds.bed_number,
                beds.bed_type

            ORDER BY b.checkin_date
        """), {
            "branch_id": branch_id,
            "from_date": from_date,
            "to_date": to_date
        })

        return result.mappings().all()



def pay_booking_amount(branch_id, booking_id, pay_amount, paid_by="customer"):
    if pay_amount <= 0:
        raise ValueError("Invalid payment amount")

    with get_connection() as conn:

        # get current totals
        row = conn.execute(text("""
            SELECT total_amount, paid_amount
            FROM bookings
            WHERE id = :booking_id
              AND branch_id = :branch_id
        """), {
            "booking_id": booking_id,
            "branch_id": branch_id
        }).mappings().fetchone()

        if not row:
            raise ValueError("Booking not found")

        total = row["total_amount"]
        paid = row["paid_amount"]

        new_paid = paid + pay_amount
        remaining = max(total - new_paid, 0)

        payment_status = "paid" if remaining == 0 else "partial"

        # update booking
        conn.execute(text("""
            UPDATE bookings
            SET paid_amount = :paid_amount,
                remaining_amount = :remaining_amount,
                payment_status = :payment_status
            WHERE id = :booking_id
              AND branch_id = :branch_id
        """), {
            "paid_amount": new_paid,
            "remaining_amount": remaining,
            "payment_status": payment_status,
            "booking_id": booking_id,
            "branch_id": branch_id
        })

        # insert payment history
        conn.execute(text("""
            INSERT INTO booking_payments (
                booking_id,
                branch_id,
                paid_amount,
                paid_by
            )
            VALUES (
                :booking_id,
                :branch_id,
                :paid_amount,
                :paid_by
            )
        """), {
            "booking_id": booking_id,
            "branch_id": branch_id,
            "paid_amount": pay_amount,
            "paid_by": paid_by
        })





def add_expense(branch_id, title, category, amount, expense_date):
    with get_connection() as conn:
        conn.execute(text("""
            INSERT INTO expenses (
                branch_id,
                title,
                category,
                amount,
                expense_date
            )
            VALUES (
                :branch_id,
                :title,
                :category,
                :amount,
                :expense_date
            )
        """), {
            "branch_id": branch_id,
            "title": title,
            "category": category,
            "amount": amount,
            "expense_date": expense_date
        })


def get_expenses_by_month(branch_id, year, month):
    with get_connection() as conn:
        result = conn.execute(text("""
            SELECT *
            FROM expenses
            WHERE branch_id = :branch_id
              AND EXTRACT(YEAR FROM expense_date) = :year
              AND EXTRACT(MONTH FROM expense_date) = :month
            ORDER BY expense_date DESC
        """), {
            "branch_id": branch_id,
            "year": year,
            "month": month
        })

        return result.mappings().all()


def get_monthly_finance(branch_id, year, month):
    with get_connection() as conn:

        # INCOME + DEBT
        row = conn.execute(text("""
            SELECT
                COALESCE(SUM(paid_amount), 0) AS income,
                COALESCE(SUM(remaining_amount), 0) AS debt
            FROM bookings
            WHERE branch_id = :branch_id
              AND EXTRACT(YEAR FROM booking_date) = :year
              AND EXTRACT(MONTH FROM booking_date) = :month
              AND status NOT IN ('canceled', 'cancelled')
        """), {
            "branch_id": branch_id,
            "year": year,
            "month": month
        }).mappings().fetchone()

        income = row["income"]
        debt = row["debt"]

        # EXPENSES
        expenses = conn.execute(text("""
            SELECT COALESCE(SUM(amount), 0) AS expenses
            FROM expenses
            WHERE branch_id = :branch_id
              AND EXTRACT(YEAR FROM expense_date) = :year
              AND EXTRACT(MONTH FROM expense_date) = :month
        """), {
            "branch_id": branch_id,
            "year": year,
            "month": month
        }).scalar()


        refunds = conn.execute(text("""
            SELECT COALESCE(SUM(refunded_amount), 0)
            FROM booking_refunds
            WHERE branch_id = :branch_id
              AND EXTRACT(YEAR FROM refunded_at) = :year
              AND EXTRACT(MONTH FROM refunded_at) = :month
        """), {
            "branch_id": branch_id,
            "year": year,
            "month": month
        }).scalar()

        return {
            "income": income,
            "expenses": expenses,
            "refunds": refunds,
            "debt": debt
        }



def get_yearly_finance(branch_id, year):
    with get_connection() as conn:

        row = conn.execute(text("""
            SELECT
                COALESCE(SUM(paid_amount), 0) AS income,
                COALESCE(SUM(remaining_amount), 0) AS debt
            FROM bookings
            WHERE branch_id = :branch_id
              AND EXTRACT(YEAR FROM booking_date) = :year
              AND status NOT IN ('canceled', 'cancelled')
        """), {
            "branch_id": branch_id,
            "year": year
        }).mappings().fetchone()

        income = row["income"]
        debt = row["debt"]

        expenses = conn.execute(text("""
            SELECT COALESCE(SUM(amount), 0) AS expenses
            FROM expenses
            WHERE branch_id = :branch_id
              AND EXTRACT(YEAR FROM expense_date) = :year
        """), {
            "branch_id": branch_id,
            "year": year
        }).scalar()

        return {
            "income": income,
            "expenses": expenses,
            "debt": debt
        }


def get_admin_finance_report_db(
    admin_id: int,
    year: int | None = None,
    month: int | None = None,
    is_root: bool = False
):
    with get_connection() as conn:
        if is_root:
            branch_rows = conn.execute(text("""
                SELECT id, name
                FROM branches
                ORDER BY id
            """)).mappings().all()
        else:
            branch_rows = conn.execute(text("""
                SELECT DISTINCT b.id, b.name
                FROM branches b
                LEFT JOIN user_branches ub
                  ON ub.branch_id = b.id
                WHERE b.created_by = :aid
                   OR ub.user_id = :aid
                ORDER BY b.id
            """), {"aid": admin_id}).mappings().all()

        result_rows = []
        total_income = 0.0
        total_expenses = 0.0
        total_refunds = 0.0
        total_debt = 0.0

        for b in branch_rows:
            bid = int(b["id"])
            income_debt = conn.execute(text("""
                SELECT
                    COALESCE(SUM(paid_amount), 0) AS income,
                    COALESCE(SUM(remaining_amount), 0) AS debt
                FROM bookings
                WHERE branch_id = :branch_id
                  AND status NOT IN ('canceled', 'cancelled')
                  AND (:year IS NULL OR EXTRACT(YEAR FROM booking_date) = :year)
                  AND (:month IS NULL OR EXTRACT(MONTH FROM booking_date) = :month)
            """), {
                "branch_id": bid,
                "year": year,
                "month": month
            }).mappings().fetchone()

            expenses = conn.execute(text("""
                SELECT COALESCE(SUM(amount), 0) AS expenses
                FROM expenses
                WHERE branch_id = :branch_id
                  AND (:year IS NULL OR EXTRACT(YEAR FROM expense_date) = :year)
                  AND (:month IS NULL OR EXTRACT(MONTH FROM expense_date) = :month)
            """), {
                "branch_id": bid,
                "year": year,
                "month": month
            }).scalar() or 0

            refunds = conn.execute(text("""
                SELECT COALESCE(SUM(refunded_amount), 0) AS refunds
                FROM booking_refunds
                WHERE branch_id = :branch_id
                  AND (:year IS NULL OR EXTRACT(YEAR FROM refunded_at) = :year)
                  AND (:month IS NULL OR EXTRACT(MONTH FROM refunded_at) = :month)
            """), {
                "branch_id": bid,
                "year": year,
                "month": month
            }).scalar() or 0

            income = float(income_debt["income"] or 0)
            debt = float(income_debt["debt"] or 0)
            expenses = float(expenses)
            refunds = float(refunds)
            profit = income - expenses - refunds

            total_income += income
            total_expenses += expenses
            total_refunds += refunds
            total_debt += debt

            result_rows.append({
                "branch_id": bid,
                "branch_name": b["name"],
                "income": income,
                "expenses": expenses,
                "refunds": refunds,
                "debt": debt,
                "profit": profit,
            })

        return {
            "branches": result_rows,
            "totals": {
                "income": total_income,
                "expenses": total_expenses,
                "refunds": total_refunds,
                "debt": total_debt,
                "profit": total_income - total_expenses - total_refunds,
            }
        }





# ================= EXPENSE CATEGORY =================
def get_expense_category_stats(branch_id, year, month=None):
    with get_connection() as conn:

        if month:
            result = conn.execute(text("""
                SELECT category, SUM(amount) AS total
                FROM expenses
                WHERE branch_id = :branch_id
                  AND EXTRACT(YEAR FROM expense_date) = :year
                  AND EXTRACT(MONTH FROM expense_date) = :month
                GROUP BY category
            """), {
                "branch_id": branch_id,
                "year": year,
                "month": month
            })
        else:
            result = conn.execute(text("""
                SELECT category, SUM(amount) AS total
                FROM expenses
                WHERE branch_id = :branch_id
                  AND EXTRACT(YEAR FROM expense_date) = :year
                GROUP BY category
            """), {
                "branch_id": branch_id,
                "year": year
            })

        rows = result.mappings().all()
        return {r["category"]: r["total"] for r in rows}


def pay_booking_debt(branch_id, booking_id, pay_amount):
    if pay_amount <= 0:
        raise ValueError("Invalid payment amount")

    with get_connection() as conn:

        row = conn.execute(text("""
            SELECT paid_amount, remaining_amount
            FROM bookings
            WHERE id = :booking_id
              AND branch_id = :branch_id
        """), {
            "booking_id": booking_id,
            "branch_id": branch_id
        }).mappings().fetchone()

        if not row:
            raise ValueError("Booking not found")

        paid = row["paid_amount"]
        remaining = row["remaining_amount"]

        if pay_amount > remaining:
            raise ValueError("Payment exceeds remaining debt")

        new_paid = paid + pay_amount
        new_remaining = remaining - pay_amount
        status = "paid" if new_remaining == 0 else "partial"

        conn.execute(text("""
            UPDATE bookings
            SET paid_amount = :paid_amount,
                remaining_amount = :remaining_amount,
                payment_status = :status
            WHERE id = :booking_id
              AND branch_id = :branch_id
        """), {
            "paid_amount": new_paid,
            "remaining_amount": new_remaining,
            "status": status,
            "booking_id": booking_id,
            "branch_id": branch_id
        })


# ================= BRANCHES =================
def get_branches(user_id):
    ensure_branch_contact_columns()
    with get_connection() as conn:
        result = conn.execute(text("""
            SELECT
                b.id,
                b.name,
                b.address,
                b.latitude,
                b.longitude,
                b.contact_phone,
                b.contact_telegram
            FROM branches b
            JOIN user_branches ub ON ub.branch_id = b.id
            WHERE ub.user_id = :user_id
            ORDER BY b.name
        """), {"user_id": user_id})

        return result.mappings().all()


def add_branch(name, user_id):
    with get_connection() as conn:

        branch_id = conn.execute(text("""
            INSERT INTO branches (name)
            VALUES (:name)
            RETURNING id
        """), {"name": name.strip()}).scalar()

        conn.execute(text("""
            INSERT INTO user_branches (user_id, branch_id)
            VALUES (:user_id, :branch_id)
        """), {
            "user_id": user_id,
            "branch_id": branch_id
        })

        return branch_id   # 🔥 IMPORTANT


def update_branch(branch_id, new_name, user_id):
    with get_connection() as conn:

        result = conn.execute(text("""
            UPDATE branches
            SET name = :new_name
            WHERE id = :branch_id
              AND id IN (
                  SELECT branch_id
                  FROM user_branches
                  WHERE user_id = :user_id
              )
        """), {
            "new_name": new_name.strip(),
            "branch_id": branch_id,
            "user_id": user_id
        })

        if result.rowcount == 0:
            raise Exception("You are not allowed to modify this branch")


def get_payment_history(branch_id):
    with get_connection() as conn:
        result = conn.execute(text("""
            SELECT
                bp.paid_at,
                bp.paid_amount,
                bp.paid_by,
                b.customer_name,
                b.passport_id,
                r.number AS room_number,
                COALESCE(r.room_name, r.number) AS room_name,
                beds.bed_number
            FROM booking_payments bp
            JOIN bookings b ON b.id = bp.booking_id
            JOIN rooms r ON r.id = b.room_id
            JOIN beds ON beds.id = b.bed_id
            WHERE bp.branch_id = :branch_id
              AND b.status NOT IN ('canceled', 'cancelled')
            ORDER BY bp.paid_at DESC
        """), {"branch_id": branch_id})

        return result.mappings().all()


def get_payment_history_by_month(branch_id, year, month):
    with get_connection() as conn:
        result = conn.execute(text("""
            SELECT
                bp.paid_at,
                bp.paid_amount,
                bp.paid_by,

                b.customer_name,
                b.passport_id,
                b.room_id,

                r.number AS room_number,
                COALESCE(r.room_name, r.number) AS room_name,
                beds.bed_number,

                -- 👇 second guests (same pattern as active bookings)
                json_agg(
                    json_build_object(
                        'id', c.id,
                        'name', c.name
                    )
                ) FILTER (WHERE bg.id IS NOT NULL) AS second_guests

            FROM booking_payments bp
            JOIN bookings b ON b.id = bp.booking_id
            JOIN rooms r ON r.id = b.room_id
            JOIN beds ON beds.id = b.bed_id

            LEFT JOIN booking_guests bg ON bg.booking_id = b.id
            LEFT JOIN customers c ON c.id = bg.customer_id

            WHERE bp.branch_id = :branch_id
              AND EXTRACT(YEAR FROM bp.paid_at) = :year
              AND EXTRACT(MONTH FROM bp.paid_at) = :month
              AND b.status NOT IN ('canceled', 'cancelled')

            GROUP BY
                bp.paid_at,
                bp.paid_amount,
                bp.paid_by,
                b.customer_name,
                b.passport_id,
                b.room_id,
                r.number,
                r.room_name,
                beds.bed_number

            ORDER BY bp.paid_at DESC
        """), {
            "branch_id": branch_id,
            "year": year,
            "month": month
        })

        return result.mappings().all()






def get_payments_by_range(branch_id, start_date, end_date):
    with get_connection() as conn:
        result = conn.execute(text("""
            SELECT
                bp.paid_amount,
                bp.paid_at,
                bp.paid_by,

                b.customer_name,
                b.passport_id,
                b.contact,
                b.bed_id,
                r.number AS room_number,
                COALESCE(r.room_name, r.number) AS room_name,
                b.checkin_date,
                b.checkout_date

            FROM booking_payments bp
            JOIN bookings b ON b.id = bp.booking_id
            JOIN rooms r ON r.id = b.room_id

            WHERE bp.branch_id = :branch_id
              AND bp.paid_at::date BETWEEN :start_date AND :end_date
              AND b.status NOT IN ('canceled', 'cancelled')
            ORDER BY bp.paid_at DESC
        """), {
            "branch_id": branch_id,
            "start_date": start_date,
            "end_date": end_date
        })

        return result.mappings().all()


# def cancel_booking(booking_id: int, branch_id: int):
#     with get_connection() as conn:
#         conn.execute(text("""
#             UPDATE bookings
#             SET status = 'canceled'
#             WHERE id = :booking_id
#               AND branch_id = :branch_id
#               AND status = 'active'
#         """), {
#             "booking_id": booking_id,
#             "branch_id": branch_id
#         })

def cancel_booking(booking_id: int, branch_id: int):
    with get_connection() as conn:
        conn.execute(text("""
            UPDATE bookings
            SET
                status = 'canceled',
                remaining_amount = 0,
                payment_status = 'canceled'
            WHERE id = :booking_id
              AND branch_id = :branch_id
              AND status = 'active'
        """), {
            "booking_id": booking_id,
            "branch_id": branch_id
        })

def end_booking_now(booking_id: int, branch_id: int, settle_debt: bool = False):
    with get_connection() as conn:
        if settle_debt:
            row = conn.execute(text("""
                SELECT remaining_amount
                FROM bookings
                WHERE id = :booking_id
                  AND branch_id = :branch_id
                  AND status = 'active'
                  AND checkin_date <= CURRENT_DATE
                LIMIT 1
            """), {
                "booking_id": booking_id,
                "branch_id": branch_id
            }).mappings().fetchone()

            if row:
                remain = float(row["remaining_amount"] or 0)
                if remain > 0:
                    conn.execute(text("""
                        UPDATE bookings
                        SET
                            paid_amount = paid_amount + :remain,
                            remaining_amount = 0,
                            payment_status = 'paid'
                        WHERE id = :booking_id
                          AND branch_id = :branch_id
                    """), {
                        "remain": remain,
                        "booking_id": booking_id,
                        "branch_id": branch_id
                    })

                    conn.execute(text("""
                        INSERT INTO booking_payments (
                            booking_id,
                            branch_id,
                            paid_amount,
                            paid_by
                        )
                        VALUES (
                            :booking_id,
                            :branch_id,
                            :paid_amount,
                            :paid_by
                        )
                    """), {
                        "booking_id": booking_id,
                        "branch_id": branch_id,
                        "paid_amount": remain,
                        "paid_by": "manager_end"
                    })

        res = conn.execute(text("""
            UPDATE bookings
            SET
                status = 'completed',
                checkout_date = CASE
                    WHEN checkout_date > CURRENT_DATE THEN CURRENT_DATE
                    ELSE checkout_date
                END
            WHERE id = :booking_id
              AND branch_id = :branch_id
              AND status = 'active'
              AND checkin_date <= CURRENT_DATE
        """), {
            "booking_id": booking_id,
            "branch_id": branch_id
        })

        if (res.rowcount or 0) == 0:
            raise ValueError("No active booking found to end")


def update_booking(booking_id, bed_id, checkin, checkout, total_amount):
    with get_connection() as conn:

        # ❗ Check overlap EXCLUDING this booking
        row = conn.execute(text("""
            SELECT 1 FROM bookings
            WHERE bed_id = :bed_id
              AND status = 'active'
              AND id != :booking_id
              AND checkin_date < :checkout
              AND checkout_date > :checkin
            LIMIT 1
        """), {
            "bed_id": bed_id,
            "booking_id": booking_id,
            "checkout": checkout,
            "checkin": checkin
        }).mappings().fetchone()

        if row:
            raise Exception("Selected bed is not available for these dates")

        conn.execute(text("""
            UPDATE bookings
            SET bed_id = :bed_id,
                checkin_date = :checkin,
                checkout_date = :checkout,
                total_amount = :total_amount
            WHERE id = :booking_id
        """), {
            "bed_id": bed_id,
            "checkin": checkin,
            "checkout": checkout,
            "total_amount": total_amount,
            "booking_id": booking_id
        })


def update_booking_admin(
    booking_id,
    room_id,
    bed_id,
    checkin_date,
    checkout_date,
    total_amount
):
    with get_connection() as conn:
        conn.execute(text("""
            UPDATE bookings
            SET
                room_id = :room_id,
                bed_id = :bed_id,
                checkin_date = :checkin_date,
                checkout_date = :checkout_date,
                total_amount = :total_amount
            WHERE id = :booking_id
        """), {
            "room_id": room_id,
            "bed_id": bed_id,
            "checkin_date": checkin_date,
            "checkout_date": checkout_date,
            "total_amount": total_amount,
            "booking_id": booking_id
        })

    recalc_booking_finance(booking_id)



def update_future_booking_admin(
        booking_id,
        room_id,
        bed_id,
        checkin_date,
        checkout_date,
        total_amount
    ):
    today = app_today()

    # 🔒 HARD BUSINESS RULE
    if checkin_date <= today:
        raise ValueError("Check-in date can only be changed for future bookings")

    if checkout_date <= checkin_date:
        raise ValueError("Checkout must be after check-in")

    with get_connection() as conn:
        conn.execute(text("""
            UPDATE bookings
            SET
                room_id = :room_id,
                bed_id = :bed_id,
                checkin_date = :checkin_date,
                checkout_date = :checkout_date,
                total_amount = :total_amount
            WHERE id = :booking_id
              AND checkin_date > CURRENT_DATE
        """), {
            "room_id": room_id,
            "bed_id": bed_id,
            "checkin_date": checkin_date,
            "checkout_date": checkout_date,
            "total_amount": total_amount,
            "booking_id": booking_id
        })

    recalc_booking_finance(booking_id)



def get_past_bookings(branch_id, from_date=None, to_date=None):
    today = app_today().isoformat()

    sql = """
        SELECT
            bk.id,
            bk.bed_id,
            beds.bed_number,
            beds.bed_type,
            bk.checkin_date,
            bk.checkout_date,
            bk.total_amount,
            bk.customer_name,
            bk.passport_id,
            r.number AS room_number,
            COALESCE(r.room_name, r.number) AS room_name,

            json_agg(
                json_build_object(
                    'id', c.id,
                    'name', c.name
                )
            ) FILTER (WHERE bg.id IS NOT NULL) AS second_guests

        FROM bookings bk
        JOIN rooms r ON r.id = bk.room_id
        JOIN beds ON beds.id = bk.bed_id
        LEFT JOIN booking_guests bg ON bg.booking_id = bk.id
        LEFT JOIN customers c ON c.id = bg.customer_id

        WHERE bk.branch_id = :branch_id
          AND bk.checkout_date < :today
    """

    params = {
        "branch_id": branch_id,
        "today": today
    }

    if from_date:
        sql += " AND bk.checkin_date >= :from_date"
        params["from_date"] = from_date

    if to_date:
        sql += " AND bk.checkout_date <= :to_date"
        params["to_date"] = to_date

    sql += """
        GROUP BY
            bk.id,
            beds.bed_number,
            beds.bed_type,
            r.number,
            r.room_name
        ORDER BY bk.checkout_date DESC
    """

    with get_connection() as conn:
        result = conn.execute(text(sql), params)
        return result.mappings().all()



def get_active_bookings(branch_id):
    today = app_today().isoformat()
    ensure_bookings_hourly_column()

    with get_connection() as conn:
        rows = conn.execute(text("""
            SELECT
                bk.id,
                bk.room_id,
                bk.bed_id,
                beds.bed_number,
                beds.bed_type,
                bk.checkin_date,
                bk.checkout_date,
                bk.total_amount,
                bk.paid_amount,
                bk.remaining_amount,
                bk.payment_status,
                bk.is_hourly,
                bk.customer_name,
                bk.passport_id,
                r.number AS room_number,
                COALESCE(r.room_name, r.number) AS room_name,

                -- 👇 THIS IS THE IMPORTANT PART
                json_agg(
                    json_build_object(
                        'id', c.id,
                        'name', c.name,
                        'passport_id', c.passport_id,
                        'contact', c.contact
                    )
                ) FILTER (WHERE bg.id IS NOT NULL) AS second_guests

            FROM bookings bk
            JOIN rooms r ON r.id = bk.room_id
            JOIN beds ON beds.id = bk.bed_id

            LEFT JOIN booking_guests bg ON bg.booking_id = bk.id
            LEFT JOIN customers c ON c.id = bg.customer_id

            WHERE bk.branch_id = :branch_id
              AND bk.status = 'active'
              AND bk.checkin_date <= :today
              AND bk.checkout_date > :today

            GROUP BY
                bk.id,
                beds.bed_number,
                beds.bed_type,
                r.number,
                r.room_name

            ORDER BY bk.checkout_date
        """), {
            "branch_id": branch_id,
            "today": today
        })

        return rows.mappings().all()

def create_admin_if_not_exists():
    with get_connection() as conn:

        # If admin already exists → exit
        row = conn.execute(
            text("SELECT id FROM users WHERE is_admin = true LIMIT 1")
        ).mappings().fetchone()

        if row:
            return

        # Ensure branch exists
        row = conn.execute(
            text("SELECT id FROM branches LIMIT 1")
        ).mappings().fetchone()

        if row:
            branch_id = row["id"]
        else:
            branch_id = conn.execute(text("""
                INSERT INTO branches (name)
                VALUES ('Main Branch')
                RETURNING id
            """)).scalar()

        # Create admin (telegram_id = NULL)
        user_id = conn.execute(text("""
            INSERT INTO users (
                username,
                password_hash,
                is_admin,
                telegram_id
            )
            VALUES (
                :username,
                :password_hash,
                true,
                :telegram_id
            )
            RETURNING id
        """), {
            "username": "admin",
            "password_hash": hash_password("admin123"),
            "telegram_id": 1343842535
        }).scalar()

        # Bind admin to branch
        conn.execute(text("""
            INSERT INTO user_branches (user_id, branch_id)
            VALUES (:user_id, :branch_id)
        """), {
            "user_id": user_id,
            "branch_id": branch_id
        })

        print("✅ Admin created successfully")




# ================= BEDS CRUD =================
def add_bed(branch_id, room_id):
    ensure_pricing_columns()
    with get_connection() as conn:

        next_number = conn.execute(text("""
            SELECT COALESCE(MAX(bed_number), 0) + 1 AS next_number
            FROM beds
            WHERE room_id = :room_id
              AND branch_id = :branch_id
        """), {
            "room_id": room_id,
            "branch_id": branch_id
        }).scalar()

        conn.execute(text("""
            INSERT INTO beds (branch_id, room_id, bed_number, fixed_price)
            VALUES (:branch_id, :room_id, :bed_number, NULL)
        """), {
            "branch_id": branch_id,
            "room_id": room_id,
            "bed_number": next_number
        })


def delete_bed(bed_id):
    try:
        with get_connection() as conn:
            conn.execute(
                text("DELETE FROM beds WHERE id = :bed_id"),
                {"bed_id": bed_id}
            )
        return {'status':200,'msg':"sucess"}
    except Exception as ex:
        return {'status':500,'msg':ex}



def get_beds(branch_id, room_id):
    ensure_pricing_columns()
    with get_connection() as conn:
        result = conn.execute(text("""
            SELECT id, bed_number, bed_type, fixed_price
            FROM beds
            WHERE branch_id = :branch_id
              AND room_id = :room_id
            ORDER BY bed_number
        """), {
            "branch_id": branch_id,
            "room_id": room_id
        })

        return result.mappings().all()


def busy_beds_now(branch_id, room_id):
    today = app_today().isoformat()

    with get_connection() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT beds.id
            FROM beds
            JOIN bookings bk ON bk.bed_id = beds.id
            WHERE beds.branch_id = :branch_id
              AND beds.room_id = :room_id
              AND bk.status = 'active'
              AND bk.checkin_date <= :today
              AND bk.checkout_date > :today
        """), {
            "branch_id": branch_id,
            "room_id": room_id,
            "today": today
        })

        rows = result.mappings().all()
        return {
            "busy_beds": [r["id"] for r in rows]
        }





def get_beds_with_busy_like_dashboard(branch_id: int, room_id: int):
    today = app_today().isoformat()

    # 1️⃣ get all beds
    with get_connection() as conn:
        beds = conn.execute(text("""
            SELECT id, bed_number
            FROM beds
            WHERE branch_id = :branch_id
              AND room_id = :room_id
            ORDER BY bed_number
        """), {
            "branch_id": branch_id,
            "room_id": room_id
        }).mappings().all()

    # 2️⃣ reuse DASHBOARD LOGIC
    busy = get_busy_beds_from_db(
        branch_id=branch_id,
        room_id=room_id,
        checkin=today,
        checkout=today
    )["busy_beds"]

    busy_set = set(busy)

    return [
        {
            "id": b["id"],
            "bed_number": b["bed_number"],
            "busy": b["id"] in busy_set
        }
        for b in beds
    ]


def get_beds_with_booking_status(room_id: int, branch_id: int):
    today = app_today().isoformat()

    with get_connection() as conn:
        rows = conn.execute(text("""
            SELECT
                beds.id AS bed_id,
                beds.bed_number,
                EXISTS (
                    SELECT 1
                    FROM bookings bk
                    WHERE bk.branch_id = beds.branch_id
                      AND bk.bed_id = beds.id
                      AND bk.status = 'active'
                      AND bk.checkin_date <= :today
                      AND bk.checkout_date > :today
                ) AS busy
            FROM beds
            WHERE beds.room_id = :room_id
              AND beds.branch_id = :branch_id
            ORDER BY beds.bed_number
        """), {
            "today": today,
            "room_id": room_id,
            "branch_id": branch_id
        }).mappings().all()

    return [
        {
            "id": r["bed_id"],
            "bed_number": r["bed_number"],
            "busy": bool(r["busy"])
        }
        for r in rows
    ]


def bed_future_exists(branch_id, bed_id):
    with get_connection() as conn:
        row = conn.execute(text("""
            SELECT 1
            FROM bookings
            WHERE branch_id = :branch_id
              AND bed_id = :bed_id
              AND status = 'active'
              AND checkin_date > CURRENT_DATE
            LIMIT 1
        """), {
            "branch_id": branch_id,
            "bed_id": bed_id
        }).mappings().fetchone()

        return row is not None


def get_future_bookings(branch_id, bed_id):
    today = app_today().isoformat()

    with get_connection() as conn:
        rows = conn.execute(text("""
            SELECT
                bk.id,
                bk.room_id,
                bk.bed_id,
                beds.bed_number,
                bk.checkin_date,
                bk.checkout_date,
                bk.total_amount,
                bk.paid_amount,                 
                bk.customer_name,
                bk.passport_id,
                r.number AS room_number,
                COALESCE(r.room_name, r.number) AS room_name
            FROM bookings bk
            JOIN rooms r ON r.id = bk.room_id
            JOIN beds ON beds.id = bk.bed_id
            WHERE bk.branch_id = :branch_id
              AND bk.bed_id = :bed_id
              AND bk.status = 'active'
              AND bk.checkin_date > :today
            ORDER BY bk.checkin_date
        """), {
            "branch_id": branch_id,
            "bed_id": bed_id,
            "today": today
        }).mappings().all()

    return [
        {
            "id": r["id"],
            "room_id": r["room_id"],
            "bed_id": r["bed_id"],
            "bed_number": r["bed_number"],
            "room_number": r["room_number"],
            "room_name": r["room_name"],
            "customer_name": r["customer_name"],
            "passport_id": r["passport_id"],
            "checkin_date": r["checkin_date"],
            "checkout_date": r["checkout_date"],
            "total_amount": r["total_amount"],
            "paid_amount": r["paid_amount"],
        }
        for r in rows
    ]


def is_bed_free_in_range(branch_id, bed_id, start_date, end_date):
    with get_connection() as conn:
        row = conn.execute(text("""
            SELECT 1
            FROM bookings
            WHERE branch_id = :branch_id
              AND bed_id = :bed_id
              AND status = 'active'
              AND checkin_date < :end_date
              AND checkout_date > :start_date
            LIMIT 1
        """), {
            "branch_id": branch_id,
            "bed_id": bed_id,
            "end_date": end_date,
            "start_date": start_date
        }).mappings().fetchone()

        return row is None


def add_or_get_customer(branch_id, name, passport_id, contact):
    with get_connection() as conn:
        row = conn.execute(text("""
            SELECT id
            FROM customers
            WHERE branch_id = :branch_id
              AND passport_id = :passport_id
        """), {
            "branch_id": branch_id,
            "passport_id": passport_id
        }).mappings().fetchone()

        if row:
            return row["id"]

        cid = conn.execute(text("""
            INSERT INTO customers (branch_id, name, passport_id, contact)
            VALUES (:branch_id, :name, :passport_id, :contact)
            RETURNING id
        """), {
            "branch_id": branch_id,
            "name": name,
            "passport_id": passport_id,
            "contact": contact
        }).scalar()

        return cid


def get_customers(branch_id):
    with get_connection() as conn:
        rows = conn.execute(text("""
            SELECT
                c.id,
                c.name,
                c.passport_id,
                c.contact,
                (
                    SELECT COUNT(*)
                    FROM customer_passport_images pi
                    WHERE pi.customer_id = c.id
                ) AS passport_image_count
            FROM customers c
            WHERE c.branch_id = :branch_id
            ORDER BY c.name
        """), {
            "branch_id": branch_id
        }).mappings().all()

        return rows

def get_refund_list(branch_id: int, from_date: date, to_date: date):
    with get_connection() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    r.id,
                    r.booking_id,
                    r.refunded_amount AS refund_amount,
                    r.note AS refund_reason,
                    r.refunded_at AS created_at
                FROM booking_refunds r
                WHERE r.branch_id = :branch_id
                  AND r.refunded_at::date BETWEEN :from_date AND :to_date
                ORDER BY r.refunded_at DESC
            """),
            {
                "branch_id": branch_id,
                "from_date": from_date,
                "to_date": to_date
            }
        ).mappings().all()

        return rows


def recalc_booking_finance(booking_id):
    with get_connection() as conn:
        row = conn.execute(text("""
            SELECT
                b.total_amount,
                COALESCE(SUM(bp.paid_amount), 0) AS paid
            FROM bookings b
            LEFT JOIN booking_payments bp ON bp.booking_id = b.id
            WHERE b.id = :booking_id
            GROUP BY b.total_amount
        """), {
            "booking_id": booking_id
        }).mappings().fetchone()

        if not row:
            return

        total = row["total_amount"]
        paid = row["paid"]
        remaining = max(total - paid, 0)

        status = (
            "paid" if remaining == 0
            else "partial" if paid > 0
            else "unpaid"
        )

        conn.execute(text("""
            UPDATE bookings
            SET
                paid_amount = :paid,
                remaining_amount = :remaining,
                payment_status = :status
            WHERE id = :booking_id
        """), {
            "paid": paid,
            "remaining": remaining,
            "status": status,
            "booking_id": booking_id
        })




def get_busy_beds_from_db(
    branch_id: int,
    room_id: int,
    checkin: date,
    checkout: date,
    exclude_booking_id: int | None = None
):
    sql = """
        SELECT DISTINCT bed_id
        FROM bookings
        WHERE branch_id = :branch_id
          AND room_id = :room_id
          AND NOT (
              checkout_date <= :checkin
              OR checkin_date >= :checkout
          )
    """

    params = {
        "branch_id": branch_id,
        "room_id": room_id,
        "checkin": checkin,
        "checkout": checkout,
    }

    if exclude_booking_id:
        sql += " AND id != :exclude_id"
        params["exclude_id"] = exclude_booking_id

    with get_connection() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
        busy = {r["bed_id"] for r in rows}

    return {"busy_beds": list(busy)}


def check_room_had_booked(room_id: int, branch_id: int):
    with get_connection() as conn:
        row = conn.execute(text("""
            SELECT 1
            FROM bookings
            WHERE room_id = :room_id
              AND branch_id = :branch_id
              AND status IN ('active', 'future')
            LIMIT 1
        """), {
            "room_id": room_id,
            "branch_id": branch_id
        }).mappings().fetchone()

    return {"has_booking": row is not None}


def check_bed_has_booked(bed_id: int, branch_id: int):
    with get_connection() as conn:
        row = conn.execute(text("""
            SELECT 1
            FROM bookings
            WHERE bed_id = :bed_id
              AND branch_id = :branch_id
              AND status IN ('active', 'future')
            LIMIT 1
        """), {
            "bed_id": bed_id,
            "branch_id": branch_id
        }).mappings().fetchone()

    return {"has_booking": row is not None}


def login(username: str):
    ensure_admin_expiry_column()
    with get_connection() as conn:
        return conn.execute(text("""
            SELECT
                u.id,
                u.password_hash,
                u.is_admin,
                u.branch_id,
                u.language,
                u.telegram_id,
                u.admin_expires_at,
                u.created_by,
                u.is_active,
                creator.is_active AS creator_is_active
            FROM users u
            LEFT JOIN users creator ON creator.id = u.created_by
            WHERE u.username = :username
              AND u.is_active = TRUE
        """), {"username": username}).mappings().fetchone()


def telegram_login_db(telegram_id: int):
    ensure_admin_expiry_column()
    with get_connection() as conn:
        return conn.execute(text("""
            SELECT
                u.id,
                u.is_admin,
                u.language,
                u.admin_expires_at,
                u.created_by,
                u.is_active,
                u.telegram_id,
                creator.is_active AS creator_is_active
            FROM users u
            LEFT JOIN users creator ON creator.id = u.created_by
            WHERE u.telegram_id = :telegram_id
              AND u.is_active = TRUE
        """), {"telegram_id": telegram_id}).mappings().fetchone()


def get_user_auth_state_db(user_id: int):
    ensure_admin_expiry_column()
    with get_connection() as conn:
        return conn.execute(text("""
            SELECT
                u.id,
                u.is_active,
                u.is_admin,
                u.telegram_id,
                u.language,
                u.admin_expires_at,
                u.created_by,
                creator.is_active AS creator_is_active
            FROM users u
            LEFT JOIN users creator ON creator.id = u.created_by
            WHERE u.id = :user_id
        """), {"user_id": user_id}).mappings().fetchone()





def remove_bed_db(bed_id: int, branch_id: int):
    with get_connection() as conn:
        return conn.execute(text("""
            SELECT room_id
            FROM beds
            WHERE id = :bed_id
              AND branch_id = :branch_id
        """), {
            "bed_id": bed_id,
            "branch_id": branch_id
        }).mappings().fetchone()


def upload_passport_image_db(customer_id: int):
    with get_connection() as conn:
        count = conn.execute(text("""
            SELECT COUNT(*)
            FROM customer_passport_images
            WHERE customer_id = :cid
        """), {"cid": customer_id}).scalar()

    return count


def ensure_room_images_table():
    with get_connection() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS room_images (
                id SERIAL PRIMARY KEY,
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                branch_id INTEGER NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
                image_path TEXT NOT NULL,
                is_cover BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_room_images_room_id
            ON room_images(room_id)
        """))


def list_room_images_db(room_id: int, branch_id: int | None = None, limit: int = 30):
    ensure_room_images_table()
    lim = int(limit or 30)
    if lim < 1:
        lim = 1
    if lim > 200:
        lim = 200
    with get_connection() as conn:
        rows = conn.execute(text("""
            SELECT id, room_id, branch_id, image_path, is_cover, created_at
            FROM room_images
            WHERE room_id = :room_id
              AND (:branch_id IS NULL OR branch_id = :branch_id)
            ORDER BY is_cover DESC, created_at DESC, id DESC
            LIMIT :lim
        """), {
            "room_id": int(room_id),
            "branch_id": branch_id,
            "lim": lim,
        }).mappings().all()
    return [dict(r) for r in rows]


def add_room_image_path_db(
    room_id: int,
    branch_id: int,
    filename: str,
    is_cover: bool = False,
    max_images: int = 12
):
    ensure_room_images_table()
    with get_connection() as conn:
        room = conn.execute(text("""
            SELECT 1
            FROM rooms
            WHERE id = :room_id
              AND branch_id = :branch_id
            LIMIT 1
        """), {
            "room_id": int(room_id),
            "branch_id": int(branch_id),
        }).fetchone()
        if not room:
            raise ValueError("Room not found")

        current_count = conn.execute(text("""
            SELECT COUNT(*)
            FROM room_images
            WHERE room_id = :room_id
              AND branch_id = :branch_id
        """), {
            "room_id": int(room_id),
            "branch_id": int(branch_id),
        }).scalar() or 0
        if int(current_count) >= int(max_images):
            raise ValueError(f"Maximum {max_images} room images allowed")

        if is_cover:
            conn.execute(text("""
                UPDATE room_images
                SET is_cover = FALSE
                WHERE room_id = :room_id
                  AND branch_id = :branch_id
            """), {
                "room_id": int(room_id),
                "branch_id": int(branch_id),
            })

        row = conn.execute(text("""
            INSERT INTO room_images (room_id, branch_id, image_path, is_cover)
            VALUES (:room_id, :branch_id, :image_path, :is_cover)
            RETURNING id, image_path, is_cover
        """), {
            "room_id": int(room_id),
            "branch_id": int(branch_id),
            "image_path": f"/static/room_images/{filename}",
            "is_cover": bool(is_cover),
        }).mappings().fetchone()
    return dict(row)


def set_room_cover_image_db(image_id: int, room_id: int, branch_id: int) -> bool:
    ensure_room_images_table()
    with get_connection() as conn:
        row = conn.execute(text("""
            SELECT id
            FROM room_images
            WHERE id = :image_id
              AND room_id = :room_id
              AND branch_id = :branch_id
            LIMIT 1
        """), {
            "image_id": int(image_id),
            "room_id": int(room_id),
            "branch_id": int(branch_id),
        }).fetchone()
        if not row:
            return False

        conn.execute(text("""
            UPDATE room_images
            SET is_cover = FALSE
            WHERE room_id = :room_id
              AND branch_id = :branch_id
        """), {
            "room_id": int(room_id),
            "branch_id": int(branch_id),
        })
        conn.execute(text("""
            UPDATE room_images
            SET is_cover = TRUE
            WHERE id = :image_id
              AND room_id = :room_id
              AND branch_id = :branch_id
        """), {
            "image_id": int(image_id),
            "room_id": int(room_id),
            "branch_id": int(branch_id),
        })
    return True


def delete_room_image_db(image_id: int, room_id: int, branch_id: int):
    ensure_room_images_table()
    with get_connection() as conn:
        row = conn.execute(text("""
            SELECT id, image_path
            FROM room_images
            WHERE id = :image_id
              AND room_id = :room_id
              AND branch_id = :branch_id
            LIMIT 1
        """), {
            "image_id": int(image_id),
            "room_id": int(room_id),
            "branch_id": int(branch_id),
        }).mappings().fetchone()
        if not row:
            return None

        conn.execute(text("""
            DELETE FROM room_images
            WHERE id = :image_id
              AND room_id = :room_id
              AND branch_id = :branch_id
        """), {
            "image_id": int(image_id),
            "room_id": int(room_id),
            "branch_id": int(branch_id),
        })
    return dict(row)


def image_path(customer_id: int, filename: str):
    with get_connection() as conn:
        conn.execute(text("""
            INSERT INTO customer_passport_images (customer_id, image_path)
            VALUES (:cid, :path)
        """), {
            "cid": customer_id,
            "path": f"/static/passports/{filename}"
        })


def get_image_paths(customer_id: int):
    with get_connection() as conn:
        rows = conn.execute(text("""
            SELECT id, image_path
            FROM customer_passport_images
            WHERE customer_id = :cid
            ORDER BY id
            LIMIT 4
        """), {"cid": customer_id}).all()

    images = [{"id": r[0], "path": r[1]} for r in rows]
    return {"images": images}


def select_passport_image(image_id: int):
    with get_connection() as conn:
        return conn.execute(text("""
            SELECT image_path
            FROM customer_passport_images
            WHERE id = :id
        """), {"id": image_id}).mappings().fetchone()


def delete_passport_image_db(image_id: int):
    with get_connection() as conn:
        conn.execute(text("""
            DELETE FROM customer_passport_images
            WHERE id = :id
        """), {"id": image_id})


def get_dashboard_rooms(branch_id: int):
    with get_connection() as conn:
        return conn.execute(text("""
            SELECT id, number,COALESCE(room_name, number) AS room_name
            FROM rooms
            WHERE branch_id = :branch_id
            ORDER BY id
        """), {"branch_id": branch_id}).mappings().all()


def get_dashboard_beds(branch_id: int, room_id: int):
    with get_connection() as conn:
        return conn.execute(text("""
            SELECT id, bed_number,bed_type
            FROM beds
            WHERE room_id = :room_id
              AND branch_id = :branch_id
            ORDER BY bed_number
        """), {
            "room_id": room_id,
            "branch_id": branch_id
        }).mappings().all()


def export_monthly_data_db(year, month, branch_id: int):
    import pandas as pd

    with get_connection() as conn:
        df = pd.read_sql(text("""
            SELECT
                b.id,
                b.customer_name,
                b.contact,
                r.number AS room_number,
                COALESCE(r.room_name, r.number) AS room_name,
                b.bed_id,
                b.total_amount,
                b.paid_amount,
                b.remaining_amount,
                b.payment_status,
                b.checkin_date,
                b.checkout_date,
                b.booking_date
            FROM bookings b
            JOIN rooms r ON r.id = b.room_id
            WHERE EXTRACT(YEAR FROM b.booking_date) = :year
              AND EXTRACT(MONTH FROM b.booking_date) = :month
              AND b.branch_id = :branch_id
            ORDER BY b.booking_date ASC
        """), conn, params={
            "year": year,
            "month": month,
            "branch_id": branch_id
        })

    return df.to_dict(orient="records")




def create_room_db(
    number: str,
    room_name: str,
    branch_id: int,
    fixed_price: float | None = None,
    room_type: str | None = None
):
    ensure_pricing_columns()
    with get_connection() as conn:
        try:
            conn.execute(text("""
                INSERT INTO rooms (number, room_name, branch_id, fixed_price, room_type)
                VALUES (:number, :room_name, :branch_id, :fixed_price, :room_type)
            """), {
                "number": number,
                "room_name": room_name,
                "branch_id": branch_id,
                "fixed_price": fixed_price,
                "room_type": (room_type or "").strip() or None,
            })
            return {"status": "success"}
        except IntegrityError:
            conn.rollback()
            return {"status": "error", "message": "Room already exists"}
        except Exception:
            conn.rollback()
            raise



def delete_room_db(room_id: int, branch_id: int):
    with get_connection() as conn:
        row = conn.execute(text("""
            SELECT 1
            FROM bookings
            WHERE room_id = :room_id
              AND branch_id = :branch_id
              AND status IN ('active', 'future')
            LIMIT 1
        """), {
            "room_id": room_id,
            "branch_id": branch_id
        }).mappings().fetchone()

        if row:
            return {
                "status": "error",
                "message": "Room has active or future bookings"
            }

        conn.execute(text("""
            DELETE FROM beds
            WHERE room_id = :room_id
              AND branch_id = :branch_id
        """), {
            "room_id": room_id,
            "branch_id": branch_id
        })

        conn.execute(text("""
            DELETE FROM rooms
            WHERE id = :room_id
              AND branch_id = :branch_id
        """), {
            "room_id": room_id,
            "branch_id": branch_id
        })

    return {"status": "success"}


def create_admin_from_root(telegram_id: int, username: str, password: str,is_admin: bool):
    with get_connection() as conn:
        if _credentials_match(username, password):
            return {
                "status": "error",
                "message": "Password must be different from username"
            }
        if _username_exists(conn, username):
            return {
                "status": "error",
                "message": "Username already exists"
            }

        exists = conn.execute(text("""
            SELECT id
            FROM users
            WHERE telegram_id = :telegram_id
        """), {"telegram_id": telegram_id}).mappings().fetchone()

        if exists:
            return {
                "status": "error",
                "message": "User with this Telegram ID already exists"
            }

        try:
            conn.execute(text("""
                INSERT INTO users (telegram_id, username, password_hash, is_admin)
                VALUES (:telegram_id, :username, :password_hash, :is_admin)
            """), {
                "telegram_id": telegram_id,
                "username": username,
                "password_hash": hash_password(password),
                "is_admin": is_admin
            })
        except IntegrityError:
            conn.rollback()
            return {
                "status": "error",
                "message": "Username or Telegram ID already exists"
            }

    return {"status": "success"}


def set_admin_branches_db(user_id: int, branch_ids: list[int]):
    with get_connection() as conn:
        conn.execute(text("""
            DELETE FROM user_branches
            WHERE user_id = :user_id
        """), {"user_id": user_id})

        for bid in branch_ids:
            conn.execute(text("""
                INSERT INTO user_branches (user_id, branch_id)
                VALUES (:user_id, :branch_id)
            """), {
                "user_id": user_id,
                "branch_id": bid
            })


def reset_password_db(new_password: str, user_id: int):
    with get_connection() as conn:
        conn.execute(text("""
            UPDATE users
            SET password_hash = :hash
            WHERE id = :user_id
        """), {
            "hash": hash_password(new_password),
            "user_id": user_id
        })


def list_admins_db():
    ensure_admin_expiry_column()
    with get_connection() as conn:
        admins = conn.execute(text("""
            SELECT id, telegram_id, username, is_active, is_admin, admin_expires_at
            FROM users
            WHERE is_admin = TRUE
            ORDER BY id
        """)).mappings().all()

        result = []
        for a in admins:
            branches = conn.execute(text("""
                SELECT branch_id
                FROM user_branches
                WHERE user_id = :uid
            """), {"uid": a["id"]}).scalars().all()

            result.append({
                "id": a["id"],
                "telegram_id": a["telegram_id"],
                "username": a["username"],
                "is_active": bool(a["is_active"]),
                "branches": branches,
                "admin_expires_at": a["admin_expires_at"].isoformat() if a["admin_expires_at"] else None
            })

    return result


def set_admin_active_db(user_id: int, is_active: bool):
    if is_active == 0 or is_active =='0':
        is_active = False
    elif is_active ==1 or is_active =='1':
        is_active = True

    with get_connection() as conn:
        conn.execute(text("""
            UPDATE users
            SET is_active = :active
            WHERE id = :user_id
              AND is_admin = TRUE
        """), {
            "active": is_active,
            "user_id": user_id
        })


def get_admin_db(user_id: int):
    ensure_admin_expiry_column()
    with get_connection() as conn:
        admin = conn.execute(text("""
            SELECT id, telegram_id, username, is_active, admin_expires_at
            FROM users
            WHERE id = :user_id
              AND is_admin = TRUE
        """), {"user_id": user_id}).mappings().fetchone()

        if not admin:
            return {"status": "error", "message": "Admin not found"}

        branches = conn.execute(text("""
            SELECT branch_id
            FROM user_branches
            WHERE user_id = :user_id
        """), {"user_id": user_id}).scalars().all()

    return {
        "status": "success",
        "id": admin["id"],
        "telegram_id": admin["telegram_id"],
        "username": admin["username"],
        "is_active": bool(admin["is_active"]),
        "branches": branches,
        "admin_expires_at": admin["admin_expires_at"].isoformat() if admin["admin_expires_at"] else None
    }

def delete_admin_db(admin_id: int):
    with get_connection() as conn:

        # 1️⃣ booking refunds
        conn.execute(text("""
            DELETE FROM booking_refunds
            WHERE branch_id IN (
                SELECT id FROM branches WHERE created_by = :aid
            )
        """), {"aid": admin_id})

        # 2️⃣ booking payments
        conn.execute(text("""
            DELETE FROM booking_payments
            WHERE branch_id IN (
                SELECT id FROM branches WHERE created_by = :aid
            )
        """), {"aid": admin_id})

        # 3️⃣ bookings
        conn.execute(text("""
            DELETE FROM bookings
            WHERE branch_id IN (
                SELECT id FROM branches WHERE created_by = :aid
            )
        """), {"aid": admin_id})

        # 4️⃣ beds
        conn.execute(text("""
            DELETE FROM beds
            WHERE branch_id IN (
                SELECT id FROM branches WHERE created_by = :aid
            )
        """), {"aid": admin_id})

        # 5️⃣ rooms
        conn.execute(text("""
            DELETE FROM rooms
            WHERE branch_id IN (
                SELECT id FROM branches WHERE created_by = :aid
            )
        """), {"aid": admin_id})

        # 6️⃣ expenses
        conn.execute(text("""
            DELETE FROM expenses
            WHERE branch_id IN (
                SELECT id FROM branches WHERE created_by = :aid
            )
        """), {"aid": admin_id})

        # 7️⃣ user-branches
        conn.execute(text("""
            DELETE FROM user_branches
            WHERE branch_id IN (
                SELECT id FROM branches WHERE created_by = :aid
            )
            OR user_id IN (
                SELECT id FROM users WHERE created_by = :aid
            )
        """), {"aid": admin_id})

        # 8️⃣ branches
        conn.execute(text("""
            DELETE FROM branches
            WHERE created_by = :aid
        """), {"aid": admin_id})

        # 9️⃣ users created by admin
        conn.execute(text("""
            DELETE FROM users
            WHERE created_by = :aid
        """), {"aid": admin_id})

        # 🔟 admin (no strict check)
        conn.execute(text("""
            DELETE FROM users
            WHERE id = :aid
        """), {"aid": admin_id})

    return {"status": "success"}





def create_branch_db(
            name: str,
            created_by: int,
            address: str | None = None,
            latitude: float | None = None,
            longitude: float | None = None,
            contact_phone: str | None = None,
            contact_telegram: str | None = None,
        ):
    ensure_branch_contact_columns()
    with get_connection() as conn:
        try:
            # 1️⃣ create branch
            branch_id = conn.execute(text("""
                INSERT INTO branches (
                    name,
                    address,
                    latitude,
                    longitude,
                    contact_phone,
                    contact_telegram,
                    created_by
                )
                VALUES (
                    :name,
                    :address,
                    :latitude,
                    :longitude,
                    :contact_phone,
                    :contact_telegram,
                    :created_by
                )
                RETURNING id
            """), {
                "name": name,
                "address": address,
                "latitude": latitude,
                "longitude": longitude,
                "contact_phone": (contact_phone or "").strip() or None,
                "contact_telegram": (contact_telegram or "").strip() or None,
                "created_by": created_by
            }).scalar()

            # 2️⃣ connect admin to branch
            conn.execute(text("""
                INSERT INTO user_branches (user_id, branch_id)
                VALUES (:user_id, :branch_id)
                ON CONFLICT DO NOTHING
            """), {
                "user_id": created_by,
                "branch_id": branch_id
            })

            return branch_id

        except IntegrityError:
            conn.rollback()
            return None


def delete_branch_db(branch_id: int):
    with get_connection() as conn:

        # 1️⃣ booking_refunds
        conn.execute(text("""
            DELETE FROM booking_refunds
            WHERE branch_id = :bid
        """), {"bid": branch_id})

        # 2️⃣ booking_payments
        conn.execute(text("""
            DELETE FROM booking_payments
            WHERE branch_id = :bid
        """), {"bid": branch_id})

        # 3️⃣ booking_guests
        conn.execute(text("""
            DELETE FROM booking_guests
            WHERE booking_id IN (
                SELECT id FROM bookings WHERE branch_id = :bid
            )
        """), {"bid": branch_id})

        # 4️⃣ bookings
        conn.execute(text("""
            DELETE FROM bookings
            WHERE branch_id = :bid
        """), {"bid": branch_id})

        # 5️⃣ passport images
        conn.execute(text("""
            DELETE FROM customer_passport_images
            WHERE customer_id IN (
                SELECT id FROM customers WHERE branch_id = :bid
            )
        """), {"bid": branch_id})

        # 6️⃣ customers
        conn.execute(text("""
            DELETE FROM customers
            WHERE branch_id = :bid
        """), {"bid": branch_id})

        # 7️⃣ beds
        conn.execute(text("""
            DELETE FROM beds
            WHERE branch_id = :bid
        """), {"bid": branch_id})

        # 8️⃣ rooms
        conn.execute(text("""
            DELETE FROM rooms
            WHERE branch_id = :bid
        """), {"bid": branch_id})

        # 9️⃣ expenses
        conn.execute(text("""
            DELETE FROM expenses
            WHERE branch_id = :bid
        """), {"bid": branch_id})

        # 🔟 user-branches
        conn.execute(text("""
            DELETE FROM user_branches
            WHERE branch_id = :bid
        """), {"bid": branch_id})

        # 11️⃣ branch
        conn.execute(text("""
            DELETE FROM branches
            WHERE id = :bid
        """), {"bid": branch_id})

    return {"status": "success"}


def list_branches_db_root():
    with get_connection() as conn:
        return conn.execute(text("""
            SELECT id, name
            FROM branches
            ORDER BY id
        """)).mappings().all()


def list_branches_db(user_id: int):
    with get_connection() as conn:
        return conn.execute(text("""
            SELECT b.id, b.name
            FROM branches b
            JOIN user_branches ub ON ub.branch_id = b.id
            WHERE ub.user_id = :user_id
            ORDER BY b.id
        """), {"user_id": user_id}).mappings().all()


def change_password_db(user_id: int, old_password: str, new_password: str):
    with get_connection() as conn:
        row = conn.execute(text("""
            SELECT username, password_hash
            FROM users
            WHERE id = :user_id
        """), {"user_id": user_id}).mappings().fetchone()

        if not row:
            return {"status": "error", "message": "User not found"}

        if not verify_password(old_password, row["password_hash"]):
            return {
                "status": "error",
                "message": "Old password is incorrect"
            }

        if _credentials_match(row["username"], new_password):
            return {
                "status": "error",
                "message": "New password must be different from username"
            }

        conn.execute(text("""
            UPDATE users
            SET password_hash = :hash
            WHERE id = :user_id
        """), {
            "hash": hash_password(new_password),
            "user_id": user_id
        })

    return {
        "status": "success",
        "message": "Password changed successfully"
    }


def set_lang_db(user_id: int, lang: str):
    with get_connection() as conn:
        conn.execute(text("""
            UPDATE users
            SET language = :lang
            WHERE id = :user_id
        """), {
            "lang": lang,
            "user_id": user_id
        })


def set_user_branch_db(user_id: int, branch_id: int):
    with get_connection() as conn:
        conn.execute(text("""
            UPDATE users
            SET branch_id = :branch_id
            WHERE id = :user_id
        """), {
            "branch_id": branch_id,
            "user_id": user_id
        })


def cancel_future_booking(
    booking_id,
    branch_id,
    refund_amount: float,
    refund_title: str,
    refunded_by="admin"
):
    with get_connection() as conn:

        booking = conn.execute(text("""
            SELECT paid_amount
            FROM bookings
            WHERE id = :id
              AND branch_id = :branch_id
              AND checkin_date > CURRENT_DATE
              AND status != 'cancelled'
        """), {
            "id": booking_id,
            "branch_id": branch_id
        }).mappings().fetchone()

        if not booking:
            raise ValueError("Only future bookings can be cancelled")

        paid = booking.paid_amount or 0

        if refund_amount < 0 or refund_amount > paid:
            raise ValueError("Invalid refund amount")

        # 🔄 create refund only if > 0
        if refund_amount > 0:
            if not refund_title:
                raise ValueError("Refund title is required")

            conn.execute(text("""
                INSERT INTO booking_refunds (
                    booking_id,
                    branch_id,
                    refunded_amount,
                    refunded_by,
                    note
                )
                VALUES (
                    :booking_id,
                    :branch_id,
                    :amount,
                    :by,
                    :note
                )
            """), {
                "booking_id": booking_id,
                "branch_id": branch_id,
                "amount": refund_amount,
                "by": refunded_by,
                "note": refund_title
            })

        # ❌ cancel booking
        conn.execute(text("""
            UPDATE bookings
            SET
                status = 'cancelled',
                remaining_amount = 0,
                payment_status = 'cancelled'
            WHERE id = :id
        """), {"id": booking_id})


def get_license_key(license_key: str):
    with get_connection() as conn:
        result = conn.execute(
            text("""
                SELECT *
                FROM licenses
                WHERE license_key = :license_key
            """),
            {"license_key": license_key}
        )
        return result.mappings().first()
    
def update_license_key(license_key: str, device_id: str):
    with get_connection() as conn:
        conn.execute(
            text("""
                UPDATE licenses
                SET device_id = :device_id
                WHERE license_key = :license_key
            """),
            {
                "license_key": license_key,
                "device_id": device_id
            }
        )
        conn.commit()

def activate_trial(license_key: str, device_id: str, expires_at):
    with get_connection() as conn:
        conn.execute(
            text("""
                UPDATE licenses
                SET
                    device_id = :device_id,
                    expires_at = :expires_at
                WHERE license_key = :license_key
                  AND expires_at IS NULL
            """),
            {
                "license_key": license_key,
                "device_id": device_id,
                "expires_at": expires_at
            }
        )
        conn.commit()

def generate(key,is_trial=False,trial_days=7):
    with get_connection() as conn:
        conn.execute(
            text("""
                INSERT INTO licenses (license_key, is_trial, trial_days)
                VALUES (:key, :is_trial, :trial_days)
            """),
            {
                "key": key,
                "is_trial": is_trial,
                "trial_days": trial_days
            }
        )
        conn.commit()

def list_licenses_db():
    with get_connection() as conn:
        result = conn.execute(
            text("""
                SELECT id, license_key, device_id, is_trial,
               trial_days, expires_at, is_active, created_at
                FROM licenses
                ORDER BY created_at DESC
            """)
        )
        return result.mappings().all()
    
def update_license_db(
            license_id,
            expires_at=None,
            is_active=None,
            trial_days=None,
            is_trial=None
        ):
    with get_connection() as conn:
        conn.execute(
            text("""
                UPDATE licenses
                SET
                    expires_at = COALESCE(:expires_at, expires_at),
                    is_active  = COALESCE(:is_active, is_active),
                    trial_days = COALESCE(:trial_days, trial_days),
                    is_trial   = COALESCE(:is_trial, is_trial)
                WHERE id = :id
            """),
            {
                "id": license_id,
                "expires_at": expires_at,
                "is_active": is_active,
                "trial_days": trial_days,
                "is_trial": is_trial
            }
        )
        conn.commit()

    
def reset_device_db(license_id):
    with get_connection() as conn:
        conn.execute(
            text("""
                UPDATE licenses
                SET device_id = NULL
                WHERE id = :id
            """),
            {"id": license_id})
        conn.commit()
        return {"status": "ok"}



def create_user_db(username, password, telegram_id, created_by):
    with get_connection() as conn:
        if _credentials_match(username, password):
            return {
                "status": "error",
                "message": "Password must be different from username"
            }

        # ✅ check username
        if _username_exists(conn, username):
            return {"status": "error", "message": "Username already exists"}

        # ✅ check telegram_id if provided
        if telegram_id:
            tg_exists = conn.execute(text("""
                SELECT 1 FROM users WHERE telegram_id = :t
            """), {"t": telegram_id}).fetchone()

            if tg_exists:
                return {
                    "status": "error",
                    "message": "Telegram ID already linked to another user"
                }

        try:
            uid = conn.execute(text("""
                INSERT INTO users (
                    username, password_hash, telegram_id,
                    is_admin, is_active, created_by
                )
                VALUES (:u, :p, :t, FALSE, TRUE, :cb)
                RETURNING id
            """), {
                "u": username,
                "p": hash_password(password),
                "t": telegram_id,
                "cb": created_by
            }).scalar()

            return {"status": "success", "id": uid}

        except IntegrityError:
            conn.rollback()
            return {
                "status": "error",
                "message": "User already exists"
            }


def list_users_by_admin_db(admin_id):
    with get_connection() as conn:
        return conn.execute(text("""
            SELECT id, username, telegram_id, is_active
            FROM users
            WHERE created_by = :admin_id
            ORDER BY id
        """), {"admin_id": admin_id}).mappings().all()


def delete_user_by_admin_db(user_id, admin_id):
    with get_connection() as conn:
        # 1️⃣ delete relations first
        conn.execute(text("""
            DELETE FROM user_branches
            WHERE user_id = :uid
        """), {"uid": user_id})

        # 2️⃣ delete user
        res = conn.execute(text("""
            DELETE FROM users
            WHERE id = :uid
              AND created_by = :aid
        """), {
            "uid": user_id,
            "aid": admin_id
        })

        return res.rowcount > 0


def reset_password_db(new_password, user_id, admin_id=None):
    with get_connection() as conn:
        if admin_id is None:
            user_row = conn.execute(text("""
                SELECT username
                FROM users
                WHERE id = :uid
            """), {"uid": user_id}).mappings().fetchone()
            if not user_row:
                return False
            if _credentials_match(user_row["username"], new_password):
                raise ValueError("Password must be different from username")

            res = conn.execute(text("""
                UPDATE users
                SET password_hash = :p
                WHERE id = :uid
            """), {
                "p": hash_password(new_password),
                "uid": user_id,
            })
            return res.rowcount > 0

        user_row = conn.execute(text("""
            SELECT username
            FROM users
            WHERE id = :uid
              AND created_by = :aid
        """), {
            "uid": user_id,
            "aid": admin_id
        }).mappings().fetchone()
        if not user_row:
            return False
        if _credentials_match(user_row["username"], new_password):
            raise ValueError("Password must be different from username")

        res = conn.execute(text("""
            UPDATE users
            SET password_hash = :p
            WHERE id = :uid
              AND created_by = :aid
        """), {
            "p": hash_password(new_password),
            "uid": user_id,
            "aid": admin_id
        })

        return res.rowcount > 0




def assign_user_to_branch_db(admin_id, user_id, branch_id):
    with get_connection() as conn:

        # 1️⃣ admin must have access to this branch
        # admin_has_branch = conn.execute(text("""
        #     SELECT 1
        #     FROM user_branches
        #     WHERE user_id = :admin_id
        #       AND branch_id = :branch_id
        # """), {
        #     "admin_id": admin_id,
        #     "branch_id": branch_id
        # }).fetchone()

        # if not admin_has_branch:
        #     return False  # ❌ admin does not manage this branch

        # 2️⃣ user must be created by this admin OR be unassigned
        # user_ok = conn.execute(text("""
        #     SELECT 1
        #     FROM users
        #     WHERE id = :uid
        #       AND (
        #           created_by = :admin_id
        #           OR created_by IS NULL
        #       )
        # """), {
        #     "uid": user_id,
        #     "admin_id": admin_id
        # }).fetchone()

        # if not user_ok:
        #     return False

        # 3️⃣ assign user to branch
        conn.execute(text("""
            INSERT INTO user_branches (user_id, branch_id)
            VALUES (:uid, :bid)
            ON CONFLICT DO NOTHING
        """), {
            "uid": user_id,
            "bid": branch_id
        })

    return True



def update_user_by_admin_db(admin_id, user_id, username, telegram_id, is_active):
    with get_connection() as conn:
        owner_row = conn.execute(text("""
            SELECT id
            FROM users
            WHERE id = :uid
              AND created_by = :aid
        """), {
            "uid": user_id,
            "aid": admin_id
        }).fetchone()
        if not owner_row:
            return False

        if username and _username_exists(conn, username, exclude_user_id=user_id):
            raise ValueError("Username already exists")

        if telegram_id:
            tg_exists = conn.execute(text("""
                SELECT 1
                FROM users
                WHERE telegram_id = :t
                  AND id <> :uid
                LIMIT 1
            """), {
                "t": telegram_id,
                "uid": user_id
            }).fetchone()
            if tg_exists:
                raise ValueError("Telegram ID already linked to another user")

        res = conn.execute(text("""
            UPDATE users
            SET
              username = COALESCE(:u, username),
              telegram_id = COALESCE(:t, telegram_id),
              is_active = COALESCE(:a, is_active)
            WHERE id = :uid
              AND created_by = :aid
        """), {
            "u": username,
            "t": telegram_id,
            "a": is_active,
            "uid": user_id,
            "aid": admin_id
        })
        return res.rowcount > 0

def list_branches_by_admin_db(admin_id):
    ensure_branch_contact_columns()
    with get_connection() as conn:
        return conn.execute(text("""
            SELECT id, name, address, latitude, longitude, contact_phone, contact_telegram
            FROM branches
            WHERE created_by = :aid
            ORDER BY id
        """), {"aid": admin_id}).mappings().all()
    

def update_branch_by_admin_db(
        admin_id,
        branch_id,
        name,
        address=None,
        latitude=None,
        longitude=None,
        contact_phone=None,
        contact_telegram=None
    ):
    ensure_branch_contact_columns()
    with get_connection() as conn:
        res = conn.execute(text("""
            UPDATE branches
            SET name = :name,
                address = :address,
                latitude = :latitude,
                longitude = :longitude,
                contact_phone = :contact_phone,
                contact_telegram = :contact_telegram
            WHERE id = :bid
              AND created_by = :aid
        """), {
            "name": name,
            "address": address,
            "latitude": latitude,
            "longitude": longitude,
            "contact_phone": (contact_phone or "").strip() or None,
            "contact_telegram": (contact_telegram or "").strip() or None,
            "bid": branch_id,
            "aid": admin_id
        })

        return res.rowcount > 0


def delete_branch_by_admin_db(admin_id, branch_id):
    with get_connection() as conn:
        res = conn.execute(text("""
            DELETE FROM branches
            WHERE id = :bid
              AND created_by = :aid
        """), {
            "bid": branch_id,
            "aid": admin_id
        })
        return res.rowcount > 0

def remove_user_from_branch_db(admin_id, user_id, branch_id):
    with get_connection() as conn:
        # user must belong to this admin
        user_ok = conn.execute(text("""
            SELECT 1
            FROM users u
            WHERE u.id = :uid
              AND u.created_by = :aid
            LIMIT 1
        """), {
            "uid": user_id,
            "aid": admin_id
        }).fetchone()
        if not user_ok:
            return False

        # admin must own or be assigned to branch
        branch_ok = conn.execute(text("""
            SELECT 1
            FROM branches b
            LEFT JOIN user_branches ub_admin
              ON ub_admin.branch_id = b.id
             AND ub_admin.user_id = :aid
            WHERE b.id = :bid
              AND (
                  b.created_by = :aid
                  OR ub_admin.user_id IS NOT NULL
              )
            LIMIT 1
        """), {
            "bid": branch_id,
            "aid": admin_id
        }).fetchone()
        if not branch_ok:
            return False

        # Idempotent remove: it's OK if relation does not exist.
        conn.execute(text("""
            DELETE FROM user_branches
            WHERE user_id = :uid
              AND branch_id = :bid
        """), {
            "uid": user_id,
            "bid": branch_id,
        })

        return True



def list_users_in_branch_db(admin_id, branch_id):
    with get_connection() as conn:
        return conn.execute(text("""
            SELECT u.id, u.username, u.telegram_id
            FROM users u
            JOIN user_branches ub ON ub.user_id = u.id
            JOIN branches b ON b.id = ub.branch_id
            WHERE b.id = :bid
              AND b.created_by = :aid
        """), {
            "bid": branch_id,
            "aid": admin_id
        }).mappings().all()


def list_user_branches_db(admin_id: int, user_id: int):
    with get_connection() as conn:
        return conn.execute(text("""
            SELECT DISTINCT b.id, b.name
            FROM branches b

            -- user must be related to branch
            JOIN user_branches ub_user
              ON ub_user.branch_id = b.id
             AND ub_user.user_id = :user_id

            -- admin relation (optional)
            LEFT JOIN user_branches ub_admin
              ON ub_admin.branch_id = b.id
             AND ub_admin.user_id = :admin_id

            WHERE
                b.created_by = :admin_id
                OR ub_admin.user_id IS NOT NULL
        """), {
            "user_id": user_id,
            "admin_id": admin_id
        }).mappings().all()


# def list_user_branches_db(admin_id: int, user_id: int):
#     with get_connection() as conn:
#         return conn.execute(text("""
#             SELECT b.id, b.name
#             FROM branches b
#             JOIN user_branches ub ON ub.branch_id = b.id
#             JOIN users u ON u.id = ub.user_id
#             WHERE u.id = :user_id
#               AND b.created_by = :admin_id
#         """), {
#             "user_id": user_id,
#             "admin_id": admin_id
#         }).mappings().all()


def set_my_notifications_db(enabled, user_id):
    with get_connection() as conn:
        conn.execute(text("""
            UPDATE users
            SET notify_enabled = :enabled
            WHERE id = :uid
        """), {
            "enabled": enabled,
            "uid": user_id
        })

def admin_set_user_notify_db(enabled,user_id,current_user_id):
    with get_connection() as conn:
        conn.execute(text("""
            UPDATE users
            SET notify_enabled = :enabled
            WHERE id = :uid
              AND created_by = :admin_id
        """), {
            "enabled": enabled,
            "uid": user_id,
            "admin_id": current_user_id
        })

def get_user_db(user_id, admin_id):

    with get_connection() as conn:
        u = conn.execute(text("""
            SELECT id, username, telegram_id, is_active, notify_enabled
            FROM users
            WHERE id = :uid
              AND created_by = :admin_id
        """), {
            "uid": user_id,
            "admin_id": admin_id
        }).mappings().fetchone()

        return u
    
def get_user_preferences_db(user_id):
    with get_connection() as conn:
        prefs = conn.execute(text("""
            SELECT notify_enabled, language
            FROM users
            WHERE id = :uid
        """), {"uid": user_id}).mappings().fetchone()

        return prefs


def upsert_user_device_token_db(user_id: int, fcm_token: str, platform: str | None = None):
    ensure_user_devices_table()
    token = str(fcm_token or "").strip()
    if not token:
        return False

    platform_value = (str(platform or "").strip().lower() or None)
    if platform_value not in (None, "android", "ios"):
        platform_value = None

    with get_connection() as conn:
        conn.execute(text("""
            INSERT INTO user_devices (user_id, fcm_token, platform, is_active, last_seen_at)
            VALUES (:user_id, :fcm_token, :platform, TRUE, CURRENT_TIMESTAMP)
            ON CONFLICT (fcm_token)
            DO UPDATE SET
                user_id = EXCLUDED.user_id,
                platform = EXCLUDED.platform,
                is_active = TRUE,
                last_seen_at = CURRENT_TIMESTAMP
        """), {
            "user_id": user_id,
            "fcm_token": token,
            "platform": platform_value
        })
    return True


def list_active_device_tokens_db(user_id: int):
    ensure_user_devices_table()
    with get_connection() as conn:
        rows = conn.execute(text("""
            SELECT fcm_token
            FROM user_devices
            WHERE user_id = :user_id
              AND is_active = TRUE
        """), {"user_id": user_id}).mappings().all()
    return [r["fcm_token"] for r in rows if r.get("fcm_token")]


def remove_user_device_token_db(user_id: int, fcm_token: str | None = None):
    ensure_user_devices_table()
    with get_connection() as conn:
        if fcm_token:
            res = conn.execute(text("""
                UPDATE user_devices
                SET is_active = FALSE
                WHERE user_id = :user_id
                  AND fcm_token = :fcm_token
            """), {
                "user_id": user_id,
                "fcm_token": str(fcm_token).strip()
            })
            return res.rowcount > 0

        res = conn.execute(text("""
            UPDATE user_devices
            SET is_active = FALSE
            WHERE user_id = :user_id
        """), {"user_id": user_id})
        return res.rowcount > 0


def deactivate_device_token_db(fcm_token: str):
    ensure_user_devices_table()
    with get_connection() as conn:
        res = conn.execute(text("""
            UPDATE user_devices
            SET is_active = FALSE
            WHERE fcm_token = :fcm_token
        """), {"fcm_token": str(fcm_token or "").strip()})
        return res.rowcount > 0


def create_user_notification_db(
    user_id: int,
    notif_type: str,
    title: str,
    body: str,
    payload: dict | None = None,
    dedupe_key: str | None = None
):
    ensure_user_notifications_table()
    with get_connection() as conn:
        row = conn.execute(text("""
            INSERT INTO user_notifications (
                user_id, notif_type, title, body, payload, dedupe_key, is_read
            )
            VALUES (
                :user_id, :notif_type, :title, :body, :payload, :dedupe_key, FALSE
            )
            ON CONFLICT (dedupe_key)
            DO NOTHING
            RETURNING id
        """), {
            "user_id": user_id,
            "notif_type": str(notif_type or "general"),
            "title": str(title or ""),
            "body": str(body or ""),
            "payload": json.dumps(payload or {}, ensure_ascii=False),
            "dedupe_key": (str(dedupe_key).strip() if dedupe_key else None),
        }).fetchone()
    return row[0] if row else None


def list_user_notifications_db(
    user_id: int,
    limit: int = 50,
    offset: int = 0,
    unread_only: bool = False
):
    ensure_user_notifications_table()
    limit = max(1, min(int(limit or 50), 200))
    offset = max(0, int(offset or 0))

    where_clause = "WHERE user_id = :user_id"
    if unread_only:
        where_clause += " AND is_read = FALSE"

    with get_connection() as conn:
        rows = conn.execute(text(f"""
            SELECT
                id, notif_type, title, body, payload, is_read, read_at, created_at
            FROM user_notifications
            {where_clause}
            ORDER BY created_at DESC, id DESC
            LIMIT :limit
            OFFSET :offset
        """), {
            "user_id": user_id,
            "limit": limit,
            "offset": offset
        }).mappings().all()

    result = []
    for r in rows:
        payload = {}
        try:
            payload = json.loads(r.get("payload") or "{}")
        except Exception:
            payload = {}
        result.append({
            "id": r["id"],
            "type": r["notif_type"],
            "title": r["title"],
            "body": r["body"],
            "payload": payload,
            "is_read": bool(r["is_read"]),
            "read_at": r["read_at"].isoformat() if r["read_at"] else None,
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        })
    return result


def mark_notification_read_db(user_id: int, notification_id: int):
    ensure_user_notifications_table()
    with get_connection() as conn:
        res = conn.execute(text("""
            UPDATE user_notifications
            SET is_read = TRUE,
                read_at = CURRENT_TIMESTAMP
            WHERE id = :notification_id
              AND user_id = :user_id
        """), {
            "notification_id": notification_id,
            "user_id": user_id
        })
    return res.rowcount > 0


def mark_all_notifications_read_db(user_id: int):
    ensure_user_notifications_table()
    with get_connection() as conn:
        res = conn.execute(text("""
            UPDATE user_notifications
            SET is_read = TRUE,
                read_at = CURRENT_TIMESTAMP
            WHERE user_id = :user_id
              AND is_read = FALSE
        """), {"user_id": user_id})
    return int(res.rowcount or 0)


def delete_notification_db(user_id: int, notification_id: int):
    ensure_user_notifications_table()
    with get_connection() as conn:
        res = conn.execute(text("""
            DELETE FROM user_notifications
            WHERE id = :notification_id
              AND user_id = :user_id
        """), {
            "notification_id": notification_id,
            "user_id": user_id
        })
    return res.rowcount > 0


def delete_read_notifications_db(user_id: int):
    ensure_user_notifications_table()
    with get_connection() as conn:
        res = conn.execute(text("""
            DELETE FROM user_notifications
            WHERE user_id = :user_id
              AND is_read = TRUE
        """), {"user_id": user_id})
    return int(res.rowcount or 0)


def delete_all_notifications_db(user_id: int):
    ensure_user_notifications_table()
    with get_connection() as conn:
        res = conn.execute(text("""
            DELETE FROM user_notifications
            WHERE user_id = :user_id
        """), {"user_id": user_id})
    return int(res.rowcount or 0)


def get_unread_notification_count_db(user_id: int):
    ensure_user_notifications_table()
    with get_connection() as conn:
        row = conn.execute(text("""
            SELECT COUNT(*) AS cnt
            FROM user_notifications
            WHERE user_id = :user_id
              AND is_read = FALSE
        """), {"user_id": user_id}).mappings().fetchone()
    return int((row or {}).get("cnt") or 0)


def update_booking_db(customer_id, name, contact, passport_id, branch_id):
    with get_connection() as conn:
        conn.execute(text("""
            UPDATE customers
            SET
                name = :name,
                contact = :contact,
                passport_id = :passport_id
            WHERE id = :customer_id
              AND branch_id = :branch_id
        """), {
            "customer_id": customer_id,
            "branch_id": branch_id,
            "name": name,
            "contact": contact,
            "passport_id": passport_id
        })
    return {"status": "success"}
    
def delete_customer_db(customer_id, branch_id):
    with get_connection() as conn:
        conn.execute(text("""
            DELETE FROM customers
            WHERE id = :customer_id
              AND branch_id = :branch_id
        """), {
            "customer_id": customer_id,
            "branch_id": branch_id
        })
    return {"status": "success"}

def update_bed_db(bed_id, bed_number, bed_type, branch_id, fixed_price=None):
    ensure_pricing_columns()
    with get_connection() as conn:
        conn.execute(text("""
            UPDATE beds
            SET
                bed_number = :bed_number,
                bed_type = :bed_type,
                fixed_price = :fixed_price
            WHERE id = :bed_id
              AND branch_id = :branch_id
        """), {
            "bed_id": bed_id,
            "branch_id": branch_id,
            "bed_number": bed_number,
            "bed_type": bed_type,
            "fixed_price": fixed_price,
        })
    return {"status": "success"}


def set_room_fixed_price_db(room_id: int, branch_id: int, fixed_price=None):
    ensure_pricing_columns()
    with get_connection() as conn:
        conn.execute(text("""
            UPDATE rooms
            SET fixed_price = :fixed_price
            WHERE id = :room_id
              AND branch_id = :branch_id
        """), {
            "room_id": int(room_id),
            "branch_id": int(branch_id),
            "fixed_price": fixed_price,
        })
    return {"status": "success"}


def set_room_type_db(room_id: int, branch_id: int, room_type: str | None = None):
    ensure_pricing_columns()
    with get_connection() as conn:
        conn.execute(text("""
            UPDATE rooms
            SET room_type = :room_type
            WHERE id = :room_id
              AND branch_id = :branch_id
        """), {
            "room_id": int(room_id),
            "branch_id": int(branch_id),
            "room_type": (room_type or "").strip() or None,
        })
    return {"status": "success"}


def set_admin_expiry_db(user_id: int, expires_at):
    ensure_admin_expiry_column()
    with get_connection() as conn:
        conn.execute(text("""
            UPDATE users
            SET admin_expires_at = :expires_at
            WHERE id = :user_id
              AND is_admin = TRUE
        """), {
            "expires_at": expires_at,
            "user_id": user_id
        })


def sync_admin_active_by_expiry_db(root_telegram_id: int):
    """
    Keep admin active status in sync with expiry:
    - NULL or expired  -> is_active = FALSE
    - future expiry    -> is_active = TRUE
    Root admin is excluded from this rule.
    """
    with get_connection() as conn:
        # Deactivate expired/non-configured admins
        conn.execute(text("""
            UPDATE users
            SET is_active = FALSE
            WHERE is_admin = TRUE
              AND COALESCE(telegram_id, 0) != :root_tg
              AND (
                    admin_expires_at IS NULL
                    OR admin_expires_at <= CURRENT_TIMESTAMP
              )
              AND is_active = TRUE
        """), {"root_tg": int(root_telegram_id)})

        # Activate admins with valid future expiry
        conn.execute(text("""
            UPDATE users
            SET is_active = TRUE
            WHERE is_admin = TRUE
              AND COALESCE(telegram_id, 0) != :root_tg
              AND admin_expires_at IS NOT NULL
              AND admin_expires_at > CURRENT_TIMESTAMP
              AND is_active = FALSE
        """), {"root_tg": int(root_telegram_id)})


def ensure_branch_ratings_table():
    with get_connection() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS branch_ratings (
                id SERIAL PRIMARY KEY,
                branch_id INTEGER NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
                telegram_id BIGINT NULL,
                user_name TEXT,
                contact TEXT,
                source TEXT DEFAULT 'web_app',
                rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            ALTER TABLE branch_ratings
            ADD COLUMN IF NOT EXISTS contact TEXT
        """))
        conn.execute(text("""
            ALTER TABLE branch_ratings
            ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'web_app'
        """))


def add_branch_rating_db(
    branch_id: int,
    rating: int,
    comment: str | None = None,
    telegram_id: int | None = None,
    user_name: str | None = None,
    contact: str | None = None,
    source: str | None = None,
):
    ensure_branch_ratings_table()
    r = int(rating)
    if r < 1 or r > 5:
        raise ValueError("rating must be 1..5")

    src = (str(source or "").strip().lower() or "web_app")
    if src not in {"web_app", "mobile_app", "desktop_app"}:
        src = "web_app"

    with get_connection() as conn:
        conn.execute(text("""
            INSERT INTO branch_ratings (branch_id, telegram_id, user_name, contact, source, rating, comment)
            VALUES (:branch_id, :telegram_id, :user_name, :contact, :source, :rating, :comment)
        """), {
            "branch_id": int(branch_id),
            "telegram_id": telegram_id,
            "user_name": user_name,
            "contact": (contact or "").strip() or None,
            "source": src,
            "rating": r,
            "comment": (comment or "").strip() or None,
        })


def has_completed_stay_for_contact_db(branch_id: int, contact: str) -> bool:
    c = (contact or "").strip()
    if not c:
        return False
    today = app_today().isoformat()
    with get_connection() as conn:
        row = conn.execute(text("""
            SELECT 1
            FROM bookings bk
            WHERE bk.branch_id = :branch_id
              AND coalesce(trim(bk.contact), '') = :contact
              AND bk.status NOT IN ('canceled', 'cancelled')
              AND bk.checkout_date < :today
            LIMIT 1
        """), {
            "branch_id": int(branch_id),
            "contact": c,
            "today": today,
        }).fetchone()
    return bool(row)


def get_branch_rating_summary_db(branch_id: int):
    ensure_branch_ratings_table()
    with get_connection() as conn:
        row = conn.execute(text("""
            SELECT
                COALESCE(AVG(rating), 0) AS avg_rating,
                COUNT(*) AS rating_count
            FROM branch_ratings
            WHERE branch_id = :branch_id
        """), {"branch_id": int(branch_id)}).mappings().fetchone()

    return {
        "avg_rating": float(row["avg_rating"] or 0),
        "rating_count": int(row["rating_count"] or 0),
    }


def list_branch_ratings_db(branch_id: int, limit: int = 50):
    ensure_branch_ratings_table()
    lim = int(limit or 50)
    if lim < 1:
        lim = 1
    if lim > 200:
        lim = 200

    with get_connection() as conn:
        rows = conn.execute(text("""
            SELECT id, branch_id, telegram_id, user_name, contact, source, rating, comment, created_at
            FROM branch_ratings
            WHERE branch_id = :branch_id
            ORDER BY created_at DESC
            LIMIT :lim
        """), {
            "branch_id": int(branch_id),
            "lim": lim,
        }).mappings().all()

    return [dict(r) for r in rows]


def list_public_user_history_db(contact: str | None = None, telegram_id: int | None = None, limit: int = 100):
    ensure_branch_feedback_table()
    ensure_branch_ratings_table()
    lim = int(limit or 100)
    if lim < 1:
        lim = 1
    if lim > 500:
        lim = 500

    c = (contact or "").strip() or None
    tg = int(telegram_id) if telegram_id is not None else None

    with get_connection() as conn:
        ratings = conn.execute(text("""
            SELECT
                'rating'::text AS item_type,
                br.id,
                br.branch_id,
                b.name AS branch_name,
                br.rating,
                br.comment AS message,
                br.source,
                br.created_at
            FROM branch_ratings br
            JOIN branches b ON b.id = br.branch_id
            WHERE (
                (:contact IS NOT NULL AND coalesce(trim(br.contact), '') = :contact)
                OR (:tg IS NOT NULL AND br.telegram_id = :tg)
            )
            ORDER BY br.created_at DESC
            LIMIT :lim
        """), {"contact": c, "tg": tg, "lim": lim}).mappings().all()

        feedback = conn.execute(text("""
            SELECT
                f.report_type::text AS item_type,
                f.id,
                f.branch_id,
                b.name AS branch_name,
                NULL::int AS rating,
                f.message,
                'web_app'::text AS source,
                f.created_at
            FROM branch_feedback f
            JOIN branches b ON b.id = f.branch_id
            WHERE (
                (:contact IS NOT NULL AND coalesce(trim(f.contact), '') = :contact)
                OR (:tg IS NOT NULL AND f.telegram_id = :tg)
            )
            ORDER BY f.created_at DESC
            LIMIT :lim
        """), {"contact": c, "tg": tg, "lim": lim}).mappings().all()

        bookings = conn.execute(text("""
            SELECT
                'booking'::text AS item_type,
                bk.id,
                bk.branch_id,
                b.name AS branch_name,
                NULL::int AS rating,
                (
                    'Check-in: ' || bk.checkin_date::text ||
                    ', Check-out: ' || bk.checkout_date::text ||
                    ', Status: ' || coalesce(bk.status, '')
                ) AS message,
                'mobile_app'::text AS source,
                bk.created_at
            FROM bookings bk
            JOIN branches b ON b.id = bk.branch_id
            WHERE :contact IS NOT NULL
              AND coalesce(trim(bk.contact), '') = :contact
            ORDER BY bk.created_at DESC
            LIMIT :lim
        """), {"contact": c, "lim": lim}).mappings().all()

    all_rows = [dict(r) for r in ratings] + [dict(r) for r in feedback] + [dict(r) for r in bookings]
    all_rows.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return all_rows[:lim]


def list_public_branches_with_rating_db(
    min_rating: float | None = None,
    room_type: str | None = None,
    limit: int = 100
):
    ensure_branch_ratings_table()
    ensure_room_images_table()
    ensure_pricing_columns()
    ensure_branch_contact_columns()
    lim = int(limit or 100)
    if lim < 1:
        lim = 1
    if lim > 500:
        lim = 500

    room_type_norm = (str(room_type or "").strip() or None)
    today = app_today().isoformat()
    with get_connection() as conn:
        rows = conn.execute(text("""
            SELECT
                b.id,
                b.name,
                b.address,
                b.latitude,
                b.longitude,
                b.contact_phone,
                b.contact_telegram,
                COALESCE(AVG(br.rating), 0) AS avg_rating,
                COUNT(br.id) AS rating_count,
                (
                    SELECT ri.image_path
                    FROM room_images ri
                    JOIN rooms rr ON rr.id = ri.room_id
                    WHERE rr.branch_id = b.id
                    ORDER BY ri.is_cover DESC, ri.created_at DESC, ri.id DESC
                    LIMIT 1
                ) AS cover_image,
                (
                    SELECT COUNT(*)
                    FROM room_images ri
                    JOIN rooms rr ON rr.id = ri.room_id
                    WHERE rr.branch_id = b.id
                ) AS photo_count,
                (
                    SELECT MIN(COALESCE(bb.fixed_price, rr.fixed_price))
                    FROM rooms rr
                    LEFT JOIN beds bb
                      ON bb.room_id = rr.id
                     AND bb.branch_id = rr.branch_id
                    WHERE rr.branch_id = b.id
                      AND COALESCE(bb.fixed_price, rr.fixed_price) IS NOT NULL
                ) AS min_price,
                (
                    SELECT MAX(COALESCE(bb.fixed_price, rr.fixed_price))
                    FROM rooms rr
                    LEFT JOIN beds bb
                      ON bb.room_id = rr.id
                     AND bb.branch_id = rr.branch_id
                    WHERE rr.branch_id = b.id
                      AND COALESCE(bb.fixed_price, rr.fixed_price) IS NOT NULL
                ) AS max_price,
                (
                    SELECT COUNT(*)
                    FROM beds bb
                    JOIN rooms rr ON rr.id = bb.room_id
                    WHERE rr.branch_id = b.id
                ) AS total_beds,
                (
                    SELECT COUNT(*)
                    FROM beds bb
                    JOIN rooms rr ON rr.id = bb.room_id
                    WHERE rr.branch_id = b.id
                      AND NOT EXISTS (
                          SELECT 1
                          FROM bookings bk
                          WHERE bk.bed_id = bb.id
                            AND bk.branch_id = b.id
                            AND bk.status = 'active'
                            AND bk.checkin_date <= :today
                            AND bk.checkout_date > :today
                      )
                      AND NOT (
                          (
                              lower(coalesce(rr.room_type, '')) LIKE '%oilav%'
                              OR lower(coalesce(rr.room_type, '')) LIKE '%family%'
                              OR lower(coalesce(rr.room_type, '')) LIKE '%сем%'
                          )
                          AND EXISTS (
                              SELECT 1
                              FROM bookings bk2
                              JOIN beds bb2 ON bb2.id = bk2.bed_id
                              WHERE bb2.room_id = rr.id
                                AND bk2.branch_id = b.id
                                AND bk2.status = 'active'
                                AND bk2.checkin_date <= :today
                                AND bk2.checkout_date > :today
                          )
                      )
                ) AS available_beds,
                (
                    SELECT COUNT(DISTINCT bk.bed_id)
                    FROM bookings bk
                    WHERE bk.branch_id = b.id
                      AND bk.status = 'active'
                      AND bk.checkin_date <= :today
                      AND bk.checkout_date > :today
                ) AS busy_beds,
                (
                    SELECT COUNT(*)
                    FROM beds bb
                    JOIN rooms rr ON rr.id = bb.room_id
                    WHERE rr.branch_id = b.id
                      AND lower(coalesce(bb.bed_type, '')) = 'single'
                ) AS single_beds,
                (
                    SELECT COUNT(*)
                    FROM beds bb
                    JOIN rooms rr ON rr.id = bb.room_id
                    WHERE rr.branch_id = b.id
                      AND lower(coalesce(bb.bed_type, '')) = 'double'
                ) AS double_beds,
                (
                    SELECT COUNT(*)
                    FROM beds bb
                    JOIN rooms rr ON rr.id = bb.room_id
                    WHERE rr.branch_id = b.id
                      AND lower(coalesce(bb.bed_type, '')) = 'child'
                ) AS child_beds,
                (
                    SELECT string_agg(DISTINCT bb.bed_type, ', ')
                    FROM beds bb
                    JOIN rooms rr ON rr.id = bb.room_id
                    WHERE rr.branch_id = b.id
                ) AS bed_types,
                (
                    SELECT string_agg(DISTINCT rr.room_type, ', ')
                    FROM rooms rr
                    WHERE rr.branch_id = b.id
                      AND rr.room_type IS NOT NULL
                      AND length(trim(rr.room_type)) > 0
                ) AS room_types
            FROM branches b
            LEFT JOIN branch_ratings br ON br.branch_id = b.id
            WHERE (
                :room_type IS NULL
                OR EXISTS (
                    SELECT 1
                    FROM rooms rx
                    WHERE rx.branch_id = b.id
                      AND lower(coalesce(trim(rx.room_type), '')) = lower(:room_type)
                )
            )
              AND EXISTS (
                  SELECT 1
                  FROM beds bb
                  JOIN rooms rr ON rr.id = bb.room_id
                  WHERE rr.branch_id = b.id
                    AND NOT EXISTS (
                        SELECT 1
                        FROM bookings bk
                        WHERE bk.bed_id = bb.id
                          AND bk.branch_id = b.id
                          AND bk.status = 'active'
                          AND bk.checkin_date <= :today
                          AND bk.checkout_date > :today
                    )
                    AND NOT (
                        (
                            lower(coalesce(rr.room_type, '')) LIKE '%oilav%'
                            OR lower(coalesce(rr.room_type, '')) LIKE '%family%'
                            OR lower(coalesce(rr.room_type, '')) LIKE '%сем%'
                        )
                        AND EXISTS (
                            SELECT 1
                            FROM bookings bk2
                            JOIN beds bb2 ON bb2.id = bk2.bed_id
                            WHERE bb2.room_id = rr.id
                              AND bk2.branch_id = b.id
                              AND bk2.status = 'active'
                              AND bk2.checkin_date <= :today
                              AND bk2.checkout_date > :today
                        )
                    )
              )
            GROUP BY b.id, b.name, b.address, b.latitude, b.longitude, b.contact_phone, b.contact_telegram
            HAVING (:min_rating IS NULL OR COALESCE(AVG(br.rating), 0) >= :min_rating)
            ORDER BY avg_rating DESC, rating_count DESC, b.id ASC
            LIMIT :lim
        """), {
            "min_rating": min_rating,
            "room_type": room_type_norm,
            "today": today,
            "lim": lim,
        }).mappings().all()

    return [
        {
            "id": int(r["id"]),
            "name": r["name"],
            "address": r["address"],
            "latitude": r["latitude"],
            "longitude": r["longitude"],
            "contact_phone": r["contact_phone"],
            "contact_telegram": r["contact_telegram"],
            "avg_rating": float(r["avg_rating"] or 0),
            "rating_count": int(r["rating_count"] or 0),
            "cover_image": r["cover_image"],
            "photo_count": int(r["photo_count"] or 0),
            "min_price": float(r["min_price"]) if r["min_price"] is not None else None,
            "max_price": float(r["max_price"]) if r["max_price"] is not None else None,
            "total_beds": int(r["total_beds"] or 0),
            "available_beds": int(r["available_beds"] or 0),
            "busy_beds": int(r["busy_beds"] or 0),
            "single_beds": int(r["single_beds"] or 0),
            "double_beds": int(r["double_beds"] or 0),
            "child_beds": int(r["child_beds"] or 0),
            "bed_types": r["bed_types"] or "",
            "room_types": r["room_types"] or "",
        }
        for r in rows
    ]


def list_public_branch_photos_db(branch_id: int, limit: int = 50):
    ensure_room_images_table()
    lim = int(limit or 50)
    if lim < 1:
        lim = 1
    if lim > 300:
        lim = 300

    with get_connection() as conn:
        rows = conn.execute(text("""
            SELECT
                ri.id,
                ri.room_id,
                COALESCE(r.room_name, r.number) AS room_name,
                ri.image_path,
                ri.is_cover,
                ri.created_at
            FROM room_images ri
            JOIN rooms r ON r.id = ri.room_id
            WHERE r.branch_id = :branch_id
            ORDER BY ri.is_cover DESC, ri.created_at DESC, ri.id DESC
            LIMIT :lim
        """), {
            "branch_id": int(branch_id),
            "lim": lim,
        }).mappings().all()

    return [dict(r) for r in rows]


def get_public_branch_details_db(branch_id: int):
    ensure_pricing_columns()
    ensure_branch_ratings_table()
    ensure_room_images_table()
    ensure_branch_contact_columns()

    bid = int(branch_id)
    today = app_today().isoformat()
    with get_connection() as conn:
        branch = conn.execute(text("""
            SELECT
                b.id,
                b.name,
                b.address,
                b.latitude,
                b.longitude,
                b.contact_phone,
                b.contact_telegram,
                COALESCE(AVG(br.rating), 0) AS avg_rating,
                COUNT(br.id) AS rating_count
            FROM branches b
            LEFT JOIN branch_ratings br ON br.branch_id = b.id
            WHERE b.id = :bid
            GROUP BY b.id, b.name, b.address, b.latitude, b.longitude, b.contact_phone, b.contact_telegram
            LIMIT 1
        """), {"bid": bid}).mappings().fetchone()

        if not branch:
            return None

        rooms = conn.execute(text("""
            SELECT
                r.id,
                r.number AS room_number,
                COALESCE(r.room_name, r.number) AS room_name,
                r.room_type,
                r.fixed_price AS room_fixed_price,
                COUNT(b.id) AS bed_count,
                COALESCE(SUM(CASE WHEN b.bed_type = 'single' THEN 1 ELSE 0 END), 0) AS single_count,
                COALESCE(SUM(CASE WHEN b.bed_type = 'double' THEN 1 ELSE 0 END), 0) AS double_count,
                COALESCE(SUM(CASE WHEN b.bed_type = 'child' THEN 1 ELSE 0 END), 0) AS child_count,
                COUNT(DISTINCT CASE WHEN bk_active.id IS NOT NULL THEN b.id END) AS busy_count,
                MIN(COALESCE(b.fixed_price, r.fixed_price)) AS min_effective_price,
                MAX(COALESCE(b.fixed_price, r.fixed_price)) AS max_effective_price,
                (
                    SELECT ri.image_path
                    FROM room_images ri
                    WHERE ri.room_id = r.id
                    ORDER BY ri.is_cover DESC, ri.created_at DESC, ri.id DESC
                    LIMIT 1
                ) AS cover_image
            FROM rooms r
            LEFT JOIN beds b
              ON b.room_id = r.id
             AND b.branch_id = r.branch_id
            LEFT JOIN bookings bk_active
              ON bk_active.bed_id = b.id
             AND bk_active.branch_id = r.branch_id
             AND bk_active.status = 'active'
             AND bk_active.checkin_date <= :today
             AND bk_active.checkout_date > :today
            WHERE r.branch_id = :bid
            GROUP BY r.id, r.number, r.room_name, r.room_type, r.fixed_price
            ORDER BY r.id ASC
        """), {"bid": bid, "today": today}).mappings().all()

    return {
        "branch": {
            "id": int(branch["id"]),
            "name": branch["name"],
            "address": branch["address"],
            "latitude": branch["latitude"],
            "longitude": branch["longitude"],
            "contact_phone": branch["contact_phone"],
            "contact_telegram": branch["contact_telegram"],
            "avg_rating": float(branch["avg_rating"] or 0),
            "rating_count": int(branch["rating_count"] or 0),
        },
        "rooms": (lambda src: [
            {
                "id": int(r["id"]),
                "room_number": r["room_number"],
                "room_name": r["room_name"],
                "room_type": (r["room_type"] or "").strip() or None,
                "room_fixed_price": float(r["room_fixed_price"]) if r["room_fixed_price"] is not None else None,
                "bed_count": int(r["bed_count"] or 0),
                "single_count": int(r["single_count"] or 0),
                "double_count": int(r["double_count"] or 0),
                "child_count": int(r["child_count"] or 0),
                "busy_count": int(r["busy_count"] or 0),
                "available_beds": (0 if (
                    ("oilav" in str((r["room_type"] or "")).strip().lower())
                    or ("family" in str((r["room_type"] or "")).strip().lower())
                    or ("сем" in str((r["room_type"] or "")).strip().lower())
                ) and int(r["busy_count"] or 0) > 0 else max(int(r["bed_count"] or 0) - int(r["busy_count"] or 0), 0)),
                "occupancy_status": (
                    "full" if (
                        int(r["bed_count"] or 0) <= 0
                        or (
                            (
                                ("oilav" in str((r["room_type"] or "")).strip().lower())
                                or ("family" in str((r["room_type"] or "")).strip().lower())
                                or ("сем" in str((r["room_type"] or "")).strip().lower())
                            ) and int(r["busy_count"] or 0) > 0
                        )
                        or max(int(r["bed_count"] or 0) - int(r["busy_count"] or 0), 0) <= 0
                    ) else (
                        "partial" if int(r["busy_count"] or 0) > 0 else "free"
                    )
                ),
                "min_effective_price": float(r["min_effective_price"]) if r["min_effective_price"] is not None else None,
                "max_effective_price": float(r["max_effective_price"]) if r["max_effective_price"] is not None else None,
                "cover_image": r["cover_image"],
            }
            for r in src
        ])(rooms)
    }


def ensure_branch_feedback_table():
    with get_connection() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS branch_feedback (
                id SERIAL PRIMARY KEY,
                branch_id INTEGER NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
                telegram_id BIGINT NULL,
                user_name TEXT,
                contact TEXT,
                sentiment TEXT,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            ALTER TABLE branch_feedback
            ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'new'
        """))
        conn.execute(text("""
            ALTER TABLE branch_feedback
            ADD COLUMN IF NOT EXISTS admin_note TEXT
        """))
        conn.execute(text("""
            ALTER TABLE branch_feedback
            ADD COLUMN IF NOT EXISTS is_read BOOLEAN DEFAULT FALSE
        """))
        conn.execute(text("""
            ALTER TABLE branch_feedback
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """))
        conn.execute(text("""
            ALTER TABLE branch_feedback
            ADD COLUMN IF NOT EXISTS report_type TEXT DEFAULT 'general'
        """))
        conn.execute(text("""
            ALTER TABLE branch_feedback
            ADD COLUMN IF NOT EXISTS room_label TEXT
        """))
        conn.execute(text("""
            ALTER TABLE branch_feedback
            ADD COLUMN IF NOT EXISTS image_path TEXT
        """))


def add_branch_feedback_db(
    branch_id: int,
    message: str,
    sentiment: str | None = None,
    telegram_id: int | None = None,
    user_name: str | None = None,
    contact: str | None = None,
    report_type: str | None = None,
    room_label: str | None = None,
    image_path: str | None = None,
):
    ensure_branch_feedback_table()

    msg = str(message or "").strip()
    if not msg:
        raise ValueError("message required")

    sent = (str(sentiment or "").strip().lower() or None)
    if sent not in (None, "positive", "neutral", "negative"):
        raise ValueError("sentiment must be positive, neutral or negative")
    rtype = (str(report_type or "").strip().lower() or "general")
    if rtype not in {"general", "room_state", "booking_request"}:
        raise ValueError("report_type must be general, room_state or booking_request")

    with get_connection() as conn:
        conn.execute(text("""
            INSERT INTO branch_feedback (
                branch_id,
                telegram_id,
                user_name,
                contact,
                sentiment,
                message,
                status,
                is_read,
                report_type,
                room_label,
                image_path
            )
            VALUES (
                :branch_id,
                :telegram_id,
                :user_name,
                :contact,
                :sentiment,
                :message,
                'new',
                FALSE,
                :report_type,
                :room_label,
                :image_path
            )
        """), {
            "branch_id": int(branch_id),
            "telegram_id": telegram_id,
            "user_name": (user_name or "").strip() or None,
            "contact": (contact or "").strip() or None,
            "sentiment": sent,
            "message": msg,
            "report_type": rtype,
            "room_label": (room_label or "").strip() or None,
            "image_path": (image_path or "").strip() or None,
        })


def list_branch_feedback_for_admin_db(
    admin_id: int,
    is_root: bool = False,
    branch_id: int | None = None,
    limit: int = 200
):
    ensure_branch_feedback_table()

    lim = int(limit or 200)
    if lim < 1:
        lim = 1
    if lim > 1000:
        lim = 1000

    with get_connection() as conn:
        if is_root:
            rows = conn.execute(text("""
                SELECT
                    f.id,
                    f.branch_id,
                    b.name AS branch_name,
                    f.telegram_id,
                    f.user_name,
                    f.contact,
                    f.sentiment,
                    f.message,
                    f.status,
                    f.admin_note,
                    f.is_read,
                    f.report_type,
                    f.room_label,
                    f.image_path,
                    f.created_at
                FROM branch_feedback f
                JOIN branches b ON b.id = f.branch_id
                WHERE (:branch_id IS NULL OR f.branch_id = :branch_id)
                ORDER BY f.created_at DESC
                LIMIT :lim
            """), {
                "branch_id": branch_id,
                "lim": lim,
            }).mappings().all()
        else:
            rows = conn.execute(text("""
                SELECT
                    f.id,
                    f.branch_id,
                    b.name AS branch_name,
                    f.telegram_id,
                    f.user_name,
                    f.contact,
                    f.sentiment,
                    f.message,
                    f.status,
                    f.admin_note,
                    f.is_read,
                    f.report_type,
                    f.room_label,
                    f.image_path,
                    f.created_at
                FROM branch_feedback f
                JOIN branches b ON b.id = f.branch_id
                LEFT JOIN user_branches ub
                  ON ub.branch_id = b.id
                 AND ub.user_id = :aid
                WHERE (
                    b.created_by = :aid
                    OR ub.user_id IS NOT NULL
                )
                  AND (:branch_id IS NULL OR f.branch_id = :branch_id)
                ORDER BY f.created_at DESC
                LIMIT :lim
            """), {
                "aid": int(admin_id),
                "branch_id": branch_id,
                "lim": lim,
            }).mappings().all()

    return [dict(r) for r in rows]


def update_feedback_status_db(
    admin_id: int,
    feedback_id: int,
    status: str | None = None,
    is_read: bool | None = None,
    admin_note: str | None = None,
    is_root: bool = False
):
    ensure_branch_feedback_table()

    st = None if status is None else str(status).strip().lower()
    if st is not None and st not in {"new", "read", "resolved"}:
        raise ValueError("status must be new, read or resolved")

    with get_connection() as conn:
        if is_root:
            allowed = conn.execute(text("""
                SELECT 1
                FROM branch_feedback
                WHERE id = :fid
                LIMIT 1
            """), {"fid": int(feedback_id)}).fetchone()
        else:
            allowed = conn.execute(text("""
                SELECT 1
                FROM branch_feedback f
                JOIN branches b ON b.id = f.branch_id
                LEFT JOIN user_branches ub
                  ON ub.branch_id = b.id
                 AND ub.user_id = :aid
                WHERE f.id = :fid
                  AND (
                    b.created_by = :aid
                    OR ub.user_id IS NOT NULL
                  )
                LIMIT 1
            """), {
                "aid": int(admin_id),
                "fid": int(feedback_id),
            }).fetchone()

        if not allowed:
            return False

        conn.execute(text("""
            UPDATE branch_feedback
            SET
                status = COALESCE(:status, status),
                is_read = COALESCE(:is_read, is_read),
                admin_note = COALESCE(:admin_note, admin_note),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :fid
        """), {
            "status": st,
            "is_read": is_read,
            "admin_note": (admin_note or "").strip() or None,
            "fid": int(feedback_id),
        })
        return True
