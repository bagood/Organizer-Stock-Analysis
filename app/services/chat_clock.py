from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

CHAT_TIMEZONE_NAME = "Asia/Jakarta"
CHAT_TIMEZONE = ZoneInfo(CHAT_TIMEZONE_NAME)


def jakarta_now() -> datetime:
    return datetime.now(CHAT_TIMEZONE)


def jakarta_business_date(now: datetime | None = None) -> date:
    current = now or jakarta_now()
    return current.astimezone(CHAT_TIMEZONE).date()


def jakarta_day_end(business_date: date) -> datetime:
    return datetime.combine(
        business_date + timedelta(days=1), time.min, tzinfo=CHAT_TIMEZONE
    )
