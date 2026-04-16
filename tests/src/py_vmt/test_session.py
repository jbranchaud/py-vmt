from datetime import datetime, timedelta, timezone
from freezegun import freeze_time
import pytest
from py_vmt.session import Session

def test_new_session():
    now = datetime.now()
    sesh = Session(now, "TIL")

    assert sesh.start_time == now
    assert sesh.project_name == "TIL"
    assert not sesh.end_time

def test_new_session_with_end_time():
    now = datetime.now()
    earlier = now - timedelta(hours=3)

    sesh = Session(earlier, "TIL", now)

    assert sesh.start_time == earlier
    assert sesh.project_name == "TIL"
    assert sesh.end_time == now

def test_start():
    initial_datetime = datetime(
        2026, 3, 14, 15, 5, 11, 0, timezone.utc
    )
    with freeze_time(initial_datetime):
        sesh = Session.start("TIL")

        assert sesh.start_time == initial_datetime
        assert sesh.project_name == "TIL"
        assert not sesh.end_time

def test_start_then_stop():
    initial_datetime = datetime(
        2026, 3, 14, 15, 5, 11, 0, timezone.utc
    )
    with freeze_time(initial_datetime) as frozen_datetime:
        sesh = Session.start("TIL")

        assert not sesh.end_time

        frozen_datetime.tick(delta=timedelta(hours=3))

        sesh.stop()

        assert sesh.end_time == (initial_datetime + timedelta(hours=3))

def test_marshal():
    initial_datetime = datetime(
        2026, 3, 14, 15, 5, 11, 0, timezone.utc
    )
    with freeze_time(initial_datetime) as frozen_datetime:
        sesh = Session.start('TIL')

        sesh_data = sesh.marshal()

        assert sesh_data['project_name'] == 'TIL'
        assert sesh_data['start_time'] == '2026-03-14T15:05:11+00:00'
        assert 'end_time' not in sesh_data

        frozen_datetime.tick(delta=timedelta(hours=3))

        sesh.stop()

        sesh_data = sesh.marshal()

        assert sesh_data['project_name'] == 'TIL'
        assert sesh_data['start_time'] == '2026-03-14T15:05:11+00:00'
        assert sesh_data['end_time'] == '2026-03-14T18:05:11+00:00'

def test_hydrate():
    sesh_data = {
        'start_time': '2026-03-14T15:05:11+00:00',
        'project_name': 'TIL',
        'end_time': '2026-03-14T18:05:11+00:00'
    }

    sesh = Session.hydrate(sesh_data)

    expected_start = datetime(
        2026, 3, 14, 15, 5, 11, 0, timezone.utc
    )
    expected_end = datetime(
        2026, 3, 14, 18, 5, 11, 0, timezone.utc
    )

    assert sesh.start_time == expected_start
    assert sesh.project_name == 'TIL'
    assert sesh.end_time == expected_end

def test_hydrate_without_end_time():
    sesh_data = {
        'start_time': '2026-03-14T15:05:11+00:00',
        'project_name': 'TIL',
    }

    sesh = Session.hydrate(sesh_data)

    expected_start = datetime(
        2026, 3, 14, 15, 5, 11, 0, timezone.utc
    )

    assert sesh.start_time == expected_start
    assert sesh.project_name == 'TIL'
    assert not sesh.end_time

def test_hydrate_with_no_start_time():
    sesh_data = {
        "project_name": "TIL"
    }

    with pytest.raises(KeyError) as exception:
        Session.hydrate(sesh_data)

    assert "'start_time'" in str(exception.value)

def test_hydrate_with_invalid_start_time():
    sesh_data = {
        "start_time": "abc123",
        "project_name": "TIL"
    }

    with pytest.raises(ValueError) as exception:
        Session.hydrate(sesh_data)

    assert "Invalid isoformat string: 'abc123'" in str(exception.value)

def test_list_of_sessions_is_sortable():
    now = datetime.now()
    sesh1 = Session(now, "TIL")

    earlier = now + timedelta(minutes=-30)
    sesh2 = Session(earlier, "Client A")

    later = now + timedelta(minutes=20)
    sesh3 = Session(later, "Alpha")

    sessions = [sesh1, sesh2, sesh3]
    sessions.sort()

    assert sessions[0] == sesh2
    assert sessions[1] == sesh1
    assert sessions[2] == sesh3