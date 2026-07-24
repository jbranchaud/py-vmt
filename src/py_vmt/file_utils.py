from contextlib import contextmanager
from pathlib import Path
import os
import tempfile


@contextmanager
def atomic_write(path: Path):
    # write to a tmp file in the same directory, then atomically swap it
    fd, temp_file_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as file:
            yield file
        os.replace(temp_file_path, path)
    except BaseException:
        os.unlink(temp_file_path)
        raise
