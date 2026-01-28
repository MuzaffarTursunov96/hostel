from datetime import date
from security import hash_password, verify_password
from database import engine
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

def get_connection():
    return engine.begin()


def init_db():
    with get_connection() as conn:

        # ---------- BRANCHES ----------
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS branches (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )
        """))

        # ---------- ROOMS ----------
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS rooms (
            id SERIAL PRIMARY KEY,
            number TEXT NOT NULL,
            description TEXT,
            branch_id INTEGER NOT NULL,
            UNIQUE(number, branch_id),
            FOREIGN KEY(branch_id) REFERENCES branches(id) ON DELETE CASCADE
        )
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

        # ---------- BEDS ----------
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS beds (
            id SERIAL PRIMARY KEY,
            room_id INTEGER NOT NULL,
            status TEXT DEFAULT 'free',
            branch_id INTEGER NOT NULL,
            bed_number INTEGER,
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
            status TEXT DEFAULT 'active',
            booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

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
            password_hash TEXT NOT NULL,
            telegram_id BIGINT UNIQUE,
            is_admin BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE,
            branch_id INTEGER,
            language TEXT DEFAULT 'ru',
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

        # ---------- DEFAULT BRANCH ----------
        conn.execute(text("""
        INSERT INTO branches (name)
        SELECT 'Main Branch'
        WHERE NOT EXISTS (SELECT 1 FROM branches)
        """))
    print("✅ Database initialized successfully.")

def get_rooms_with_beds(branch_id):
    with get_connection() as conn:
        result = conn.execute(text("""
            SELECT 
                rooms.id,
                rooms.number AS room_number,
                COUNT(beds.id) AS bed_count
            FROM rooms
            LEFT JOIN beds 
                ON beds.room_id = rooms.id
               AND beds.branch_id = rooms.branch_id
            WHERE rooms.branch_id = :branch_id
            GROUP BY rooms.id, rooms.number
            ORDER BY rooms.number ASC
        """), {"branch_id": branch_id})

        rows = result.mappings().all()

    return [
        {
            "id": r["id"],
            "room_number": r["room_number"],
            "bed_count": r["bed_count"]
        }
        for r in rows
    ]


def get_available_beds(branch_id, room_id, checkin_date, checkout_date):
    with get_connection() as conn:
        result = conn.execute(text("""
            SELECT 
                b.id,
                b.bed_number,
                b.room_id
            FROM beds b
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
    checkout_date
):
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
            "checkout_date": checkout_date
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
    today = date.today()

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
                b.customer_name,
                b.passport_id,
                b.contact,
                r.number AS room_number,
                beds.bed_number,
                b.total_amount,
                b.paid_amount,
                b.remaining_amount,
                b.checkin_date,
                b.checkout_date
            FROM bookings b
            JOIN rooms r
                ON r.id = b.room_id
               AND r.branch_id = b.branch_id
            JOIN beds
                ON beds.id = b.bed_id
            WHERE b.branch_id = :branch_id
              AND b.remaining_amount > 0
              AND b.checkin_date >= :from_date
              AND b.checkin_date <= :to_date
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
    with get_connection() as conn:
        result = conn.execute(text("""
            SELECT b.id, b.name
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
                beds.bed_number
            FROM booking_payments bp
            JOIN bookings b ON b.id = bp.booking_id
            JOIN rooms r ON r.id = b.room_id
            JOIN beds ON beds.id = b.bed_id
            WHERE bp.branch_id = :branch_id
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
                r.number AS room_number,
                beds.bed_number
            FROM booking_payments bp
            JOIN bookings b ON b.id = bp.booking_id
            JOIN rooms r ON r.id = b.room_id
            JOIN beds ON beds.id = b.bed_id
            WHERE bp.branch_id = :branch_id
              AND EXTRACT(YEAR FROM bp.paid_at) = :year
              AND EXTRACT(MONTH FROM bp.paid_at) = :month
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
                b.checkin_date,
                b.checkout_date

            FROM booking_payments bp
            JOIN bookings b ON b.id = bp.booking_id
            JOIN rooms r ON r.id = b.room_id

            WHERE bp.branch_id = :branch_id
              AND bp.paid_at::date BETWEEN :start_date AND :end_date
            ORDER BY bp.paid_at DESC
        """), {
            "branch_id": branch_id,
            "start_date": start_date,
            "end_date": end_date
        })

        return result.mappings().all()


def cancel_booking(booking_id: int, branch_id: int):
    with get_connection() as conn:
        conn.execute(text("""
            UPDATE bookings
            SET status = 'canceled'
            WHERE id = :booking_id
              AND branch_id = :branch_id
              AND status = 'active'
        """), {
            "booking_id": booking_id,
            "branch_id": branch_id
        })


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
    checkout_date,
    total_amount
):
    with get_connection() as conn:
        conn.execute(text("""
            UPDATE bookings
            SET
                room_id = :room_id,
                bed_id = :bed_id,
                checkout_date = :checkout_date,
                total_amount = :total_amount
            WHERE id = :booking_id
        """), {
            "room_id": room_id,
            "bed_id": bed_id,
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
    today = date.today()

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
    today = date.today().isoformat()

    sql = """
        SELECT
            bk.id,
            bk.bed_id,
            beds.bed_number,
            bk.checkin_date,
            bk.checkout_date,
            bk.total_amount,
            bk.customer_name,
            bk.passport_id,
            r.number AS room_number
        FROM bookings bk
        JOIN rooms r ON r.id = bk.room_id
        JOIN beds ON beds.id = bk.bed_id
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

    sql += " ORDER BY bk.checkout_date DESC"

    with get_connection() as conn:
        result = conn.execute(text(sql), params)
        return result.mappings().all()


def get_active_bookings(branch_id):
    today = date.today().isoformat()

    with get_connection() as conn:
        result = conn.execute(text("""
            SELECT
                bk.id,
                bk.room_id,
                bk.bed_id,
                beds.bed_number,
                bk.checkin_date,
                bk.checkout_date,
                bk.total_amount,
                bk.customer_name,
                bk.passport_id,
                r.number AS room_number
            FROM bookings bk
            JOIN rooms r ON r.id = bk.room_id
            JOIN beds ON beds.id = bk.bed_id
            WHERE bk.branch_id = :branch_id
              AND bk.status = 'active'
              AND bk.checkin_date <= :today
              AND bk.checkout_date > :today
            ORDER BY bk.checkout_date
        """), {
            "branch_id": branch_id,
            "today": today
        })

        return result.mappings().all()


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
            INSERT INTO beds (branch_id, room_id, bed_number)
            VALUES (:branch_id, :room_id, :bed_number)
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
    with get_connection() as conn:
        result = conn.execute(text("""
            SELECT id, bed_number
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
    today = date.today().isoformat()

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
    today = date.today().isoformat()

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
    today = date.today().isoformat()

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
    today = date.today().isoformat()

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
                r.number AS room_number
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
    with get_connection() as conn:
        return conn.execute(text("""
            SELECT id, password_hash, is_admin, branch_id, language, telegram_id
            FROM users
            WHERE username = :username
              AND is_active = TRUE
        """), {"username": username}).mappings().fetchone()


def telegram_login_db(telegram_id: int):
    with get_connection() as conn:
        return conn.execute(text("""
            SELECT id, is_admin, branch_id, language
            FROM users
            WHERE telegram_id = :telegram_id
              AND is_active = TRUE
        """), {"telegram_id": telegram_id}).mappings().fetchone()


def user_auto_create(telegram_id: int, username: str):
    with get_connection() as conn:
        user_id = conn.execute(text("""
            INSERT INTO users (telegram_id, username, is_admin, is_active)
            VALUES (:telegram_id, :username, FALSE, TRUE)
            RETURNING id
        """), {
            "telegram_id": telegram_id,
            "username": username
        }).scalar()

    return user_id


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
            SELECT id, number
            FROM rooms
            WHERE branch_id = :branch_id
            ORDER BY number
        """), {"branch_id": branch_id}).mappings().all()


def get_dashboard_beds(branch_id: int, room_id: int):
    with get_connection() as conn:
        return conn.execute(text("""
            SELECT id, bed_number
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




def create_room_db(number: str, branch_id: int):
    try:
        with get_connection() as conn:
            conn.execute(text("""
                INSERT INTO rooms (number, branch_id)
                VALUES (:number, :branch_id)
            """), {
                "number": number,
                "branch_id": branch_id
            })

        return {"status": "success"}

    except Exception:
        return {"status": "error"}


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


def create_admin_from_root(telegram_id: int, username: str, password: str):
    with get_connection() as conn:
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

        conn.execute(text("""
            INSERT INTO users (telegram_id, username, password_hash, is_admin)
            VALUES (:telegram_id, :username, :password_hash, TRUE)
        """), {
            "telegram_id": telegram_id,
            "username": username,
            "password_hash": hash_password(password)
        })

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
    with get_connection() as conn:
        admins = conn.execute(text("""
            SELECT id, telegram_id, username, is_active
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
                "branches": branches
            })

    return result


def set_admin_active_db(user_id: int, is_active: bool):
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
    with get_connection() as conn:
        admin = conn.execute(text("""
            SELECT id, telegram_id, username, is_active
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
        "branches": branches
    }


def delete_admin_db(user_id: int):
    with get_connection() as conn:
        conn.execute(text("""
            DELETE FROM user_branches
            WHERE user_id = :user_id
        """), {"user_id": user_id})

        conn.execute(text("""
            DELETE FROM users
            WHERE id = :user_id
              AND is_admin = TRUE
        """), {"user_id": user_id})

    return {"status": "success"}


def create_branch_db(name: str, current_user_id: int):
    with get_connection() as conn:
        branch_id = conn.execute(text("""
            INSERT INTO branches (name)
            VALUES (:name)
            RETURNING id
        """), {"name": name}).scalar()

        conn.execute(text("""
            INSERT INTO user_branches (user_id, branch_id)
            VALUES (:uid, :bid)
        """), {
            "uid": current_user_id,
            "bid": branch_id
        })

    return branch_id


def delete_branch_db(branch_id: int):
    with get_connection() as conn:
        exists = conn.execute(text("""
            SELECT 1
            FROM bookings
            WHERE branch_id = :branch_id
            LIMIT 1
        """), {"branch_id": branch_id}).mappings().fetchone()

        if exists:
            raise {
                "status": "error",
                "message": "Branch has bookings and cannot be deleted"
            }

        conn.execute(text("""
            DELETE FROM user_branches
            WHERE branch_id = :branch_id
        """), {"branch_id": branch_id})

        conn.execute(text("""
            DELETE FROM branches
            WHERE id = :branch_id
        """), {"branch_id": branch_id})

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
            SELECT password_hash
            FROM users
            WHERE id = :user_id
        """), {"user_id": user_id}).mappings().fetchone()

        if not row:
            return {"status": "error", "message": "User not found"}

        if not verify_password(old_password, row[0]):
            raise {
                "status": "error",
                "message": "Old password is incorrect"
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