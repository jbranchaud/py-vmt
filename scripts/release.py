"""Cut a release of visualmode-tracker.

Usage:
    mise run release <patch|minor|major> [--dry-run] [--yes]
    mise run release --resume vX.Y.Z

Nothing leaves this machine until every local check has passed. Steps:

1. Preflight: tools, gh auth, on an up-to-date `main`, clean tree, CI green,
   non-empty `[Unreleased]` changelog section.
2. Work out the next version and make sure it isn't tagged or on PyPI.
3. Confirm (skipped with --yes; --dry-run stops here and previews changes).
4. Bump the version and roll the changelog.
5. Build and smoke test the wheel.
6. Commit and tag (any failure in 4-6 is rolled back).
7. Push `main` and the tag atomically.
8. Wait for the `release` workflow, then create the GitHub Release.

--resume vX.Y.Z picks up at step 8 for a tag that is already pushed.
"""

import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PACKAGE = "visualmode-tracker"
REPO_URL = "https://github.com/jbranchaud/py-vmt"
RELEASE_WORKFLOW = "release.yml"
REQUIRED_CHECKS = {"pytest", "ruff", "basedpyright"}
RELEASE_FILES = ["pyproject.toml", "uv.lock", "CHANGELOG.md"]

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "CHANGELOG.md"

UNRELEASED_HEADING = re.compile(r"^## \[Unreleased\][^\n]*\n", re.MULTILINE)
VERSION_HEADING = re.compile(r"^## \[(\d[^\]]*)\]", re.MULTILINE)
LINK_DEFS = re.compile(r"^\[[^\]]+\]: ", re.MULTILINE)
UNRELEASED_LINK = re.compile(r"^\[Unreleased\]: .*$", re.MULTILINE)


class ReleaseError(Exception):
    pass


# -- helpers -----------------------------------------------------------------


def step(msg: str) -> None:
    print(f"\n==> {msg}", flush=True)


def info(msg: str) -> None:
    print(f"    {msg}", flush=True)


def run(*cmd: str, capture: bool = True, check: bool = True) -> str:
    result = subprocess.run(
        cmd, cwd=ROOT, text=True, capture_output=capture, check=False
    )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip() if capture else ""
        raise ReleaseError(f"`{' '.join(cmd)}` failed\n{detail}".rstrip())
    return (result.stdout or "").strip() if capture else ""


def succeeds(*cmd: str) -> bool:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True).returncode == 0


# -- changelog ---------------------------------------------------------------


def _section_body(text: str, start: int) -> str:
    """Text from `start` up to the next version heading or the link definitions."""
    rest = text[start:]
    ends = (VERSION_HEADING.search(rest), LINK_DEFS.search(rest))
    end = min((m.start() for m in ends if m), default=len(rest))
    return rest[:end].strip()


def unreleased_body(text: str) -> str:
    match = UNRELEASED_HEADING.search(text)
    if not match:
        raise ReleaseError("CHANGELOG.md has no `## [Unreleased]` section")
    return _section_body(text, match.end())


def has_entries(body: str) -> bool:
    return any(line.lstrip().startswith("- ") for line in body.splitlines())


def latest_released_version(text: str) -> str | None:
    match = VERSION_HEADING.search(text)
    return match.group(1) if match else None


def roll_changelog(text: str, prev: str, new: str, today: datetime.date) -> str:
    """Turn `[Unreleased]` into `[new]` and point the links at the new tag."""
    match = UNRELEASED_HEADING.search(text)
    if not match:
        raise ReleaseError("CHANGELOG.md has no `## [Unreleased]` section")
    heading = f"## [Unreleased]\n\n## [{new}] - {today.isoformat()}\n"
    text = text[: match.start()] + heading + text[match.end() :]

    new_links = (
        f"[Unreleased]: {REPO_URL}/compare/v{new}...HEAD\n"
        f"[{new}]: {REPO_URL}/compare/v{prev}...v{new}"
    )
    text, count = UNRELEASED_LINK.subn(new_links, text, count=1)
    if count != 1:
        raise ReleaseError("CHANGELOG.md has no `[Unreleased]: ...` link")
    return text


def release_notes(text: str, version: str) -> str:
    heading = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n", text, re.MULTILINE)
    if not heading:
        raise ReleaseError(f"CHANGELOG.md has no section for {version}")
    return _section_body(text, heading.end())


# -- steps -------------------------------------------------------------------


def preflight() -> None:
    step("Preflight checks")

    for tool in ("git", "uv", "gh"):
        if shutil.which(tool) is None:
            raise ReleaseError(f"`{tool}` is not installed")
    if not succeeds("gh", "auth", "status"):
        raise ReleaseError("gh is not authenticated; run `gh auth login`")
    info("tools installed, gh authenticated")

    branch = run("git", "branch", "--show-current")
    if branch != "main":
        raise ReleaseError(
            f"must release from `main` (on `{branch or 'detached HEAD'}`)"
        )

    if run("git", "status", "--porcelain", "--untracked-files=no"):
        raise ReleaseError("tracked files have uncommitted changes")
    info("on `main` with a clean working tree")

    run("git", "fetch", "--quiet", "--tags", "origin", "main")
    local = run("git", "rev-parse", "HEAD")
    remote = run("git", "rev-parse", "origin/main")
    if local != remote:
        raise ReleaseError(
            "local `main` differs from `origin/main`; pull or push first"
        )
    info("up to date with `origin/main`")

    runs = json.loads(
        run(
            "gh",
            "run",
            "list",
            "--commit",
            local,
            "--event",
            "push",
            "--json",
            "name,status,conclusion",
        )
    )
    seen = {r["name"]: r for r in runs}
    missing = REQUIRED_CHECKS - seen.keys()
    if missing:
        raise ReleaseError(f"no CI runs for HEAD yet: {', '.join(sorted(missing))}")
    bad = [
        f"{name} ({seen[name]['conclusion'] or seen[name]['status']})"
        for name in sorted(REQUIRED_CHECKS)
        if seen[name]["conclusion"] != "success"
    ]
    if bad:
        raise ReleaseError(f"CI is not green for HEAD: {', '.join(bad)}")
    info(f"CI green for {local[:7]}: {', '.join(sorted(REQUIRED_CHECKS))}")

    if not has_entries(unreleased_body(CHANGELOG.read_text())):
        raise ReleaseError("`## [Unreleased]` in CHANGELOG.md has no entries")
    info("changelog has unreleased entries")


def on_pypi(version: str) -> bool:
    url = f"https://pypi.org/pypi/{PACKAGE}/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=10):
            return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise ReleaseError(f"PyPI lookup failed: HTTP {e.code}") from e
    except urllib.error.URLError as e:
        raise ReleaseError(f"PyPI lookup failed: {e.reason}") from e


def plan_version(part: str) -> tuple[str, str]:
    step("Working out the version")
    current = run("uv", "version", "--short")
    new = run("uv", "version", "--bump", part, "--dry-run", "--short")
    tag = f"v{new}"

    if succeeds("git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"):
        raise ReleaseError(f"tag {tag} already exists locally")
    if run("git", "ls-remote", "--tags", "origin", f"refs/tags/{tag}"):
        raise ReleaseError(f"tag {tag} already exists on origin")
    if on_pypi(new):
        raise ReleaseError(f"{PACKAGE} {new} is already on PyPI")

    prev = latest_released_version(CHANGELOG.read_text())
    if prev != current:
        raise ReleaseError(
            f"latest CHANGELOG.md release ({prev}) doesn't match pyproject.toml ({current})"
        )
    info(f"{current} -> {new}")
    return current, new


def confirm(current: str, new: str, notes: str, assume_yes: bool) -> None:
    step(f"Release v{new} (from {current}) with these notes:")
    print("\n" + "\n".join(f"    {line}" for line in notes.splitlines()) + "\n")
    if assume_yes:
        return
    answer = input(f"Release v{new}? [y/N] ").strip().lower()
    if answer not in ("y", "yes"):
        raise ReleaseError("aborted")


def apply_release(part: str, current: str, new: str) -> None:
    step("Bumping the version and rolling the changelog")
    run("uv", "version", "--bump", part, "--no-sync")
    if (actual := run("uv", "version", "--short")) != new:
        raise ReleaseError(f"expected version {new} after bump, got {actual}")

    text = roll_changelog(CHANGELOG.read_text(), current, new, datetime.date.today())
    CHANGELOG.write_text(text)
    if latest_released_version(text) != new:
        raise ReleaseError("changelog rewrite didn't produce the new version heading")
    info(f"pyproject.toml, uv.lock and CHANGELOG.md updated for {new}")


def build_and_smoke_test(new: str) -> None:
    step("Building and smoke testing")
    shutil.rmtree(ROOT / "dist", ignore_errors=True)
    run("uv", "build", "--quiet")
    wheels = list((ROOT / "dist").glob(f"*-{new}-*.whl"))
    if len(wheels) != 1:
        raise ReleaseError(f"expected one {new} wheel in dist/, found {len(wheels)}")

    out = run(
        "uv", "tool", "run", "--isolated", "--from", str(wheels[0]), "vmt", "--version"
    )
    if not out.endswith(new):
        raise ReleaseError(f"built wheel reports `{out}`, expected {new}")
    info(f"{wheels[0].name} -> `{out}`")


def commit_and_tag(new: str) -> None:
    step("Committing and tagging")
    tag = f"v{new}"
    run("git", "add", *RELEASE_FILES)
    run("git", "commit", "--quiet", "-m", f"Release {tag}")
    run("git", "tag", "-a", tag, "-m", f"Release {tag}")
    info(f"committed and tagged {tag}")


def rollback(start_sha: str, tag: str) -> None:
    step("Rolling back local changes")
    # Preflight guaranteed tracked files were clean, so this only discards the
    # release changes. Untracked files are left alone.
    run("git", "reset", "--hard", "--quiet", start_sha, check=False)
    run("git", "tag", "-d", tag, check=False)
    info(f"reset to {start_sha[:7]}, removed tag {tag} if it was created")


def push(new: str) -> None:
    step("Pushing `main` and the tag")
    run("git", "push", "--atomic", "origin", "main", f"v{new}", capture=False)


def find_release_run(tag: str, timeout: int = 120) -> int:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        runs = json.loads(
            run(
                "gh",
                "run",
                "list",
                "--workflow",
                RELEASE_WORKFLOW,
                "--branch",
                tag,
                "--limit",
                "1",
                "--json",
                "databaseId",
            )
        )
        if runs:
            return runs[0]["databaseId"]
        time.sleep(5)
    raise ReleaseError(f"no `{RELEASE_WORKFLOW}` run appeared for {tag}")


def wait_for_pypi(version: str, timeout: int = 180) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if on_pypi(version):
            return True
        time.sleep(10)
    return False


def publish(new: str) -> None:
    tag = f"v{new}"
    step(f"Waiting for the `{RELEASE_WORKFLOW}` workflow")
    run_id = find_release_run(tag)
    if not succeeds("gh", "run", "watch", str(run_id), "--exit-status"):
        raise ReleaseError(
            f"release workflow failed: {REPO_URL}/actions/runs/{run_id}\n"
            f"If nothing reached PyPI, fix it, re-run the workflow, then run:\n"
            f"    mise run release --resume {tag}\n"
            f"If {new} did reach PyPI, never reuse it: fix and release a new patch."
        )
    info("workflow succeeded")

    step("Creating the GitHub Release")
    if succeeds("gh", "release", "view", tag):
        info(f"GitHub Release {tag} already exists")
    else:
        notes = release_notes(CHANGELOG.read_text(), new)
        run("gh", "release", "create", tag, "--title", tag, "--notes", notes)
        info(f"created {REPO_URL}/releases/tag/{tag}")

    step("Checking PyPI")
    if wait_for_pypi(new):
        info(f"https://pypi.org/project/{PACKAGE}/{new}/")
    else:
        info(
            f"{new} isn't visible on PyPI yet; check https://pypi.org/project/{PACKAGE}/"
        )


# -- entry points ------------------------------------------------------------


def release(part: str, dry_run: bool, assume_yes: bool) -> None:
    preflight()
    current, new = plan_version(part)
    notes = unreleased_body(CHANGELOG.read_text())

    if dry_run:
        step("Dry run: no changes made")
        info(f"would release v{new} (from {current}) with these notes:")
        print("\n" + "\n".join(f"    {line}" for line in notes.splitlines()))
        return

    confirm(current, new, notes, assume_yes)

    start_sha = run("git", "rev-parse", "HEAD")
    try:
        apply_release(part, current, new)
        build_and_smoke_test(new)
        commit_and_tag(new)
    except BaseException:
        rollback(start_sha, f"v{new}")
        raise

    push(new)
    publish(new)
    step(f"Released v{new}")


def resume(tag: str) -> None:
    if not re.fullmatch(r"v\d+\.\d+\.\d+\S*", tag):
        raise ReleaseError(f"`{tag}` doesn't look like a release tag (vX.Y.Z)")
    if not run("git", "ls-remote", "--tags", "origin", f"refs/tags/{tag}"):
        raise ReleaseError(f"tag {tag} isn't on origin; nothing to resume")
    publish(tag.removeprefix("v"))
    step(f"Released {tag}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Cut a visualmode-tracker release.")
    parser.add_argument("part", nargs="?", choices=["patch", "minor", "major"])
    parser.add_argument("--dry-run", action="store_true", help="check and preview only")
    parser.add_argument("--yes", action="store_true", help="skip the confirmation")
    parser.add_argument(
        "--resume", metavar="TAG", help="resume publishing a pushed tag"
    )
    args = parser.parse_args()

    if bool(args.part) == bool(args.resume):
        parser.error("pass exactly one of PART or --resume TAG")

    try:
        if args.resume:
            resume(args.resume)
        else:
            release(args.part, args.dry_run, args.yes)
    except ReleaseError as e:
        print(f"\nerror: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
