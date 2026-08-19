# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `vmt config --init` to generate a config file with default settings, printing
  its location (and a notice if one already exists).
- `vmt config --path` to print the path to the config file.
- `vmt info` to show the config file path, data dir, and version (plus schema
  version when using sqlite storage), with a `--json` flag for JSON output.

### Changed

- Upgraded the project to Python 3.14 (now requires Python >= 3.14).
- Config file parsing now uses pydantic to validate settings, with a
  `StorageFormat` enum (`sqlite`, `json`) for the storage format.

## [0.1.0] - 2026-08-02

### Added

- `vmt start <name> [+tags]` to begin tracking a work session, with an optional
  `--at` flag to backdate the start time.
- `vmt status` to show the currently tracked session and elapsed time.
- `vmt stop` to end the active session, with `--at` and `--round` flags to adjust
  the exact end time
- `vmt log` to display sessions tracked over the last 7 days.
- Session tags (e.g. `+python`) for categorizing tracked work.

[Unreleased]: https://github.com/jbranchaud/py-vmt/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/jbranchaud/py-vmt/releases/tag/v0.1.0
