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
