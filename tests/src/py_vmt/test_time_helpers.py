import pytest
from datetime import timedelta
from py_vmt.time_helpers import format_time_delta

@pytest.mark.parametrize("input,expected", [
    (timedelta(seconds=30), "30s"),
    (timedelta(seconds=60), "1m"),
    (timedelta(seconds=90), "1m30s"),
    (timedelta(minutes=24, seconds=8), "24m8s"),
    (timedelta(hours=1), "1h"),
    (timedelta(hours=1, minutes=24, seconds=8), "1h24m"),
    (timedelta(seconds=87000), "24h10m")
])
def test_format_time_delta(input, expected):
    assert format_time_delta(input) == expected