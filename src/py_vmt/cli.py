from datetime import datetime, timezone
import json
from pathlib import Path
from platformdirs import user_data_dir, user_config_dir
import click
from typing import Optional
import math


class CliContext:
    def __init__(self) -> None:
        self.data_dir: Path = CliContext.get_data_dir()
        self.config_dir: Path = CliContext.get_config_dir()
        self.active_session_file: Path = self.data_dir / "active_session.json"
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


# define top-level CLI group
@click.group()
@click.pass_context
def cli(ctx):
    ctx.ensure_object(dict)
    ctx.obj = CliContext()


# define `start` subcommand
@cli.command()
@click.argument("project-name")
@click.option("--at", help='Hours previous to start the timer, e.g. "2 hours ago"')
@click.pass_context
# TODO: How can I add type annotations to `ctx` so that I get IDE type hints?
def start(ctx, project_name: str, at: Optional[str] = None) -> None:
    msg = f"start cmd ctx - data_dir: {ctx.obj.data_dir}, config_dir: {ctx.obj.config_dir}"
    click.echo(msg)

    if ctx.obj.active_session:
        msg = f"Error: already tracking '{ctx.obj.active_session['project_name']}. Stop the current session first."
        click.echo(msg)
        ctx.abort()

    start_time = datetime.now(timezone.utc)
    # Make sure to convert to local time (with `astimezone()`) before printing
    # to stdout.
    formatted_start_time = start_time.astimezone().strftime("%-I:%M%p")

    # • Started tracking 'visual-mode-tracking' [cli] at 11:11 AM
    click.echo(f"• Started tracking '{project_name}' at {formatted_start_time}")

    # TODO: Add support for actually using the `--at` flag
    if at:
        click.echo(f"  with flag --at of '{at}'")

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
        elapsed_time = format_time_delta(time_diff)
        click.echo(f"• Tracking '{sesh['project_name']}' for {elapsed_time}")
    else:
        # • Not tracking
        # Last: 'ccstorage' (8h 45m) at 8:37 AM
        click.echo("• Not tracking")
        # TODO: add support for listing last active session


# define `stop` subcommand
@cli.command()
@click.option("--at", help='Hours previous to end the timer, e.g. "2 hours ago"')
def stop(at: Optional[str] = None):
    click.echo("Stopping the timer for the current project")


def format_time_delta(diff) -> str:
    if diff.seconds < 60:
        return f"{diff.seconds}s"

    minutes = math.floor(diff.seconds / 60)
    return f"{minutes}m"
