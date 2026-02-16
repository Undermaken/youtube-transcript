#!/usr/bin/env python3
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from constants import APP_VERSION

SEMVER_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
PLAIN_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int

    def bump(self, kind: str) -> "SemVer":
        if kind == "major":
            return SemVer(self.major + 1, 0, 0)
        if kind == "minor":
            return SemVer(self.major, self.minor + 1, 0)
        if kind in {"patch", "fix"}:
            return SemVer(self.major, self.minor, self.patch + 1)
        raise ValueError(f"Unknown bump kind: {kind}")

    def tag(self) -> str:
        return f"v{self.major}.{self.minor}.{self.patch}"


def run_git(args: list[str], *, capture: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )
    return result.stdout.strip() if capture and result.stdout else ""


def get_current_branch() -> str:
    return run_git(["rev-parse", "--abbrev-ref", "HEAD"])


def get_repo_root() -> Path:
    return Path(__file__).resolve().parent


def get_git_status_porcelain() -> str:
    return run_git(["status", "--porcelain"])


def get_app_version() -> SemVer:
    match = PLAIN_SEMVER_RE.match(APP_VERSION.strip())
    if not match:
        raise ValueError("APP_VERSION must be in the form X.Y.Z (e.g. 1.2.3).")
    return SemVer(int(match[1]), int(match[2]), int(match[3]))


def update_app_version(version: SemVer) -> None:
    constants_path = get_repo_root() / "constants.py"
    content = constants_path.read_text(encoding="utf-8")

    # Aggiorna APP_VERSION
    updated, count = re.subn(
        r'APP_VERSION\s*=\s*"[^"]+"',
        f'APP_VERSION = "{version.tag().lstrip("v")}"',
        content,
        count=1,
    )
    if count != 1:
        raise ValueError("Unable to update APP_VERSION in constants.py.")

    # Aggiorna APP_UPDATE con la data corrente (formato DD-MM-YYYY)
    today = datetime.now()
    date_str = f"{today.day:02d}-{today.month:02d}-{today.year}"
    updated, count = re.subn(
        r'APP_UPDATE\s*=\s*"[^"]+"',
        f'APP_UPDATE = "{date_str}"',
        updated,
        count=1,
    )
    if count != 1:
        raise ValueError("Unable to update APP_UPDATE in constants.py.")

    constants_path.write_text(updated, encoding="utf-8")


def prompt_choice() -> str:
    print("Select release type:")
    print("  1) major")
    print("  2) minor")
    print("  3) fix")
    choice = input("Choice [1-3]: ").strip()
    return {"1": "major", "2": "minor", "3": "fix"}.get(choice, "")


def prompt_tag(default_tag: str) -> str:
    tag = input(f"Tag to create [{default_tag}]: ").strip()
    return tag or default_tag


def main() -> int:
    try:
        branch = get_current_branch()
    except subprocess.CalledProcessError as exc:
        print("Unable to read the current git branch.")
        if exc.stdout:
            print(exc.stdout)
        return 1

    if branch != "main":
        print(f"Current branch is '{branch}'. Please switch to 'main' before releasing.")
        return 1

    if get_git_status_porcelain():
        print("Working tree is not clean. Please commit or stash changes before releasing.")
        return 1

    try:
        current = get_app_version()
    except ValueError as exc:
        print(str(exc))
        return 1

    print(f"APP_VERSION: {current.tag().lstrip('v')}")

    bump_kind = ""
    while bump_kind not in {"major", "minor", "fix"}:
        bump_kind = prompt_choice()
        if bump_kind not in {"major", "minor", "fix"}:
            print("Please select 1, 2, or 3.")

    suggested = current.bump(bump_kind).tag()
    tag = prompt_tag(suggested)

    if not SEMVER_RE.match(tag):
        print("Tag must be in the form vX.Y.Z (e.g. v1.2.3).")
        return 1

    confirm = input(f"Create and push tag {tag}? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Release cancelled.")
        return 0

    try:
        new_version = SemVer(*map(int, tag.lstrip("v").split(".")))
        print("Updating APP_VERSION...")
        update_app_version(new_version)
        run_git(["add", "constants.py"], capture=False)
        print("Committing version bump...")
        run_git(["commit", "-m", f"Bump version to {tag}"], capture=False)
        print("Creating tag...")
        run_git(["tag", "-a", tag, "-m", f"Release {tag}"], capture=False)
        print("Pushing tag to origin...")
        run_git(["push", "origin", tag], capture=False)
    except subprocess.CalledProcessError as exc:
        print("Git command failed. Please check the repository state.")
        if exc.stdout:
            print(exc.stdout)
        return 1

    print("Tag pushed. The GitHub Action will build and publish the release.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
