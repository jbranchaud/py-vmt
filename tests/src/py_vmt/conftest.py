from click.testing import CliRunner


class BetterCliRunner(CliRunner):
    def invoke(self, *args, **kwargs):
        result = super().invoke(*args, **kwargs)
        if result.exception and not isinstance(result.exception, SystemExit):
            raise result.exception
        return result
