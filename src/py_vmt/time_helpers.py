import dateparser
from datetime import datetime, timezone
import math


def parse_to_datetime(at: str) -> datetime:
    settings = {"TO_TIMEZONE": "UTC", "RETURN_AS_TIMEZONE_AWARE": True}
    return dateparser.parse(at, settings=settings)


def format_time_delta(diff) -> str:
    if diff.seconds < 60:
        return f"{diff.seconds}s"

    minutes = math.floor(diff.seconds / 60)
    return f"{minutes}m"


def format_timestamp(utc_datetime: datetime) -> str:
    # H:MM[AM|PM], e.g. 6:32PM
    format = "%-I:%M%p"

    assert utc_datetime.tzinfo is not None and utc_datetime.tzinfo is timezone.utc

    # Make sure to convert to local time (with `astimezone()`) before formatting
    # the string.
    local_datetime = utc_datetime.astimezone()
    return local_datetime.strftime(format)
