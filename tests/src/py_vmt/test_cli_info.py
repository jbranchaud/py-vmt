import json
import textwrap
from pathlib import Path

import pytest
from conftest import BetterCliRunner

from py_vmt.cli import VMT_VERSION, CliContext, ConfigFile, cli


@pytest.fixture
def config_dir(tmp_path: Path, monkeypatch) -> Path:
    config_dir: Path = tmp_path / "config"
    config_dir.mkdir()
    monkeypatch.setattr(ConfigFile, "_get_config_dir", staticmethod(lambda: config_dir))

    return config_dir


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch) -> Path:
    data_dir: Path = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(CliContext, "get_data_dir", staticmethod(lambda: data_dir))

    return data_dir


def test_info(config_dir: Path, data_dir: Path):
    config_file = config_dir / ConfigFile.FILENAME
    config_file.write_text(json.dumps({}))

    runner = BetterCliRunner()

    info_result = runner.invoke(cli, ["info"])
    output = textwrap.dedent(f"""
    config_file : {config_file}
    data_dir : {data_dir}
    version : {VMT_VERSION}
    schema_version : 1
    """).strip()
    assert output in info_result.output


def test_info_as_json(config_dir: Path, data_dir: Path):
    config_file = config_dir / ConfigFile.FILENAME
    config_file.write_text(json.dumps({}))

    runner = BetterCliRunner()

    info_result = runner.invoke(cli, ["info", "--json"])
    output = textwrap.dedent(f"""
    {{
      "config_file": "{config_file}",
      "data_dir": "{data_dir}",
      "version": "{VMT_VERSION}",
      "schema_version": 1
    }}
    """).strip()
    assert output in info_result.output
