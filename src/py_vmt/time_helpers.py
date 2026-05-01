import dateparser
from datetime import datetime, timedelta
import math


def parse_to_datetime(at: str) -> datetime:
    settings = {"TO_TIMEZONE": "UTC", "RETURN_AS_TIMEZONE_AWARE": True}
    return dateparser.parse(at, settings=settings)


def format_time_delta(diff) -> str:
    minutes = math.floor(diff.seconds / 60)
    seconds = diff.seconds % 60

    min_str = ""
    if minutes > 0:
        min_str = f"{minutes}m"

    sec_str = ""
    if seconds > 0:
        sec_str = f"{seconds}s"

    return f"{min_str}{sec_str}"


def format_timestamp(utc_datetime: datetime) -> str:
    # H:MM[AM|PM], e.g. 6:32PM
    format = "%-I:%M%p"

    check = utc_datetime.tzinfo is not None and utc_datetime.utcoffset() == timedelta(0)
    msg = f"The given datetime must have tzinfo ({utc_datetime.tzinfo}) with offset of 0 ({utc_datetime.utcoffset()})"
    assert check, msg

    # Make sure to convert to local time (with `astimezone()`) before formatting
    # the string.
    local_datetime = utc_datetime.astimezone()
    return local_datetime.strftime(format)
