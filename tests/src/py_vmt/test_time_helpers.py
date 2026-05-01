import pytest
from datetime import timedelta
from py_vmt.time_helpers import format_time_delta

def test_format_time_delta():
    # less than a minute
    thirty_seconds = timedelta(seconds=30)
    assert "30s" == format_time_delta(thirty_seconds)

    # one minute exactly
    one_minute = timedelta(seconds=60)
    assert "1m" == format_time_delta(one_minute)

    # more than a minute
    assert "1m30s" == format_time_delta(one_minute + thirty_seconds)

    # bunch of minutes and seconds
    delta = timedelta(minutes=24, seconds=8)
    assert "24m8s" == format_time_delta(delta)

    # one hour exactly
    one_hour = timedelta(hours=1)
    assert "1h" == format_time_delta(one_hour)

    # more than one hour
    assert "1h24m" == format_time_delta(one_hour + delta)