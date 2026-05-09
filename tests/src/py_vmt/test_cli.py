from click.testing import CliRunner
import datetime
from freezegun import freeze_time
import pytest
from py_vmt.cli import cli, CliContext


# auto fixture for all test cases that monkeypatches the platform dirs to a tmp
# path so that test side-effects don't persist between runs
@pytest.fixture(autouse=True)
def use_tmp_platform_dirs(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    config_dir = tmp_path / "config"
    data_dir.mkdir()
    config_dir.mkdir()
    monkeypatch.setattr(CliContext, "get_data_dir", staticmethod(lambda: data_dir))
    monkeypatch.setattr(CliContext, "get_config_dir", staticmethod(lambda: config_dir))


def test_no_status():
    runner = CliRunner()
    result = runner.invoke(cli, ["status"])
    assert "Not tracking" in result.output


def test_start_status_stop_flow():
    runner = CliRunner()

    initial_datetime = datetime.datetime(
        2026, 3, 14, 15, 5, 11, 0, datetime.timezone.utc
    )
    with freeze_time(initial_datetime) as frozen_datetime:
        # start a session
        start_result = runner.invoke(cli, ["start", "my-project"])
        output = "Started tracking 'my-project' at 10:05AM"
        assert output in start_result.output

        frozen_datetime.tick(delta=datetime.timedelta(minutes=30))

        # check status
        status_result = runner.invoke(cli, ["status"])
        output = "Tracking 'my-project' for 30m (since 10:05AM)"
        assert output in status_result.output

        frozen_datetime.tick(delta=datetime.timedelta(hours=1))

        # stop a session
        stop_result = runner.invoke(cli, ["stop"])
        output = "Stopped tracking 'my-project' (1h30m)"
        assert output in stop_result.output


def test_start_cancel_flow():
    runner = CliRunner()

    initial_datetime = datetime.datetime(
        2026, 3, 14, 15, 5, 11, 0, datetime.timezone.utc
    )
    with freeze_time(initial_datetime) as frozen_datetime:
        # start a session
        start_result = runner.invoke(cli, ["start", "my-project"])
        output = "Started tracking 'my-project' at 10:05AM"
        assert output in start_result.output

        frozen_datetime.tick(delta=datetime.timedelta(minutes=30))

        # cancel session
        cancel_result = runner.invoke(cli, ["cancel"])
        output = "Cancelled session for 'my-project' (30m)"
        assert output in cancel_result.output


def test_start_at_past_time():
    runner = CliRunner()

    initial_datetime = datetime.datetime(
        2026, 3, 14, 15, 5, 11, 0, datetime.timezone.utc
    )
    with freeze_time(initial_datetime) as frozen_datetime:
        # start a session
        start_result = runner.invoke(
            cli, ["start", "my-project", "--at", "'33 minutes ago'"]
        )
        output = "Started tracking 'my-project' at 9:32AM"
        assert output in start_result.output

        frozen_datetime.tick(delta=datetime.timedelta(minutes=30))

        # check status
        status_result = runner.invoke(cli, ["status"])
        output = "Tracking 'my-project' for 1h3m (since 9:32AM)"
        assert output in status_result.output

def test_start_at_in_future():
    runner = CliRunner()

    initial_datetime = datetime.datetime(
        2026, 3, 14, 15, 5, 11, 0, datetime.timezone.utc
    )
    with freeze_time(initial_datetime):
        # start a session
        start_result = runner.invoke(
            cli, ["start", "my-project", "--at", "'in 23 minutes'"]
        )

        output_lines = [
          "Usage: cli start [OPTIONS] PROJECT_NAME",
          "Try 'cli start --help' for help",
          "Error: Invalid value for '--at': must be a relative time in the past"
        ]
        for output in output_lines:
            assert output in start_result.output


def test_log_recent_activity():
    runner = CliRunner()

    # set up the data dir file with some existing session entries
    initial_datetime = datetime.datetime(
        2026, 3, 14, 15, 5, 11, 0, datetime.timezone.utc
    )
    with freeze_time(initial_datetime) as frozen_datetime:
        # record 8 hour session
        runner.invoke(cli, ["start", "TIL"])
        frozen_datetime.tick(delta=datetime.timedelta(hours=8))
        runner.invoke(cli, ["stop"])

        # 1 day later
        frozen_datetime.tick(delta=datetime.timedelta(hours=13))

        # record another day
        runner.invoke(cli, ["start", "still"])
        frozen_datetime.tick(delta=datetime.timedelta(hours=4, minutes=32))
        runner.invoke(cli, ["stop"])
        frozen_datetime.tick(delta=datetime.timedelta(minutes=28))
        runner.invoke(cli, ["start", "TIL"])
        frozen_datetime.tick(delta=datetime.timedelta(hours=3, minutes=3))
        runner.invoke(cli, ["stop"])

        # to the next day
        frozen_datetime.tick(delta=datetime.timedelta(hours=14))

        # record one more day
        runner.invoke(cli, ["start", "Client A", "--at", "33 minutes ago"])
        frozen_datetime.tick(delta=datetime.timedelta(hours=6))
        runner.invoke(cli, ["stop"])
        frozen_datetime.tick(delta=datetime.timedelta(minutes=15))
        runner.invoke(cli, ["start", "TIL"])
        frozen_datetime.tick(delta=datetime.timedelta(minutes=28))
        runner.invoke(cli, ["stop"])

        frozen_datetime.tick(delta=datetime.timedelta(hours=14))

        # Time to check the log
        log_result = runner.invoke(cli, ["log"])

        expected_log_output = """Session Log
Yesterday
  4:35AM - 11:08AM		6h33m		Client A
  11:23AM - 11:51AM		28m		TIL

Sunday, March 15
  7:05AM - 11:37AM		4h32m		still
  12:05PM - 3:08PM		3h3m		TIL

Saturday, March 14
  10:05AM - 6:05PM		8h		TIL
"""

        log_output_by_line = log_result.output.split('\n')
        for i, expected_line in enumerate(expected_log_output.split('\n')):
            actual_line = log_output_by_line[i]
            assert actual_line == expected_line
