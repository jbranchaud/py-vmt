import copy
from datetime import datetime, timezone
import json
from pathlib import Path
from platformdirs import user_data_dir, user_config_dir
import click
from typing import Optional
from py_vmt import time_helpers


class CliContext:
    def __init__(self, verbose: bool) -> None:
        self.verbose: bool = verbose
        self.data_dir: Path = CliContext.get_data_dir()
        self.config_dir: Path = CliContext.get_config_dir()
        self.active_session_file: Path = self.data_dir / "active_session.json"
        self.session_log_file: Path = self.data_dir / "session_log.json"
        self.active_session: dict | None = None
        self.load_active_session()

    @staticmethod
    def get_data_dir() -> Path:
        path = Path(user_data_dir("vmt"))
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def get_config_dir() -> Path:
        path = Path(user_config_dir("vmt"))
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def hydrate_session_data(data: dict) -> dict:
        data["start_time"] = datetime.fromisoformat(data["start_time"])
        return data

    @staticmethod
    def marshal_session_data(data: dict) -> dict:
        marshalled_data = copy.copy(data)

        CliContext.marshal_datetime_field("start_time", marshalled_data)
        CliContext.marshal_datetime_field("end_time", marshalled_data)

        return marshalled_data

    @staticmethod
    def marshal_datetime_field(field_name: str, data: dict) -> dict:
        if isinstance(data[field_name], datetime):
            data[field_name] = datetime.isoformat(data[field_name])

        return data

    def load_active_session(self) -> None:
        if self.active_session_file.exists():
            # TODO: good place to use Pydantic eventually
            session_data = json.loads(self.active_session_file.read_text()) or {}
            if "project_name" in session_data:
                self.active_session = CliContext.hydrate_session_data(session_data)

    def start_active_session(self, project_name: str, start_time: datetime) -> None:
        self.active_session_file.write_text(
            json.dumps(
                {"project_name": project_name, "start_time": start_time.isoformat()}
            )
        )

    # TODO: add explicit typing for the return type
    def stop_active_session(self, at: datetime) -> dict:
        assert (
            self.active_session
        ), "An active session is required in order to stop an active session"

        session = {"end_time": at, **self.active_session}

        # log current session to "database"
        self._write_event_to_session_log(session)

        # clear out active session file
        self._wipe_active_session_file()

        return session

    def cancel_active_session(self) -> dict:
        assert (
            self.active_session
        ), "An active session is required in order to cancel an active session"

        session = copy.copy(self.active_session)
        session["end_time"] = datetime.now(timezone.utc)

        self._wipe_active_session_file()

        return session

    def _wipe_active_session_file(self) -> None:
        empty_json = "{}"
        self.active_session_file.write_text(empty_json)
        self.active_session = None

    def _write_event_to_session_log(self, session) -> None:
        existing_sessions = self._load_session_log()

        writeable_session = CliContext.marshal_session_data(session)
        existing_sessions.append(writeable_session)

        self.session_log_file.write_text(json.dumps(existing_sessions))

    def _load_session_log(self) -> list:
        if self.session_log_file.exists():
            return json.loads(self.session_log_file.read_text())

        return []


# define top-level CLI group
@click.group()
@click.option(
    "--verbose",
    "-v",
    help="See extra output when running commands",
    is_flag=True,
)
@click.pass_context
def cli(ctx, verbose: bool):
    ctx.ensure_object(dict)
    ctx.obj = CliContext(verbose)

    if ctx.obj.verbose:
        click.echo("[ running `vmt` in verbose mode ]")


# define `start` subcommand
@cli.command()
@click.argument("project-name")
@click.option("--at", help='Hours previous to start the timer, e.g. "2 hours ago"')
@click.pass_context
# TODO: How can I add type annotations to `ctx` so that I get IDE type hints?
def start(ctx, project_name: str, at: Optional[str] = None) -> None:
    if ctx.obj.verbose:
        msg = f"[ start cmd ctx - data_dir: {ctx.obj.data_dir}, config_dir: {ctx.obj.config_dir} ]"
        click.echo(msg)

    if ctx.obj.active_session:
        msg = f"Error: already tracking '{ctx.obj.active_session['project_name']}'. Stop the current session first."
        click.echo(msg)
        ctx.abort()

    if at:
        start_at = time_helpers.parse_to_datetime(at)

    # TODO: abort if `start_at` isn't earlier than now

    start_time = start_at or datetime.now(timezone.utc)
    formatted_start_time = time_helpers.format_timestamp(start_time)

    # • Started tracking 'visual-mode-tracking' [cli] at 11:11 AM
    click.echo(f"• Started tracking '{project_name}' at {formatted_start_time}")

    # TODO: Add support for actually using the `--at` flag
    if at and ctx.obj.verbose:
        click.echo(f"  [ with flag --at of '{at}' ]")

    ctx.obj.start_active_session(
        project_name,
        start_time,
    )


# define `status` subcommand
@cli.command()
@click.pass_context
def status(ctx) -> None:
    sesh = ctx.obj.active_session
    if sesh and "project_name" in sesh:
        curr_time = datetime.now(timezone.utc)
        time_diff = curr_time - sesh["start_time"]
        elapsed_time = time_helpers.format_time_delta(time_diff)
        started_at = time_helpers.format_timestamp(sesh["start_time"])

        msg = f"• Tracking '{sesh['project_name']}' for {elapsed_time} (since {started_at})"
        click.echo(msg)
    else:
        # • Not tracking
        # Last: 'ccstorage' (8h 45m) at 8:37 AM
        click.echo("• Not tracking")
        # TODO: add support for listing last active session


# define `stop` subcommand
@cli.command()
@click.option("--at", help='Hours previous to end the timer, e.g. "2 hours ago"')
@click.pass_context
def stop(ctx, at: Optional[str] = None):
    if not ctx.obj.active_session:
        msg = "Error: No active session being tracked. Start a session first."
        click.echo(msg)
        ctx.abort()

    # TODO: add support for `--at` flag option using
    # `time_helpers.parse_to_datetime`
    # And then ensure that the time value is greater than
    # `latest_sesh['start_time']`

    stopped_at = datetime.now(timezone.utc)
    latest_sesh = ctx.obj.stop_active_session(stopped_at)

    # TODO: move this to a `session` dataclass method
    duration = latest_sesh["end_time"] - latest_sesh["start_time"]
    elapsed_time = time_helpers.format_time_delta(duration)

    click.echo(f"• Stopped tracking '{latest_sesh['project_name']}' ({elapsed_time})")


# define `cancel` subcommand
@cli.command()
@click.pass_context
def cancel(ctx):
    if not ctx.obj.active_session:
        msg = "Error: No active session to be cancelled."
        click.echo(msg)
        ctx.abort()

    cancelled_sesh = ctx.obj.cancel_active_session()
    project_name = cancelled_sesh["project_name"]
    duration = cancelled_sesh["end_time"] - cancelled_sesh["start_time"]
    elapsed_time = time_helpers.format_time_delta(duration)
    click.echo(f"• Cancelled session for '{project_name}' ({elapsed_time})")
