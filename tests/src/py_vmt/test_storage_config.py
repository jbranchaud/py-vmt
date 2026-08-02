from py_vmt.cli import STORAGE_FORMATS, CliContext


def test_storage_formats_match_repo_registry():
    assert sorted(list(CliContext._REPOS)) == sorted(STORAGE_FORMATS)
