import json
from pathlib import Path
import textwrap

from conftest import BetterCliRunner

from py_vmt.cli import ConfigFile, cli, CliContext

import pytest


@pytest.fixture(autouse=True)
def config_dir(tmp_path: Path, monkeypatch) -> Path:
    config_dir: Path = tmp_path / "config"
    config_dir.mkdir()
    monkeypatch.setattr(ConfigFile, "_get_config_dir", staticmethod(lambda: config_dir))

    return config_dir


def test_config_path(config_dir: Path):
    config_file = config_dir / ConfigFile.FILENAME
    config_file.write_text(json.dumps({"storage_format": "json"}))

    runner = BetterCliRunner()

    config_result = runner.invoke(cli, ["config", "--path"])
    output = f"{config_file}"
    assert output in config_result.output
    assert config_result.exit_code == 0


def test_config_path_no_config_file():
    runner = BetterCliRunner()

    config_result = runner.invoke(cli, ["config", "--path"])
    output = "vmt: no config file found\n"
    assert output == config_result.output
    assert config_result.exit_code == 1


def test_config_init():
    runner = BetterCliRunner()

    config_result = runner.invoke(cli, ["config", "--init"])
    output = textwrap.dedent(f"""\
        A base config file has been initialized with minimal defaults.
        Location: {CliContext(verbose=False).config_file.location()}
    """)
    assert output in config_result.output


def test_config_with_no_flag():
    runner = BetterCliRunner()

    config_result = runner.invoke(cli, ["config"])
    output = "The config subcommand only suppports the `--init` flag at this time\n"
    assert output == config_result.output
