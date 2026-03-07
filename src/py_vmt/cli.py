from pathlib import Path
from platformdirs import user_data_dir, user_config_dir
import click
from typing import Optional


class CliContext:
    def __init__(self) -> None:
        self.data_dir: Path = CliContext.get_data_dir()
        self.config_dir: Path = CliContext.get_config_dir()

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


# define top-level CLI group
@click.group()
@click.pass_context
def cli(ctx):
    ctx.ensure_object(dict)
    ctx.obj = CliContext()


@cli.command()
@click.argument("project-name")
@click.option("--at", help='Hours previous to start the timer, e.g. "2 hours ago"')
@click.pass_context
def start(ctx, project_name: str, at: Optional[str] = None):
    print(
        f"start cmd ctx - data_dir: {ctx.obj.data_dir}, config_dir: {ctx.obj.config_dir}"
    )
    print(f"Starting a time for project {project_name}")
    if at:
        print(f"  with flag --at of '{at}'")


@cli.command()
@click.option("--at", help='Hours previous to end the timer, e.g. "2 hours ago"')
def stop(at: Optional[str] = None):
    print("Stopping the timer for the current project")
