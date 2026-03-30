import os
from sqlalchemy import create_engine, event

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    pool_timeout=30,
)


@event.listens_for(engine, "connect")
def set_db_timezone(dbapi_connection, connection_record):
    # PostgreSQL session timezone for CURRENT_DATE/CURRENT_TIMESTAMP consistency.
    try:
        cur = dbapi_connection.cursor()
        cur.execute("SET TIME ZONE 'Asia/Tashkent'")
        cur.close()
    except Exception:
        # Keep app running for non-Postgres test environments.
        pass

