import dateparser
from datetime import datetime, timedelta
import math


def parse_to_datetime(at: str) -> datetime:
    settings = {"TO_TIMEZONE": "UTC", "RETURN_AS_TIMEZONE_AWARE": True}
    return dateparser.parse(at, settings=settings)


def format_time_delta(diff: timedelta) -> str:
    total_seconds = int(diff.total_seconds())

    hours, remainder = divmod(total_seconds, 3600)
    minutes, remainder = divmod(remainder, 60)
    seconds = remainder

    hour_str = _format_amount_with_suffix(hours, "h")
    min_str = _format_amount_with_suffix(minutes, "m")
    sec_str = _format_amount_with_suffix(seconds, "s")

    if hour_str:
        return f"{hour_str}{min_str}"
    else:
        return f"{min_str}{sec_str}"


def _format_amount_with_suffix(amount, suffix):
    str = ""
    if amount > 0:
        str = f"{amount}{suffix}"

    return str

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
