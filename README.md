# VisualMode Tracker, built with Python

> A command-line time tracker for your project and work sessions

## Usage

Standard usage of `vmt` is to `start` a session by name (e.g. `py-vmt`) with
zero or more tags (e.g. `+python`) while you work. You can always check the
`status`. When you are done with a session, you can `stop` it. Check the `log`
to see what sessions you have tracked over the last 7 days.

```bash
❯ vmt start py-vmt +python --at "14 minutes ago"
• Started tracking 'py-vmt' [python] at 12:00PM

❯ vmt status
• Tracking 'py-vmt' [python] for 27m20s (since 12:00PM)

❯ vmt stop --round
• Stopped tracking 'py-vmt' [python] (30m)

❯ vmt log
Session Log
Sunday, August 02
  12:00PM - 12:30PM		30m		'py-vmt' [python]

❯ vmt status
• Not tracking
Last: 'py-vmt' [python] (30m) at 12:00PM
```

## Installation

`vmt` (`visualmode-tracker`) can be installed via `uv` and `pipx`:

```bash
❯ uv tool install visualmode-tracker
```

```bash
❯ pipx install visualmode-tracker
```

Note: that while the package name on PyPI is `visualmode-tracker`, the
executable binary is called via `vmt`.

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
