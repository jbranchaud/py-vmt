from click.testing import CliRunner
import datetime
from freezegun import freeze_time
from py_vmt.cli import cli


def test_no_status():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["status"])
        assert "Not tracking" in result.output


def test_active_status():
    runner = CliRunner()

    with runner.isolated_filesystem():
        initial_datetime = datetime.datetime(
            2026, 3, 14, 15, 5, 11, 0, datetime.timezone.utc
        )
        with freeze_time(initial_datetime) as frozen_datetime:
            # start a session
            start_result = runner.invoke(cli, ["start", "my-project"])
            output = "Started tracking 'my-project' at 10:05AM"
            assert output in start_result.output

            # check status
            status_result = runner.invoke(cli, ["status"])
            assert "Tracking 'my-project'" in status_result.output

            # stop a session
            stop_result = runner.invoke(cli, ["stop"])
            assert "Stopped tracking 'my-project'" in stop_result.output
