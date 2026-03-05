import click
from typing import Optional


# define top-level CLI group
@click.group()
def cli():
    pass


@cli.command()
@click.argument("project-name")
@click.option("--at", help='Hours previous to start the timer, e.g. "2 hours ago"')
def start(project_name: str, at: Optional[str] = None):
    print(f"Starting a time for project {project_name}")
    if at:
        print(f"  with flag --at of '{at}'")


@cli.command()
@click.option("--at", help='Hours previous to end the timer, e.g. "2 hours ago"')
def stop(at: Optional[str] = None):
    print("Stopping the timer for the current project")
