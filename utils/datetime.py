from datetime import date, datetime, timedelta
from typing import Literal, TypeAlias
from zoneinfo import ZoneInfo

import config


Day: TypeAlias = Literal["yesterday", "today", "tomorrow"]
DATE_FORMAT = "%d_%m_%Y"


def _today() -> date:
    return datetime.now(ZoneInfo(config.TIME_ZONE)).date()


def local_datetime(timestamp: int | float | None = None) -> datetime:
    """Return a timezone-aware local datetime for now or a Unix timestamp."""
    zone = ZoneInfo(config.TIME_ZONE)
    if timestamp is None:
        return datetime.now(zone)
    return datetime.fromtimestamp(timestamp, zone)


def date_for_date(day: Day) -> str:
    """Return yesterday, today, or tomorrow in DD_MM_YYYY format."""
    offsets: dict[Day, int] = {
        "yesterday": -1,
        "today": 0,
        "tomorrow": 1,
    }
    try:
        offset = offsets[day]
    except KeyError as error:
        raise ValueError(
            "day must be 'yesterday', 'today', or 'tomorrow'"
        ) from error
    return (_today() + timedelta(days=offset)).strftime(DATE_FORMAT)


def list_of_dates(offset: int, count: int) -> list[str]:
    """Return consecutive dates beginning at today's date plus offset."""
    if not isinstance(offset, int) or isinstance(offset, bool):
        raise TypeError("offset must be an integer")
    if not isinstance(count, int) or isinstance(count, bool):
        raise TypeError("count must be an integer")
    if count < 0:
        raise ValueError("count cannot be negative")

    first_date = _today() + timedelta(days=offset)
    return [
        (first_date + timedelta(days=index)).strftime(DATE_FORMAT)
        for index in range(count)
    ]
