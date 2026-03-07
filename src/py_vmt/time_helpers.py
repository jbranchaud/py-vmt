from datetime import datetime
import math


def format_time_delta(diff) -> str:
    if diff.seconds < 60:
        return f"{diff.seconds}s"

    minutes = math.floor(diff.seconds / 60)
    return f"{minutes}m"


def format_timestamp(utc_datetime: datetime) -> str:
    # H:MM[AM|PM], e.g. 6:32PM
    format = "%-I:%M%p"

    local_datetime = utc_datetime.astimezone()
    return local_datetime.strftime(format)
