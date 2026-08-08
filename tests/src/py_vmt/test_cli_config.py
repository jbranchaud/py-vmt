import textwrap

from conftest import BetterCliRunner

from py_vmt.cli import ConfigFile, cli, CliContext

import pytest


@pytest.fixture(autouse=True)
def use_tmp_platform_dirs(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # override the `config.json` a little
    # (config_dir / "config.json").write_text(
    #     json.dumps({"storage_format": storage_format})
    # )

    monkeypatch.setattr(ConfigFile, "_get_config_dir", staticmethod(lambda: config_dir))


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
