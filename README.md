# VisualMode Tracker, built with Python

## Development

Run the CLI in development with `uv`:

```bash
❯ uv run vmt start taco --at "1 hour ago"
• Started tracking 'taco' at 12:56PM
  with flag --at of '1 hour ago'

❯ uv run vmt status
• Tracking 'taco' for 3m

❯ uv run vmt start burrito
Error: already tracking 'taco'. Stop the current session first.
Aborted!
```

## Testing

The test suite uses `pytest` and `click`'s `CliRunner` to verify the behavior of
the `vmt` CLI.

Run the tests like so:

```bash
❯ uv run pytest
```
