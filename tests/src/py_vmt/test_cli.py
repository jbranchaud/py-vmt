from click.testing import CliRunner
from py_vmt.cli import cli


def test_no_status():
    runner = CliRunner()
    result = runner.invoke(cli, ["status"])
    assert "Not tracking" in result.output


def test_active_status():
    runner = CliRunner()

    # start a session
    start_result = runner.invoke(cli, ["start", "my-project"])
    assert "Started tracking 'my-project'" in start_result.output

    # check status
    status_result = runner.invoke(cli, ["status"])
    assert "Tracking 'my-project'" in status_result.output

    # stop a session
    stop_result = runner.invoke(cli, ["stop"])
    assert "Stopped tracking 'my-project'" in stop_result.output
