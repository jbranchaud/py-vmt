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

`vmt` (`visualmode-tracker`) requires Python 3.14+ and can be installed via
`uv` and `pipx`:

```bash
❯ uv tool install visualmode-tracker
```

`uv` downloads Python 3.14 if you don't already have it. `pipx` uses the Python
it runs on, so point it at 3.14 if that isn't your default:

```bash
❯ pipx install --python python3.14 visualmode-tracker
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

## Releasing

This project follows [Semantic Versioning](https://semver.org/) and keeps a
[`CHANGELOG.md`](CHANGELOG.md) in the
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format. The CLI
surface (commands, flags, output format, exit codes, config/data locations, and
supported Python versions) is the public API.

While on `0.x`, bump the **minor** version for new features or breaking changes
and the **patch** version for bug fixes only.

Every PR adds a user-facing entry under `## [Unreleased]` in `CHANGELOG.md`.
Feature PRs don't change the version.

To cut a release, run the `release` task from an up-to-date `main`:

```bash
❯ mise run release minor --dry-run  # check and preview, changes nothing
❯ mise run release minor            # or patch / major
```

It checks that `main` is clean and matches `origin/main`, that CI is green and
that `[Unreleased]` has entries. After you confirm, it:

1. bumps the version and rolls `[Unreleased]` into a dated `[X.Y.Z]` section in
   `CHANGELOG.md`,
2. builds the package and smoke tests the wheel,
3. commits `Release vX.Y.Z` and creates the annotated tag (rolling back locally
   if any of this fails),
4. pushes `main` and the tag together, which triggers the `release` workflow to
   publish to PyPI via Trusted Publishing,
5. waits for that workflow, then creates the GitHub Release from the changelog
   notes.

If the workflow fails before anything reaches PyPI, fix it, re-run the workflow,
and finish with `mise run release --resume vX.Y.Z`. If a version did reach PyPI,
never reuse it: fix the problem and release a new patch version.
