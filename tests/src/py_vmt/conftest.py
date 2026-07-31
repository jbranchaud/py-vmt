import os
import time
from click.testing import CliRunner


# Set the timezone that all tests run in
os.environ.setdefault("TZ", "America/Chicago")
time.tzset()


class BetterCliRunner(CliRunner):
    def invoke(self, *args, **kwargs):
        result = super().invoke(*args, **kwargs)
        if result.exception and not isinstance(result.exception, SystemExit):
            raise result.exception
        return result
