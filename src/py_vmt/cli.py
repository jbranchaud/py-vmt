import collections
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from platformdirs import user_data_dir, user_config_dir
import click
from typing import Optional
from py_vmt import time_helpers
from py_vmt.session import Session
from dataclasses import dataclass


class CliContext:
    def __init__(self, verbose: bool) -> None:
        self.verbose: bool = verbose
        self.data_dir: Path = CliContext.get_data_dir()
        self.config_dir: Path = CliContext.get_config_dir()
        self.active_session_file: Path = self.data_dir / "active_session.json"
        self.session_log_file: Path = self.data_dir / "session_log.json"
        self.active_session: Session | None = None
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

    def load_active_session(self) -> None:
        if self.active_session_file.exists():
            # TODO: good place to use Pydantic eventually
            session_data = json.loads(self.active_session_file.read_text()) or {}
            if "project_name" in session_data:
                self.active_session = Session.hydrate(session_data)
                # CliContext.hydrate_session_data(session_data)

    def start_active_session(self, project_name: str, start_time: datetime) -> None:
        new_session = Session(start_time, project_name)
        self.active_session_file.write_text(json.dumps(new_session.marshal()))

    def stop_active_session(self, at: datetime) -> Session:
        assert (
            self.active_session
        ), "An active session is required in order to stop an active session"

        session = self.active_session
        session.stop()

        # log current session to "database"
        self._write_event_to_session_log(session)

        # clear out active session file
        self._wipe_active_session_file()

        return session

    def cancel_active_session(self) -> Session:
        assert (
            self.active_session
        ), "An active session is required in order to cancel an active session"

        session = self.active_session
        session.stop()

        self._wipe_active_session_file()

        return session

    type DateToSessionDict = collections.defaultdict[date, list[Session]]

    def load_latest_sessions(self) -> DateToSessionDict:
        existing_sessions = self._load_session_log()

        days_ago_list = [timedelta(days=neg_index) for neg_index in range(0, -7, -1)]
        last_seven_days = [(datetime.now() + days_ago).date() for days_ago in days_ago_list]
        sessions_grouped_by_day: DateToSessionDict = collections.defaultdict(list)

        for date in last_seven_days:
            sessions_for_date = [sesh for sesh in existing_sessions if sesh.start_time.date() == date]

            if sessions_for_date:
                sessions_for_date.sort()
                sessions_grouped_by_day[date] = sessions_for_date

        return sessions_grouped_by_day
        # find all sessions in the last 7 days
        #
        # Note: we care about local time, not UTC
        #
        # If we are aggregating the sessions by day, where does a session that
        # spans two days go?
        # Probably it goes in the day it started in.
        # If I have a session that starts at 11pm and goes until 2am.
        # I suppose that is a late night session, so it should be attributed to
        # that day.
        # And then anything after midnight we can treat as part of the next day.
        # for sesh in existing_sessions:
        #     sesh["start_time"]

    def _wipe_active_session_file(self) -> None:
        empty_json = "{}"
        self.active_session_file.write_text(empty_json)
        self.active_session = None

    def _write_event_to_session_log(self, session: Session) -> None:
        existing_sessions = self._load_raw_session_log()

        writeable_session = session.marshal()
        existing_sessions.append(writeable_session)

        self.session_log_file.write_text(json.dumps(existing_sessions))

    def _load_raw_session_log(self) -> list:
        if self.session_log_file.exists():
            return json.loads(self.session_log_file.read_text())

        return []

    def _load_session_log(self) -> list[Session]:
        return [Session.hydrate(raw_sesh) for raw_sesh in self._load_raw_session_log()]


# This decorator allows for passing the `CliContext` object
# directly to each command handler
pass_cli = click.make_pass_decorator(CliContext)

# define top-level CLI group
@click.group()
@click.option(
    "--verbose",
    "-v",
    help="See extra output when running commands",
    is_flag=True,
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool):
    ctx.ensure_object(dict)
    ctx.obj = CliContext(verbose)

    if ctx.obj.verbose:
        click.echo("[ running `vmt` in verbose mode ]")


# define `start` subcommand
@cli.command()
@click.argument("project-name")
@click.option("--at", help='Hours previous to start the timer, e.g. "2 hours ago"')
@pass_cli
def start(cli_ctx: CliContext, project_name: str, at: Optional[str] = None) -> None:
    if cli_ctx.verbose:
        msg = f"[ start cmd ctx - data_dir: {cli_ctx.data_dir}, config_dir: {cli_ctx.config_dir} ]"
        click.echo(msg)

    if cli_ctx.active_session:
        msg = f"Error: already tracking '{cli_ctx.active_session.project_name}'. Stop the current session first."
        click.echo(msg)
        click.get_current_context().abort()

    start_at = None
    if at:
        start_at = time_helpers.parse_to_datetime(at)

    # TODO: abort if `start_at` isn't earlier than now

    start_time = start_at or datetime.now(timezone.utc)
    formatted_start_time = time_helpers.format_timestamp(start_time)

    # • Started tracking 'visual-mode-tracking' [cli] at 11:11 AM
    click.echo(f"• Started tracking '{project_name}' at {formatted_start_time}")

    cli_ctx.start_active_session(
        project_name,
        start_time,
    )


# define `status` subcommand
@cli.command()
@pass_cli
def status(cli_ctx: CliContext) -> None:
    sesh = cli_ctx.active_session
    if sesh:
        curr_time = datetime.now(timezone.utc)
        time_diff = curr_time - sesh.start_time
        elapsed_time = time_helpers.format_time_delta(time_diff)
        started_at = time_helpers.format_timestamp(sesh.start_time)

        msg = f"• Tracking '{sesh.project_name}' for {elapsed_time} (since {started_at})"
        click.echo(msg)
    else:
        # • Not tracking
        # Last: 'ccstorage' (8h 45m) at 8:37 AM
        click.echo("• Not tracking")
        # TODO: add support for listing last active session


# define `stop` subcommand
@cli.command()
@click.option("--at", help='Hours previous to end the timer, e.g. "2 hours ago"')
@pass_cli
def stop(cli_ctx: CliContext, at: Optional[str] = None):
    if not cli_ctx.active_session:
        msg = "Error: No active session being tracked. Start a session first."
        click.echo(msg)
        click.get_current_context().abort()

    # TODO: add support for `--at` flag option using
    # `time_helpers.parse_to_datetime`
    # And then ensure that the time value is greater than
    # `latest_sesh['start_time']`

    stopped_at = datetime.now(timezone.utc)
    latest_sesh = cli_ctx.stop_active_session(stopped_at)

    assert latest_sesh.end_time, "Expected this session to have an 'end_time' set"

    # TODO: move this to a `session` dataclass method
    duration = latest_sesh.end_time - latest_sesh.start_time
    elapsed_time = time_helpers.format_time_delta(duration)

    click.echo(f"• Stopped tracking '{latest_sesh.project_name}' ({elapsed_time})")


# define `cancel` subcommand
@cli.command()
@pass_cli
def cancel(cli_ctx: CliContext):
    if not cli_ctx.active_session:
        msg = "Error: No active session to be cancelled."
        click.echo(msg)
        click.get_current_context().abort()

    cancelled_sesh = cli_ctx.cancel_active_session()
    project_name = cancelled_sesh.project_name

    assert cancelled_sesh.end_time, "Expected this session to have an 'end_time' set"

    duration = cancelled_sesh.end_time - cancelled_sesh.start_time
    elapsed_time = time_helpers.format_time_delta(duration)
    click.echo(f"• Cancelled session for '{project_name}' ({elapsed_time})")


# define `log` subcommand
@cli.command()
@pass_cli
def log(cli_ctx: CliContext):
    # read in the session log file if it exists
    sessions = cli_ctx.load_latest_sessions()

    # make sure to also display the active session if there is one
    active_session = cli_ctx.active_session

    # TODO: Change all of the `print` statements to `click.echo` calls
    print("Session Log")

    curr_time = datetime.now(timezone.utc)

    if active_session:
        # Assume, for now, that an active session is always 'today'
        # Later I'll have to account for a session that started the
        # previous day.
        start_time = time_helpers.format_timestamp(active_session.start_time)

        time_diff = curr_time - active_session.start_time
        duration = time_helpers.format_time_delta(time_diff)

        project_name = active_session.project_name

        print(f"  {start_time} - ...\t\t{duration}\t\t{project_name}")

    yesterday = (datetime.now() - timedelta(days=1)).date()
    for date, sessions_for_day in sessions.items():
        date_display = date.strftime("%A, %B %d")
        if date == yesterday:
            date_display = "Yesterday"

        print(f"{date_display}")
        for session in sessions_for_day:
            start_time = time_helpers.format_timestamp(session.start_time)
            end_time = "..."
            if session.end_time:
                end_time = time_helpers.format_timestamp(session.end_time)

            time_diff = (session.end_time or curr_time) - session.start_time
            duration = time_helpers.format_time_delta(time_diff)

            project_name = session.project_name

            print(f"  {start_time} - {end_time}\t\t{duration}\t\t{project_name}")

        print("")
