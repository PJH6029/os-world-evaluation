#!/usr/bin/env python3
"""Prepare or validate a pinned OSWorld checkout for Qwen3.6 evaluation."""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from osworld_eval_common import (
    DEFAULT_OSWORLD_COMMIT,
    DEFAULT_OSWORLD_REPO,
    ensure_expected_osworld_paths,
    git_rev_parse,
    repo_root,
    run,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--osworld-home", default="external/OSWorld", help="OSWorld checkout path")
    parser.add_argument("--repo-url", default=DEFAULT_OSWORLD_REPO)
    parser.add_argument("--commit", default=DEFAULT_OSWORLD_COMMIT)
    parser.add_argument("--check-only", action="store_true", help="Validate existing checkout only")
    parser.add_argument("--revision-out", default="artifacts/osworld_revision.json")
    return parser.parse_args()


def clone_or_update(home: Path, repo_url: str, commit: str) -> None:
    if not home.exists():
        home.parent.mkdir(parents=True, exist_ok=True)
        print(f"Cloning OSWorld into {home}...")
        run(["git", "clone", repo_url, str(home)], cwd=repo_root())
    if not (home / ".git").exists():
        raise SystemExit(f"{home} exists but is not a git checkout")
    run(["git", "fetch", "--all", "--tags"], cwd=home)
    run(["git", "checkout", commit], cwd=home)


def main() -> int:
    args = parse_args()
    home = Path(args.osworld_home)
    if not home.is_absolute():
        home = repo_root() / home

    if args.check_only:
        if not home.exists():
            raise SystemExit(f"OSWorld checkout does not exist: {home}")
    else:
        clone_or_update(home, args.repo_url, args.commit)

    actual_commit = git_rev_parse(home)
    if actual_commit != args.commit:
        raise SystemExit(f"OSWorld commit mismatch: expected {args.commit}, got {actual_commit}")

    checked_paths = ensure_expected_osworld_paths(home)
    revision = {
        "checked_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "commit": actual_commit,
        "expected_commit": args.commit,
        "osworld_home": str(home),
        "repo_url": args.repo_url,
        "required_paths": checked_paths,
    }
    write_json(repo_root() / args.revision_out, revision)
    print(f"OSWorld ready at {home} ({actual_commit})")
    print(f"Wrote {args.revision_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
