from datetime import datetime, date
from zoneinfo import ZoneInfo

APP_TZ_NAME = "Asia/Tashkent"
APP_TZ = ZoneInfo(APP_TZ_NAME)


def app_now() -> datetime:
    return datetime.now(APP_TZ)


def app_now_naive() -> datetime:
    # Keep compatibility with DB fields stored as timestamp without timezone.
    return app_now().replace(tzinfo=None)


def app_today() -> date:
    return app_now().date()

