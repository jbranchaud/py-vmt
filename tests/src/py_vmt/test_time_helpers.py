import pytest
from datetime import datetime, timezone, timedelta
from py_vmt.time_helpers import format_time_delta, find_nearest_timestamp_interval


@pytest.mark.parametrize(
    "input,expected",
    [
        (timedelta(seconds=30), "30s"),
        (timedelta(seconds=60), "1m"),
        (timedelta(seconds=90), "1m30s"),
        (timedelta(minutes=24, seconds=8), "24m8s"),
        (timedelta(hours=1), "1h"),
        (timedelta(hours=1, minutes=24, seconds=8), "1h24m"),
        (timedelta(seconds=87000), "24h10m"),
    ],
)
def test_format_time_delta(input, expected):
    assert format_time_delta(input) == expected


@pytest.mark.parametrize(
    "input,expected_diff",
    [
        (timedelta(minutes=45), timedelta(minutes=45)),
        (timedelta(minutes=46), timedelta(minutes=45)),
        (timedelta(minutes=44), timedelta(minutes=45)),
        (timedelta(minutes=60), timedelta(minutes=60)),
        (timedelta(minutes=61), timedelta(minutes=60)),
        (timedelta(minutes=74), timedelta(minutes=75)),
        (timedelta(minutes=52), timedelta(minutes=45)),
        (timedelta(minutes=53), timedelta(minutes=60)),
        (timedelta(minutes=52, seconds=31), timedelta(minutes=60)),
        (timedelta(minutes=52, seconds=30), timedelta(minutes=45)),
    ],
)
def test_find_nearest_timestamp_interval(input: timedelta, expected_diff: timedelta):
    start_time = datetime(2026, 3, 14, 15, 5, 11, 0, timezone.utc)
    end_time = start_time + input

    result = find_nearest_timestamp_interval(
        start_time, end_time, timedelta(minutes=15)
    )

    expected = start_time + expected_diff
    assert result == expected
