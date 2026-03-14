from click.testing import CliRunner
import datetime
from freezegun import freeze_time
import pytest
from py_vmt.cli import cli, CliContext


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
        output = "Stopped tracking 'my-project' (90m)"
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
            cli, ["start", "my-project", "--at", '"33 minutes ago"']
        )
        output = "Started tracking 'my-project' at 9:32AM"
        assert output in start_result.output

        frozen_datetime.tick(delta=datetime.timedelta(minutes=30))

        # check status
        status_result = runner.invoke(cli, ["status"])
        output = "Tracking 'my-project' for 63m (since 9:32AM)"
        assert output in status_result.output
