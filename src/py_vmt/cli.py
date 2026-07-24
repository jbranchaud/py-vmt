import collections
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from sqlite3 import Connection
import sqlite3
from typing import Protocol
from platformdirs import user_data_dir, user_config_dir
import click
from py_vmt import time_helpers
from py_vmt.session import Session
from py_vmt.file_utils import atomic_write
from py_vmt import db


type DateToSessionDict = collections.defaultdict[date, list[Session]]


class SessionRepository(Protocol):
    def active_session(self) -> Session | None: ...
    def write_active_session(self, session) -> None: ...
    def append_session(self, session) -> None: ...
    def all_sessions(self) -> list[Session]: ...
    def clear_active_session(self) -> None: ...


class SqliteRepository:
    def __init__(self, *, data_dir: Path) -> None:
        self.db_file: Path = data_dir / "sessions.db"
        self.conn: Connection = sqlite3.connect(self.db_file)

        # always migrate the DB as part of initialization, this will mostly be a no-op
        db.migrate(self.conn)

    def active_session(self) -> Session | None:
        cursor = self.conn.cursor()
        fetch_active_session_sql = """
            select sessions.id, sessions.active, projects.name as project_name, sessions.start_time, sessions.end_time
            from sessions
            join projects on sessions.project_id = projects.id
            where sessions.active = 1;
        """
        result = cursor.execute(fetch_active_session_sql)
        raw_active_session = result.fetchone()
        if raw_active_session is None:
            return None
        _id, _active, project_name, start_time, end_time = raw_active_session
        data = {
            "project_name": project_name,
            "start_time": start_time,
            "end_time": end_time,
        }
        return Session.hydrate(data)

    def write_active_session(self, session: Session) -> None:
        self.write_session_with_project(session, active=True)

    def append_session(self, session: Session) -> None:
        self.write_session_with_project(session, active=False)

    def all_sessions(self) -> list[Session]:
        fetch_all_sessions_sql = """
            select sessions.id, sessions.active, projects.name as project_name, sessions.start_time, sessions.end_time
            from sessions
            join projects on sessions.project_id = projects.id;
        """
        cursor = self.conn.execute(fetch_all_sessions_sql)
        results = cursor.fetchall()
        if results is None:
            return []

        sessions = []
        for raw_session in results:
            _id, _active, project_name, start_time, end_time = raw_session
            data = {
                "project_name": project_name,
                "start_time": start_time,
                "end_time": end_time,
            }
            sessions.append(Session.hydrate(data))

        return sessions

    def clear_active_session(self) -> None:
        # Delete the current active session if there is one
        self.conn.execute("""
            delete from sessions where active = 1;
        """)
        self.conn.commit()

    def write_session_with_project(self, session, *, active=False) -> None:
        with self.conn:
            if active:
                # Delete the current active session if there is one
                self.conn.execute("""
                    delete from sessions where active = 1;
                """)

            # Upsert (find or create) the project based on `session.project_name`
            cursor = self.conn.execute(
                """
                insert into projects (name) values (:project_name)
                on conflict (name) do update set name = excluded.name
                returning id;
            """,
                {"project_name": session.project_name},
            )
            project_id = cursor.fetchone()[0]

            # Prepare `sessions` insert payload
            session_data = {
                "active": 1 if active else 0,
                "project_id": project_id,
                "start_time": datetime.isoformat(session.start_time),
                "end_time": None,
            }

            if session.end_time:
                session_data["end_time"] = datetime.isoformat(session.end_time)

            # Insert the new active session
            self.conn.execute(
                """
                insert into sessions (active, project_id, start_time, end_time)
                values (:active, :project_id, :start_time, :end_time);
            """,
                session_data,
            )


class JsonRepository:
    def __init__(self, *, data_dir: Path) -> None:
        self.active_session_file: Path = data_dir / "active_session.json"
        self.session_log_file: Path = data_dir / "session_log.json"

    def active_session(self) -> Session | None:
        if self.active_session_file.exists():
            # TODO: good place to use Pydantic eventually
            session_data = json.loads(self.active_session_file.read_text()) or {}
            if "project_name" in session_data:
                return Session.hydrate(session_data)

        return None

    def write_active_session(self, session: Session) -> None:
        with atomic_write(self.active_session_file) as file:
            json.dump(session.marshal(), file)

    def append_session(self, session: Session) -> None:
        existing_sessions = self.load_raw_session_log()

        writeable_session = session.marshal()
        existing_sessions.append(writeable_session)

        with atomic_write(self.session_log_file) as file:
            json.dump(existing_sessions, file)

    def load_raw_session_log(self) -> list[dict]:
        if self.session_log_file.exists():
            return json.loads(self.session_log_file.read_text())

        return []

    def all_sessions(self) -> list[Session]:
        return [Session.hydrate(raw_sesh) for raw_sesh in self.load_raw_session_log()]

    def clear_active_session(self) -> None:
        with atomic_write(self.active_session_file) as file:
            json.dump({}, file)


class CliContext:
    def __init__(self, *, verbose: bool) -> None:
        self.verbose: bool = verbose
        self.data_dir: Path = CliContext.get_data_dir()
        self.config = self.read_config()
        self.active_session: Session | None = None
        self.repo = self._initialize_configured_repo(data_dir=self.data_dir)
        self.active_session = self.repo.active_session()

    def start_active_session(self, project_name: str, start_time: datetime) -> None:
        new_session = Session(start_time, project_name)
        self.repo.write_active_session(new_session)

    def stop_active_session(self, at: datetime, round: bool = False) -> Session:
        assert self.active_session, (
            "An active session is required in order to stop an active session"
        )

        session = self.active_session
        session.stop(at, round)

        # log current session to "database"
        self.repo.append_session(session)

        # clear out active session file
        self.repo.clear_active_session()

        # clear active session state
        self.active_session = None

        return session

    def cancel_active_session(self) -> Session:
        assert self.active_session, (
            "An active session is required in order to cancel an active session"
        )

        session = self.active_session
        session.stop()

        # clear out active session file
        self.repo.clear_active_session()

        # clear active session state
        self.active_session = None

        return session

    def load_latest_sessions(self) -> DateToSessionDict:
        existing_sessions = self.repo.all_sessions()

        days_ago_list = [timedelta(days=neg_index) for neg_index in range(0, -7, -1)]
        last_seven_days = [
            (datetime.now() + days_ago).date() for days_ago in days_ago_list
        ]
        sessions_grouped_by_day: DateToSessionDict = collections.defaultdict(list)

        for previous_date in last_seven_days:
            sessions_for_date = [
                sesh
                for sesh in existing_sessions
                if sesh.start_time.date() == previous_date
            ]

            if sessions_for_date:
                sessions_for_date.sort()
                sessions_grouped_by_day[previous_date] = sessions_for_date

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

    def load_most_recent_session(self) -> Session | None:
        sessions_by_date = self.load_latest_sessions()

        if not sessions_by_date:
            return None

        latest_date = next(iter(sessions_by_date))
        if latest_date:
            sessions = sessions_by_date[latest_date]

            if sessions:
                return sessions[-1]

        return None

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
    def read_config() -> dict:
        config_dir: Path = CliContext.get_config_dir()
        config_file: Path = config_dir / "config.json"

        if config_file.exists():
            return json.loads(config_file.read_text())

        return {}

    _REPOS: dict[str, type[SessionRepository]] = {
        "json": JsonRepository,
        "sqlite": SqliteRepository,
    }

    def _initialize_configured_repo(self, **config) -> SessionRepository:
        default_format = "sqlite"
        format = self.config.get("storage_format", default_format)
        try:
            return self._REPOS[format](**config)
        except KeyError:
            raise ValueError(f"Unknown storage_format: {format!r}")


# This decorator allows for passing the `CliContext` object
# directly to each command handler
pass_cli = click.make_pass_decorator(CliContext)


# define top-level CLI group
@click.group(name="vmt")
@click.option(
    "--verbose",
    "-v",
    help="See extra output when running commands",
    is_flag=True,
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool):
    ctx.ensure_object(dict)
    ctx.obj = CliContext(verbose=verbose)

    if ctx.obj.verbose:
        click.echo("[ running `vmt` in verbose mode ]")


def validate_start_at(_ctx, _param, value: str | None) -> datetime:
    now = datetime.now(timezone.utc)

    if value is None:
        return now

    past_time = time_helpers.parse_to_datetime(value)

    if past_time is None or past_time > now:
        raise click.BadParameter("must be a relative time in the past")

    return past_time


# define `start` subcommand
@cli.command()
@click.argument("project-name")
@click.option(
    "--at",
    help='Relative time in past to start the time, e.g. "2 hours ago", "33 minutes ago"',
    callback=validate_start_at,
)
@pass_cli
def start(cli_ctx: CliContext, project_name: str, at: datetime) -> None:
    if cli_ctx.active_session:
        msg = f"Error: already tracking '{cli_ctx.active_session.project_name}'. Stop the current session first."
        click.echo(msg)
        click.get_current_context().abort()

    formatted_start_time = time_helpers.format_timestamp(at)

    # • Started tracking 'visual-mode-tracking' [cli] at 11:11 AM
    click.echo(f"• Started tracking '{project_name}' at {formatted_start_time}")

    cli_ctx.start_active_session(
        project_name,
        at,
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

        msg = (
            f"• Tracking '{sesh.project_name}' for {elapsed_time} (since {started_at})"
        )
        click.echo(msg)
    else:
        # read in most recent session
        latest_sesh = cli_ctx.load_most_recent_session()

        # • Not tracking
        # Last: 'my-project' (1h30m) at 8:37AM
        click.echo("• Not tracking")
        if latest_sesh:
            project_name = latest_sesh.project_name
            elapsed_time = time_helpers.format_time_delta(latest_sesh.duration())
            started_at = time_helpers.format_timestamp(latest_sesh.start_time)

            click.echo(f"Last: '{project_name}' ({elapsed_time}) at {started_at}")


def validate_stop_at(ctx, _param, value: str | None) -> datetime:
    now = datetime.now(timezone.utc)

    if value is None:
        return now

    past_time = time_helpers.parse_to_datetime(value)

    if past_time is None or past_time > now:
        raise click.BadParameter("must be a relative time in the past")

    if past_time < ctx.obj.active_session.start_time:
        raise click.BadParameter("stop time must be after start time")

    return past_time


class RequireActiveSessionCommand(click.Command):
    def parse_args(self, ctx, args):
        if ctx.obj.active_session is None:
            raise click.UsageError(
                "No active session being tracked. Start a session first."
            )

        return super().parse_args(ctx, args)


# define `stop` subcommand
@cli.command(cls=RequireActiveSessionCommand)
@click.option(
    "--at",
    help='Hours previous to end the timer, e.g. "2 hours ago"',
    callback=validate_stop_at,
)
@click.option(
    "--round",
    help="Round the stop time to the nearest 15 minute interval",
    is_flag=True,
)
@pass_cli
def stop(cli_ctx: CliContext, at: datetime, round: bool) -> None:
    stopped_at = at
    latest_sesh = cli_ctx.stop_active_session(stopped_at, round)

    assert latest_sesh.end_time, "Expected this session to have an 'end_time' set"

    elapsed_time = time_helpers.format_time_delta(latest_sesh.duration())

    click.echo(f"• Stopped tracking '{latest_sesh.project_name}' ({elapsed_time})")


# define `cancel` subcommand
@cli.command(cls=RequireActiveSessionCommand)
@pass_cli
def cancel(cli_ctx: CliContext):
    cancelled_sesh = cli_ctx.cancel_active_session()
    project_name = cancelled_sesh.project_name

    assert cancelled_sesh.end_time, "Expected this session to have an 'end_time' set"

    elapsed_time = time_helpers.format_time_delta(cancelled_sesh.duration())
    click.echo(f"• Cancelled session for '{project_name}' ({elapsed_time})")


# define `log` subcommand
@cli.command()
@pass_cli
def log(cli_ctx: CliContext):
    # read in the session log file if it exists
    sessions = cli_ctx.load_latest_sessions()

    # make sure to also display the active session if there is one
    active_session = cli_ctx.active_session

    click.echo("Session Log")

    if active_session:
        # Assume, for now, that an active session is always 'today'
        # Later I'll have to account for a session that started the
        # previous day.
        start_time = time_helpers.format_timestamp(active_session.start_time)

        duration = time_helpers.format_time_delta(active_session.duration())

        project_name = active_session.project_name

        click.echo(f"  {start_time} - ...\t\t{duration}\t\t{project_name}")

    yesterday = (datetime.now() - timedelta(days=1)).date()
    for session_date, sessions_for_day in sessions.items():
        date_display = session_date.strftime("%A, %B %d")
        if session_date == yesterday:
            date_display = "Yesterday"

        click.echo(f"{date_display}")
        for session in sessions_for_day:
            if session.end_time is None:
                continue

            start_time = time_helpers.format_timestamp(session.start_time)
            end_time = time_helpers.format_timestamp(session.end_time)

            elapsed_time = time_helpers.format_time_delta(session.duration())

            project_name = session.project_name

            click.echo(
                f"  {start_time} - {end_time}\t\t{elapsed_time}\t\t{project_name}"
            )

        click.echo("")
