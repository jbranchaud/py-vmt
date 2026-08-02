import textwrap

from conftest import BetterCliRunner

from py_vmt.cli import cli


def test_base_help_message():
    runner = BetterCliRunner()

    help_result = runner.invoke(cli, ["--help"])
    output = textwrap.dedent("""\
        Usage: vmt [OPTIONS] COMMAND [ARGS]...

        Options:
          -v, --verbose  See extra output when running commands
          --version      Show the version and exit.
          --help         Show this message and exit.

        Commands:
          cancel
          log
          start
          status
          stop
    """)
    assert output in help_result.output


def test_start_help_message():
    runner = BetterCliRunner()

    help_result = runner.invoke(cli, ["start", "--help"])
    output = textwrap.dedent("""\
        Usage: vmt start [OPTIONS] PROJECT_NAME [+TAG]...

        Options:
          --at TEXT  Relative time in past to start the time, e.g. "2 hours ago", "33
                     minutes ago"
          --help     Show this message and exit.

        Tags:
          +TAG  Attach one or more tags, e.g. +meeting +engineering
    """)
    assert output in help_result.output
