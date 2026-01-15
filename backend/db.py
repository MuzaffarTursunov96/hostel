import sqlite3
from datetime import date
from security import hash_password,verify_password



DB_NAME = "hostel.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # ---------- BRANCHES ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS branches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    """)
    

    # ---------- ROOMS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        number TEXT NOT NULL,
        description TEXT,
        branch_id INTEGER NOT NULL,
        UNIQUE(number, branch_id),
        FOREIGN KEY(branch_id) REFERENCES branches(id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
                CREATE TABLE IF NOT EXISTS customer_passport_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                image_path TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
            );
            """)

    # ---------- BEDS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS beds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id INTEGER NOT NULL,
        status TEXT DEFAULT 'free',
        branch_id INTEGER NOT NULL,
        bed_number INTEGER,
        FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE,
        FOREIGN KEY(branch_id) REFERENCES branches(id) ON DELETE CASCADE
    )
    """)

    # ---------- BOOKINGS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        branch_id INTEGER NOT NULL,
        customer_name TEXT NOT NULL,
        contact TEXT,
        passport_id TEXT,
        room_id INTEGER NOT NULL,
        bed_id INTEGER NOT NULL,

        total_amount REAL NOT NULL,
        paid_amount REAL NOT NULL DEFAULT 0,
        remaining_amount REAL NOT NULL,
        payment_status TEXT NOT NULL,

        checkin_date DATE NOT NULL,
        checkout_date DATE NOT NULL,
        status TEXT DEFAULT 'active',
        booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(branch_id) REFERENCES branches(id),
        FOREIGN KEY(room_id) REFERENCES rooms(id),
        FOREIGN KEY(bed_id) REFERENCES beds(id)
    )
    """)

    # ---------- EXPENSES ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        branch_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        amount REAL NOT NULL,
        expense_date DATE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(branch_id) REFERENCES branches(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS booking_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        paid_amount REAL NOT NULL,
        paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        paid_by TEXT DEFAULT 'customer',

        FOREIGN KEY(booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
        FOREIGN KEY(branch_id) REFERENCES branches(id)
    )
    """)

    # ---------- DEFAULT BRANCH ----------
    cur.execute("""
        INSERT INTO branches (name)
        SELECT 'Main Branch'
        WHERE NOT EXISTS (SELECT 1 FROM branches)
    """)

    # ---------- USERS (ADMIN AUTH) ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        telegram_id INTEGER UNIQUE,
        is_admin INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        branch_id INTEGER,
        language TEXT DEFAULT 'ru',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ------------ CUSTOMER ---------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        branch_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        passport_id TEXT,
        contact TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_branches (
        user_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        PRIMARY KEY (user_id, branch_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (branch_id) REFERENCES branches(id)
    )
    """)

    conn.commit()
    conn.close()

def get_rooms_with_beds(branch_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            rooms.id,
            rooms.number AS room_number,
            COUNT(beds.id) AS bed_count
        FROM rooms
        LEFT JOIN beds 
            ON beds.room_id = rooms.id
           AND beds.branch_id = rooms.branch_id
        WHERE rooms.branch_id = ?
        GROUP BY rooms.id, rooms.number
        ORDER BY rooms.number ASC
    """, (branch_id,))

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r["id"],
            "room_number": r["room_number"],
            "bed_count": r["bed_count"]
        }
        for r in rows
    ]

def get_available_beds(branch_id, room_id, checkin_date, checkout_date):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            b.id,
            b.bed_number,
            b.room_id
        FROM beds b
        WHERE b.branch_id = ?
          AND b.room_id = ?
          AND NOT EXISTS (
              SELECT 1
              FROM bookings bk
              WHERE bk.branch_id = b.branch_id
                AND bk.bed_id = b.id
                AND bk.status = 'active'          -- ✅ THIS LINE FIXES IT
                AND bk.checkin_date < ?
                AND bk.checkout_date > ?
          )
        ORDER BY b.id
    """, (
        branch_id,
        room_id,
        checkout_date,
        checkin_date
    ))

    beds = cur.fetchall()
    conn.close()
    return beds




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
    conn = get_connection()
    cur = conn.cursor()

    # -----------------------------
    # 1️⃣ Check bed availability
    # -----------------------------
    cur.execute("""
        SELECT COUNT(*) FROM bookings
        WHERE branch_id = ?
          AND bed_id = ?
          AND status = 'active'
          AND NOT (
              checkout_date <= ?
              OR checkin_date >= ?
          )
    """, (branch_id, bed_id, checkin_date, checkout_date))

    if cur.fetchone()[0] > 0:
        conn.close()
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
    cur.execute("""
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
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
    """, (
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
        checkout_date
    ))

    booking_id = cur.lastrowid

    if paid_amount > 0:
        cur.execute("""
            INSERT INTO booking_payments (
                booking_id,
                branch_id,
                paid_amount,
                paid_by
            )
            VALUES (?, ?, ?, ?)
        """, (
            booking_id,
            branch_id,
            paid_amount,
            "customer"
        ))

    # -----------------------------
    # 4️⃣ Mark bed as busy
    # -----------------------------
    # cur.execute("""
    #     UPDATE beds
    #     SET status = 'busy'
    #     WHERE id = ? AND branch_id = ?
    # """, (bed_id, branch_id))

    conn.commit()
    conn.close()



def is_bed_busy_today(branch_id, bed_id):
    today = date.today()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 1
        FROM bookings
        WHERE branch_id = ?
          AND bed_id = ?
          AND status = 'active'
          AND checkin_date <= ?
          AND checkout_date > ?
        LIMIT 1
    """, (branch_id, bed_id, today, today))

    busy = cur.fetchone() is not None
    conn.close()
    return busy

def get_active_booking_now(branch_id, bed_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM bookings
        WHERE branch_id = ?
          AND bed_id = ?
          AND status = 'active'
          AND checkin_date <= DATE('now')
          AND checkout_date > DATE('now')
        LIMIT 1
    """, (branch_id, bed_id))

    row = cur.fetchone()
    conn.close()
    return row



def migrate_payments():
    conn = get_connection()
    cur = conn.cursor()

    columns = [c[1] for c in cur.execute("PRAGMA table_info(bookings)").fetchall()]

    if "total_amount" not in columns:
        cur.execute("ALTER TABLE bookings ADD COLUMN total_amount REAL")

    if "paid_amount" not in columns:
        cur.execute("ALTER TABLE bookings ADD COLUMN paid_amount REAL")

    if "remaining_amount" not in columns:
        cur.execute("ALTER TABLE bookings ADD COLUMN remaining_amount REAL")

    if "payment_status" not in columns:
        cur.execute("ALTER TABLE bookings ADD COLUMN payment_status TEXT")

    


    conn.commit()
    conn.close()


def get_debt_summary(branch_id, from_date, to_date):
    """
    Returns total paid vs remaining debt
    for bookings whose checkout is in the given range
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            SUM(paid_amount) AS paid,
            SUM(remaining_amount) AS remaining
        FROM bookings
        WHERE branch_id = ?
          AND DATE(checkout_date) BETWEEN ? AND ?
          AND status IN ('active', 'completed')
    """, (branch_id, from_date, to_date))

    row = cur.fetchone()
    conn.close()

    return {
        "paid": row["paid"] or 0,
        "remaining": row["remaining"] or 0
    }



def get_debts_by_range(branch_id, from_date, to_date):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
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
        WHERE b.branch_id = ?
          AND b.remaining_amount > 0
          AND b.checkin_date >= ?
          AND b.checkin_date <= ?
        ORDER BY b.checkin_date
    """, (branch_id, from_date, to_date))

    rows = cur.fetchall()
    conn.close()
    return rows


def pay_booking_amount(branch_id, booking_id, pay_amount, paid_by="customer"):
    if pay_amount <= 0:
        raise ValueError("Invalid payment amount")

    conn = get_connection()
    cur = conn.cursor()

    # get current totals
    cur.execute("""
        SELECT total_amount, paid_amount
        FROM bookings
        WHERE id=? AND branch_id=?
    """, (booking_id, branch_id))

    row = cur.fetchone()
    if not row:
        conn.close()
        raise ValueError("Booking not found")

    total, paid = row
    new_paid = paid + pay_amount
    remaining = max(total - new_paid, 0)

    payment_status = (
        "paid" if remaining == 0 else "partial"
    )

    # update booking
    cur.execute("""
        UPDATE bookings
        SET paid_amount=?,
            remaining_amount=?,
            payment_status=?
        WHERE id=? AND branch_id=?
    """, (
        new_paid,
        remaining,
        payment_status,
        booking_id,
        branch_id
    ))

    # 🔥 INSERT PAYMENT HISTORY
    cur.execute("""
        INSERT INTO booking_payments (
            booking_id,
            branch_id,
            paid_amount,
            paid_by
        )
        VALUES (?, ?, ?, ?)
    """, (
        booking_id,
        branch_id,
        pay_amount,
        paid_by
    ))

    conn.commit()
    conn.close()


def add_expense(branch_id, title, category, amount, expense_date):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO expenses (branch_id, title, category, amount, expense_date)
        VALUES (?, ?, ?, ?, ?)
    """, (branch_id, title, category, amount, expense_date))

    conn.commit()
    conn.close()


def get_expenses_by_month(branch_id, year, month):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM expenses
        WHERE branch_id=?
          AND strftime('%Y', expense_date)=?
          AND strftime('%m', expense_date)=?
        ORDER BY expense_date DESC
    """, (branch_id, str(year), f"{month:02}"))

    rows = cur.fetchall()
    conn.close()
    return rows

def get_monthly_finance(branch_id, year, month):
    conn = get_connection()
    cur = conn.cursor()

    # INCOME + DEBT
    cur.execute("""
        SELECT
            SUM(paid_amount) AS income,
            SUM(remaining_amount) AS debt
        FROM bookings
        WHERE branch_id=?
          AND strftime('%Y', booking_date)=?
          AND strftime('%m', booking_date)=?
    """, (branch_id, str(year), f"{month:02}"))

    row = cur.fetchone()
    income = row["income"] or 0
    debt = row["debt"] or 0

    # EXPENSES
    cur.execute("""
        SELECT SUM(amount) AS expenses
        FROM expenses
        WHERE branch_id=?
          AND strftime('%Y', expense_date)=?
          AND strftime('%m', expense_date)=?
    """, (branch_id, str(year), f"{month:02}"))

    expenses = cur.fetchone()["expenses"] or 0

    conn.close()
    return {
        "income": income,
        "expenses": expenses,
        "debt": debt
    }

def get_yearly_finance(branch_id, year):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            SUM(paid_amount) AS income,
            SUM(remaining_amount) AS debt
        FROM bookings
        WHERE branch_id=?
          AND strftime('%Y', booking_date)=?
    """, (branch_id, str(year)))

    row = cur.fetchone()
    income = row["income"] or 0
    debt = row["debt"] or 0

    cur.execute("""
        SELECT SUM(amount) AS expenses
        FROM expenses
        WHERE branch_id=?
          AND strftime('%Y', expense_date)=?
    """, (branch_id, str(year)))

    expenses = cur.fetchone()["expenses"] or 0

    conn.close()
    return {
        "income": income,
        "expenses": expenses,
        "debt": debt
    }


# ================= EXPENSE CATEGORY =================
def get_expense_category_stats(branch_id, year, month=None):
    conn = get_connection()
    cur = conn.cursor()

    if month:
        cur.execute("""
            SELECT category, SUM(amount) AS total
            FROM expenses
            WHERE branch_id=?
              AND strftime('%Y', expense_date)=?
              AND strftime('%m', expense_date)=?
            GROUP BY category
        """, (branch_id, str(year), f"{month:02}"))
    else:
        cur.execute("""
            SELECT category, SUM(amount) AS total
            FROM expenses
            WHERE branch_id=?
              AND strftime('%Y', expense_date)=?
            GROUP BY category
        """, (branch_id, str(year)))

    rows = cur.fetchall()
    conn.close()

    return {r["category"]: r["total"] for r in rows}

def pay_booking_debt(branch_id, booking_id, pay_amount):
    if pay_amount <= 0:
        raise ValueError("Invalid payment amount")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT paid_amount, remaining_amount
        FROM bookings
        WHERE id=? AND branch_id=?
    """, (booking_id, branch_id))

    row = cur.fetchone()
    if not row:
        conn.close()
        raise ValueError("Booking not found")

    paid = row["paid_amount"]
    remaining = row["remaining_amount"]

    if pay_amount > remaining:
        conn.close()
        raise ValueError("Payment exceeds remaining debt")

    new_paid = paid + pay_amount
    new_remaining = remaining - pay_amount

    status = "paid" if new_remaining == 0 else "partial"

    cur.execute("""
        UPDATE bookings
        SET paid_amount=?,
            remaining_amount=?,
            payment_status=?
        WHERE id=? AND branch_id=?
    """, (
        new_paid,
        new_remaining,
        status,
        booking_id,
        branch_id
    ))

    conn.commit()
    conn.close()



# ================= BRANCHES =================

def get_branches(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT b.id, b.name
        FROM branches b
        JOIN user_branches ub ON ub.branch_id = b.id
        WHERE ub.user_id = ?
        ORDER BY b.name
    """, (user_id,))

    rows = cur.fetchall()
    conn.close()
    return rows



def add_branch(name, user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO branches (name) VALUES (?)",
        (name.strip(),)
    )
    branch_id = cur.lastrowid

    cur.execute(
        "INSERT INTO user_branches (user_id, branch_id) VALUES (?, ?)",
        (user_id, branch_id)
    )

    conn.commit()
    conn.close()
    return branch_id   # 🔥 IMPORTANT




def update_branch(branch_id, new_name, user_id):
    conn = get_connection()
    cur = conn.cursor()

    # 🔒 SECURITY: update ONLY if branch belongs to user
    cur.execute("""
        UPDATE branches
        SET name = ?
        WHERE id = ?
        AND id IN (
            SELECT branch_id
            FROM user_branches
            WHERE user_id = ?
        )
    """, (
        new_name.strip(),
        branch_id,
        user_id
    ))

    if cur.rowcount == 0:
        conn.close()
        raise Exception("You are not allowed to modify this branch")

    conn.commit()
    conn.close()



def get_payment_history(branch_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            bp.paid_at,
            bp.paid_amount,
            bp.paid_by,
            b.customer_name,
            b.passport_id,
            r.number AS room_number,
            b.bed_number
        FROM booking_payments bp
        JOIN bookings b ON b.id = bp.booking_id
        JOIN rooms r ON r.id = b.room_id
        WHERE bp.branch_id = ?
        ORDER BY bp.paid_at DESC
    """, (branch_id,))

    rows = cur.fetchall()
    conn.close()
    return rows



def get_payment_history_by_month(branch_id, year, month):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
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
    JOIN beds ON beds.id = b.bed_id      -- 🔥 JOIN BEDS
    WHERE bp.branch_id = ?
    AND strftime('%Y', bp.paid_at) = ?
    AND strftime('%m', bp.paid_at) = ?
    ORDER BY bp.paid_at DESC

    """, (
        branch_id,
        str(year),
        f"{month:02d}"
    ))

    rows = cur.fetchall()
    conn.close()
    return rows


def get_payments_by_range(branch_id, start_date, end_date):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
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

        WHERE bp.branch_id = ?
          AND DATE(bp.paid_at) BETWEEN ? AND ?
        ORDER BY bp.paid_at DESC
    """, (branch_id, start_date, end_date))

    rows = cur.fetchall()
    conn.close()
    return rows


def cancel_booking(booking_id: int, branch_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE bookings
        SET status = 'canceled'
        WHERE id = ?
          AND branch_id = ?
          AND status = 'active'
    """, (booking_id, branch_id))

    conn.commit()
    conn.close()




def update_booking(booking_id, bed_id, checkin, checkout, total_amount):
    conn = get_connection()
    cur = conn.cursor()

    # ❗ Check overlap EXCLUDING this booking
    cur.execute("""
        SELECT 1 FROM bookings
        WHERE bed_id = ?
          AND status = 'active'
          AND id != ?
          AND checkin_date < ?
          AND checkout_date > ?
        LIMIT 1
    """, (bed_id, booking_id, checkout, checkin))

    if cur.fetchone():
        conn.close()
        raise Exception("Selected bed is not available for these dates")

    cur.execute("""
        UPDATE bookings
        SET bed_id = ?,
            checkin_date = ?,
            checkout_date = ?,
            total_amount = ?
        WHERE id = ?
    """, (
        bed_id,
        checkin,
        checkout,
        total_amount,
        booking_id
    ))

    conn.commit()
    conn.close()

def update_booking_admin(
    booking_id,
    room_id,
    bed_id,
    checkout_date,
    total_amount
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE bookings
        SET
            room_id = ?,
            bed_id = ?,
            checkout_date = ?,
            total_amount = ?
        WHERE id = ?
    """, (
        room_id,
        bed_id,
        checkout_date,
        total_amount,
        booking_id
    ))

    conn.commit()
    conn.close()

    recalc_booking_finance(booking_id)


def get_past_bookings(branch_id, from_date=None, to_date=None):
    conn = get_connection()
    cur = conn.cursor()

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
        WHERE bk.branch_id = ?
          AND bk.checkout_date < ?
    """

    params = [branch_id, today]

    if from_date:
        sql += " AND bk.checkin_date >= ?"
        params.append(from_date)

    if to_date:
        sql += " AND bk.checkout_date <= ?"
        params.append(to_date)

    sql += " ORDER BY bk.checkout_date DESC"

    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows



def get_active_bookings(branch_id):
    conn = get_connection()
    cur = conn.cursor()

    today = date.today().isoformat()  # YYYY-MM-DD

    cur.execute("""
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
        WHERE bk.branch_id = ?
          AND bk.status = 'active'
          AND bk.checkin_date <= ?
          AND bk.checkout_date > ?
        ORDER BY bk.checkout_date
    """, (branch_id, today, today))

    rows = cur.fetchall()
    conn.close()
    return rows

def create_admin_if_not_exists():
    conn = get_connection()
    cur = conn.cursor()

    try:
        # if any user exists, do nothing
        cur.execute("SELECT id FROM users LIMIT 1")
        if cur.fetchone():
            return

        # ensure branch exists
        cur.execute("SELECT id FROM branches LIMIT 1")
        row = cur.fetchone()

        if row:
            branch_id = row["id"]
        else:
            cur.execute(
                "INSERT INTO branches (name) VALUES (?)",
                ("Main Branch",)
            )
            branch_id = cur.lastrowid

        # create admin user
        cur.execute("""
            INSERT INTO users (username, password_hash, is_admin)
            VALUES (?, ?, 1)
        """, (
            "admin",
            hash_password("admin123")
        ))

        user_id = cur.lastrowid

        # bind admin to branch
        cur.execute("""
            INSERT INTO user_branches (user_id, branch_id)
            VALUES (?, ?)
        """, (user_id, branch_id))

        conn.commit()

    finally:
        conn.close()

# ================= BEDS CRUD =================

def add_bed(branch_id, room_id):
    conn = get_connection()
    cur = conn.cursor()

    # get next bed number INSIDE THIS ROOM
    cur.execute("""
        SELECT COALESCE(MAX(bed_number), 0) + 1
        FROM beds
        WHERE room_id=? AND branch_id=?
    """, (room_id, branch_id))

    next_number = cur.fetchone()[0]

    cur.execute("""
        INSERT INTO beds (branch_id, room_id, bed_number)
        VALUES (?, ?, ?)
    """, (branch_id, room_id, next_number))

    conn.commit()
    conn.close()



def delete_bed(bed_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM beds WHERE id = ?", (bed_id,))
    conn.commit()
    conn.close()


def get_beds(branch_id, room_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, bed_number
        FROM beds
        WHERE branch_id=? AND room_id=?
        ORDER BY bed_number
    """, (branch_id, room_id))

    rows = cur.fetchall()
    conn.close()
    return rows

def busy_beds_now(branch_id, room_id):
    today = date.today().isoformat()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT beds.id
        FROM beds
        JOIN bookings bk ON bk.bed_id = beds.id
        WHERE beds.branch_id = ?
          AND beds.room_id = ?
          AND bk.status = 'active'
          AND bk.checkin_date <= ?
          AND bk.checkout_date > ?
    """, (branch_id, room_id, today, today))

    rows = cur.fetchall()
    conn.close()
    return {
        "busy_beds": [r["id"] for r in rows]
    }



def get_beds_with_busy_like_dashboard(branch_id: int, room_id: int):
    today = date.today().isoformat()

    # 1️⃣ get all beds
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, bed_number
        FROM beds
        WHERE branch_id = ?
          AND room_id = ?
        ORDER BY bed_number
    """, (branch_id, room_id))

    beds = cur.fetchall()

    # 2️⃣ reuse DASHBOARD LOGIC
    busy = get_busy_beds_from_db(
        branch_id=branch_id,
        room_id=room_id,
        checkin=today,
        checkout=today
    )["busy_beds"]

    busy_set = set(busy)

    conn.close()

    return [
        {
            "id": b["id"],
            "bed_number": b["bed_number"],
            "busy": b["id"] in busy_set
        }
        for b in beds
    ]

def get_beds_with_booking_status(room_id: int, branch_id: int):
    conn = get_connection()
    cur = conn.cursor()

    today = date.today().isoformat()

    cur.execute("""
        SELECT
            beds.id AS bed_id,
            beds.bed_number,
            EXISTS (
                SELECT 1
                FROM bookings bk
                WHERE bk.branch_id = beds.branch_id
                  AND bk.bed_id = beds.id
                  AND bk.status = 'active'
                  AND bk.checkin_date <= ?
                  AND bk.checkout_date > ?
            ) AS busy
        FROM beds
        WHERE beds.room_id = ?
          AND beds.branch_id = ?
        ORDER BY beds.bed_number
    """, (today, today, room_id, branch_id))

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r["bed_id"],
            "bed_number": r["bed_number"],
            "busy": bool(r["busy"])
        }
        for r in rows
    ]

def bed_future_exists(branch_id, bed_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 1
        FROM bookings
        WHERE branch_id = ?
          AND bed_id = ?
          AND status = 'active'
          AND checkin_date > DATE('now')
        LIMIT 1
    """, (branch_id, bed_id))

    exists = cur.fetchone() is not None
    conn.close()
    return exists

def get_future_bookings(branch_id, bed_id):
    conn = get_connection()
    cur = conn.cursor()

    today = date.today().isoformat()

    cur.execute(
        """
        SELECT
            bk.id,                    -- 🔥 REQUIRED
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
        WHERE bk.branch_id = ?
          AND bk.bed_id = ?
          AND bk.status = 'active'
          AND bk.checkin_date > ?
        ORDER BY bk.checkin_date
        """,
        (branch_id, bed_id, today)
    )

    rows = cur.fetchall()
    conn.close()

    result = []
    for r in rows:
        result.append({
            "id": r["id"],                      # 🔥 REQUIRED
            "room_id": r["room_id"],
            "bed_id": r["bed_id"],
            "bed_number": r["bed_number"],
            "room_number": r["room_number"],
            "customer_name": r["customer_name"],
            "passport_id": r["passport_id"],
            "checkin_date": r["checkin_date"],
            "checkout_date": r["checkout_date"],
            "total_amount": r["total_amount"],
        })

    return result


def is_bed_free_in_range(branch_id, bed_id, start_date, end_date):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT 1
        FROM bookings
        WHERE branch_id = ?
          AND bed_id = ?
          AND status = 'active'
          AND checkin_date < ?
          AND checkout_date > ?
        LIMIT 1
        """,
        (branch_id, bed_id, end_date, start_date)
    )


    busy = cur.fetchone() is not None
    conn.close()

    return not busy

def add_or_get_customer(branch_id, name, passport_id, contact):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id FROM customers
        WHERE branch_id=? AND passport_id=?
    """, (branch_id, passport_id))

    row = cur.fetchone()

    if row:
        return row["id"]

    cur.execute("""
        INSERT INTO customers (branch_id, name, passport_id, contact)
        VALUES (?, ?, ?, ?)
    """, (branch_id, name, passport_id, contact))

    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return cid


def get_customers(branch_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            c.id,                 -- ✅ REQUIRED
            c.name,
            c.passport_id,
            c.contact,

            -- ✅ metadata only (NO images)
            (
                SELECT COUNT(*)
                FROM customer_passport_images pi
                WHERE pi.customer_id = c.id
            ) AS passport_image_count

        FROM customers c
        WHERE c.branch_id = ?
        ORDER BY c.name
    """, (branch_id,))

    rows = cur.fetchall()
    conn.close()
    return rows


def recalc_booking_finance(booking_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            total_amount,
            COALESCE(SUM(bp.paid_amount), 0) AS paid
        FROM bookings b
        LEFT JOIN booking_payments bp ON bp.booking_id = b.id
        WHERE b.id = ?
    """, (booking_id,))

    row = cur.fetchone()
    if not row:
        conn.close()
        return

    total = row["total_amount"]
    paid = row["paid"]
    remaining = max(total - paid, 0)

    status = (
        "paid" if remaining == 0
        else "partial" if paid > 0
        else "unpaid"
    )

    cur.execute("""
        UPDATE bookings
        SET
            paid_amount = ?,
            remaining_amount = ?,
            payment_status = ?
        WHERE id = ?
    """, (paid, remaining, status, booking_id))

    conn.commit()
    conn.close()


def get_busy_beds_from_db(branch_id: int,
        room_id: int,
        checkin: date,
        checkout: date,
        exclude_booking_id: int | None = None):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT DISTINCT bed_id
        FROM bookings
        WHERE branch_id = ?
          AND room_id = ?
          AND NOT (
            checkout_date <= ?
            OR checkin_date >= ?
          )
    """
    params = [branch_id, room_id, checkin, checkout]

    if exclude_booking_id:
        query += " AND id != ?"
        params.append(exclude_booking_id)

    cur.execute(query, params)
    busy = {row["bed_id"] for row in cur.fetchall()}

    conn.close()
    return {"busy_beds": list(busy)}

def check_room_had_booked(room_id: int, branch_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 1
        FROM bookings
        WHERE room_id=? AND branch_id=?
          AND status IN ('active', 'future')
        LIMIT 1
    """, (room_id, branch_id))

    exists = cur.fetchone() is not None
    conn.close()

    return {"has_booking": exists}

def check_bed_has_booked(bed_id: int, branch_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 1
        FROM bookings
        WHERE bed_id=? AND branch_id=?
          AND status IN ('active', 'future')
        LIMIT 1
    """, (bed_id, branch_id))

    exists = cur.fetchone() is not None
    conn.close()

    return {"has_booking": exists}


def login(username: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, password_hash, is_admin, branch_id, language, telegram_id
        FROM users
        WHERE username=? AND is_active=1
    """, (username,))

    u = cur.fetchone()
    conn.close()
    return u

def telegram_login_db(telegram_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
       SELECT id, is_admin, branch_id, language
        FROM users
        WHERE telegram_id=? AND is_active=1
    """, (telegram_id,))

    u = cur.fetchone()
    conn.close()
    return u

def user_auto_create(telegram_id: int,username: str):
    conn = get_connection()
    cur = conn.cursor()

    # ensure branch exists
    cur.execute("""
            INSERT INTO users (telegram_id, username, is_admin, is_active)
            VALUES (?, ?, 0, 1)
        """, (telegram_id, username))
    conn.commit()
    conn.close()
    return cur.lastrowid

def remove_bed_db(bed_id: int, branch_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT room_id FROM beds WHERE id=? AND branch_id=?",
        (bed_id, branch_id)
    )
    row = cur.fetchone()
    conn.close()
    return row

def upload_passport_image_db(customer_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM customer_passport_images WHERE customer_id = ?",
        (customer_id,)
    )
    existing_count = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return existing_count

def image_path(customer_id: int, filename: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
            """
            INSERT INTO customer_passport_images (customer_id, image_path)
            VALUES (?, ?)
            """,
            (customer_id, f"/static/passports/{filename}")
        )

    conn.commit()
    conn.close()

def get_image_paths(customer_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, image_path
        FROM customer_passport_images
        WHERE customer_id = ?
        ORDER BY id
        LIMIT 4
        """,
        (customer_id,)
    )
    images = [{"id": r[0], "path": r[1]} for r in cur.fetchall()]
    conn.close()
    return {"images": images}

def select_passport_image(image_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT image_path FROM customer_passport_images WHERE id = ?",
        (image_id,)
    )
    row = cur.fetchone()

    conn.commit()
    conn.close()
    return row

def delete_passport_image_db(image_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM customer_passport_images WHERE id = ?",
        (image_id,)
    )

    conn.commit()
    conn.close()

def get_dashboard_rooms(branch_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, number
        FROM rooms
        WHERE branch_id = ?
        ORDER BY number
    """, (branch_id,))

    rows = cur.fetchall()
    conn.close()
    return rows

def get_dashboard_beds(branch_id: int, room_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
            """
            SELECT id, bed_number
            FROM beds
            WHERE room_id=? AND branch_id=?
            ORDER BY bed_number
            """,
            (room_id, branch_id)
        )
    rows = cur.fetchall()
    conn.close()
    return rows

def export_monthly_data_db(year,month,branch_id:int):
    conn = get_connection()
    import pandas as pd
 

    df = pd.read_sql_query("""
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
        WHERE strftime('%Y', b.booking_date)=?
          AND strftime('%m', b.booking_date)=?
          AND b.branch_id=?
        ORDER BY b.booking_date ASC
    """, conn, params=(str(year), f"{month:02}", branch_id))

    conn.close()

    return df.to_dict(orient="records")

def create_room_db(number: str, branch_id: int):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO rooms (number, branch_id) VALUES (?, ?)",
            (number, branch_id)
        )
        conn.commit()
        
        return {"status": "success"}

    except Exception:
        conn.rollback()
        return {"status": "error"}
    finally:
        conn.close()
    

    return {"status": "ok"}

def delete_room_db(room_id: int, branch_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 1
        FROM bookings
        WHERE room_id=? AND branch_id=?
          AND status IN ('active', 'future')
        LIMIT 1
    """, (room_id, branch_id))


    if cur.fetchone():
        conn.close()
        return {"status": "error", "message": "Room has active or future bookings"}
    
    cur.execute(
        "DELETE FROM beds WHERE room_id=? AND branch_id=?",
        (room_id, branch_id)
    )
    cur.execute(
        "DELETE FROM rooms WHERE id=? AND branch_id=?",
        (room_id, branch_id)
    )

    conn.commit()
    conn.close()
    return {"status": "success"}


def create_admin_from_root(telegram_id: int, username: str, password: str):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM users WHERE telegram_id=?",
        (telegram_id,)
    )
    if cur.fetchone():
        conn.close()
        return {"status": "error", "message": "User with this Telegram ID already exists"}

    cur.execute("""
        INSERT INTO users (telegram_id, username, password_hash, is_admin)
        VALUES (?, ?, ?, 1)
    """, (
        telegram_id,
        username,
        hash_password(password)
    ))

    conn.commit()
    conn.close()

    return {"status": "success"}


def set_admin_branches_db(user_id: int, branch_ids: list[int]):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM user_branches WHERE user_id=?",
        (user_id,)
    )

    for bid in branch_ids:
        cur.execute(
            "INSERT INTO user_branches (user_id, branch_id) VALUES (?, ?)",
            (user_id, bid)
        )

    conn.commit()
    conn.close()

def reset_password_db(new_password: str, user_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET password_hash=?
        WHERE id=?
    """, (hash_password(new_password), user_id))

    conn.commit()
    conn.close()


def list_admins_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, telegram_id, username, is_active
        FROM users
        WHERE is_admin = 1
        ORDER BY id
    """)
    admins = cur.fetchall()

    # fetch branches for each admin
    result = []
    for a in admins:
        cur.execute("""
            SELECT branch_id
            FROM user_branches
            WHERE user_id = ?
        """, (a["id"],))
        branches = [r["branch_id"] for r in cur.fetchall()]

        result.append({
            "id": a["id"],
            "telegram_id": a["telegram_id"],
            "username": a["username"],
            "is_active": bool(a["is_active"]),
            "branches": branches
        })

    conn.close()
    return result

def set_admin_active_db(user_id: int, is_active: bool):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET is_active = ?
        WHERE id = ? AND is_admin = 1
    """, (is_active, user_id))

    conn.commit()
    conn.close()


def get_admin_db(user_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, telegram_id, username, is_active
        FROM users
        WHERE id = ? AND is_admin = 1
    """, (user_id,))

    admin = cur.fetchone()
    if not admin:
        conn.close()
        return {"status": "error", "message": "Admin not found"}

    cur.execute("""
        SELECT branch_id
        FROM user_branches
        WHERE user_id = ?
    """, (user_id,))

    branches = [r["branch_id"] for r in cur.fetchall()]
    conn.close()
    return {
        "status": "success",
        "id": admin["id"],
        "telegram_id": admin["telegram_id"],
        "username": admin["username"],
        "is_active": bool(admin["is_active"]),
        "branches": branches
    }

def delete_admin_db(user_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM user_branches WHERE user_id=?", (user_id,))

    # remove admin user
    cur.execute(
        "DELETE FROM users WHERE id=? AND is_admin=1",
        (user_id,)
    )

    conn.commit()
    conn.close()
    return {"status": "success"}


def create_branch_db(name: str,current_user_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("INSERT INTO branches (name) VALUES (?)", (name,))
    branch_id = cur.lastrowid

    # 🔥 ROOT ALWAYS SEES NEW BRANCH
    cur.execute(
        "INSERT INTO user_branches (user_id, branch_id) VALUES (?, ?)",
        (current_user_id, branch_id)
    )

    conn.commit()
    conn.close()
    return branch_id

def delete_branch_db(branch_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT 1 FROM bookings WHERE branch_id=? LIMIT 1",
        (branch_id,)
    )
    if cur.fetchone():
        conn.close()
        raise {"status": "error", "message": "Branch has bookings and cannot be deleted"}

    cur.execute("DELETE FROM user_branches WHERE branch_id=?", (branch_id,))
    cur.execute("DELETE FROM branches WHERE id=?", (branch_id,))

    conn.commit()
    conn.close()

    return {"status": "success"}

def list_branches_db_root():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM branches ORDER BY id")
    branches = cur.fetchall()
    conn.close()
    return branches

def list_branches_db(user_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
            SELECT b.id, b.name
            FROM branches b
            JOIN user_branches ub ON ub.branch_id = b.id
            WHERE ub.user_id = ?
            ORDER BY b.id
        """, (user_id,))
    branches = cur.fetchall()
    conn.close()
    return branches

def change_password_db(user_id: int, old_password: str, new_password: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT password_hash FROM users WHERE id=?",
        (user_id,)
    )
    row = cur.fetchone()

    if not row:
        conn.close()
        return {"status": "error", "message": "User not found"}

    if not verify_password(old_password, row["password_hash"]):
        conn.close()
        raise {"status": "error", "message": "Old password is incorrect"}

    new_hash = hash_password(new_password)

    cur.execute(
        "UPDATE users SET password_hash=? WHERE id=?",
        (new_hash, user_id)
    )

    conn.commit()
    conn.close()

    return {"status": "success","message": "Password changed successfully"}


def set_lang_db(user_id: int, lang: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "UPDATE users SET language=? WHERE id=?",
        (lang, user_id)
    )

    conn.commit()
    conn.close()