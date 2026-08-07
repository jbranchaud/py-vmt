from py_vmt.cli import StorageFormat, CliContext


def test_storage_formats_match_repo_registry():
    assert sorted(list(CliContext._REPOS)) == sorted(list(StorageFormat))
