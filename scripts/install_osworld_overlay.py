#!/usr/bin/env python3
"""Install or verify Qwen3.6 OSWorld overlay files with provenance."""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
from pathlib import Path
from typing import Any

from osworld_eval_common import (
    DEFAULT_OSWORLD_COMMIT,
    ensure_expected_osworld_paths,
    git_rev_parse,
    repo_root,
    sha256_file,
    write_json,
    load_json,
)

OVERLAY_FILES = [
    {
        "source": "overlays/osworld/mm_agents/qwen36_openai_agent.py",
        "destination": "mm_agents/qwen36_openai_agent.py",
        "upstream_base": "mm_agents/qwen3vl_agent.py",
    },
    {
        "source": "overlays/osworld/scripts/python/run_multienv_qwen36.py",
        "destination": "scripts/python/run_multienv_qwen36.py",
        "upstream_base": "scripts/python/run_multienv_qwen3vl.py",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--osworld-home", default="external/OSWorld")
    parser.add_argument("--expected-commit", default=DEFAULT_OSWORLD_COMMIT)
    parser.add_argument("--manifest-out", default="artifacts/osworld_overlay_install.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--force-managed", action="store_true", help="Allow overwriting a destination already recorded in prior manifest")
    return parser.parse_args()


def prior_managed_destinations(manifest_path: Path) -> set[str]:
    if not manifest_path.exists():
        return set()
    try:
        data = load_json(manifest_path)
    except Exception:
        return set()
    return {item.get("destination") for item in data.get("files", []) if item.get("destination")}


def build_record(osworld_home: Path, item: dict[str, str]) -> dict[str, Any]:
    src = repo_root() / item["source"]
    dst = osworld_home / item["destination"]
    upstream = osworld_home / item["upstream_base"]
    if not src.exists():
        raise FileNotFoundError(f"missing overlay source: {src}")
    if not upstream.exists():
        raise FileNotFoundError(f"missing upstream base: {upstream}")
    return {
        "source": item["source"],
        "destination": item["destination"],
        "upstream_base": item["upstream_base"],
        "upstream_base_sha256": sha256_file(upstream),
        "source_sha256": sha256_file(src),
        "destination_sha256": sha256_file(dst) if dst.exists() else None,
        "destination_exists": dst.exists(),
    }


def main() -> int:
    args = parse_args()
    osworld_home = Path(args.osworld_home)
    if not osworld_home.is_absolute():
        osworld_home = repo_root() / osworld_home
    ensure_expected_osworld_paths(osworld_home)
    commit = git_rev_parse(osworld_home)
    if commit != args.expected_commit:
        raise SystemExit(f"OSWorld commit mismatch: expected {args.expected_commit}, got {commit}")

    manifest_path = repo_root() / args.manifest_out
    managed = prior_managed_destinations(manifest_path)
    records = [build_record(osworld_home, item) for item in OVERLAY_FILES]

    errors: list[str] = []
    for record in records:
        dst = osworld_home / record["destination"]
        if args.check_only:
            if not dst.exists():
                errors.append(f"missing installed overlay: {record['destination']}")
            elif record["destination_sha256"] != record["source_sha256"]:
                errors.append(f"installed overlay hash mismatch: {record['destination']}")
        elif dst.exists() and record["destination_sha256"] != record["source_sha256"]:
            if record["destination"] not in managed or not args.force_managed:
                errors.append(
                    f"refusing to overwrite unmanaged or changed destination {record['destination']}; "
                    "use --force-managed only for destinations recorded in the prior manifest"
                )
    if errors:
        raise SystemExit("Overlay verification failed:\n" + "\n".join(errors))

    if args.dry_run:
        for record in records:
            print(f"DRY-RUN copy {record['source']} -> {record['destination']}")
        return 0

    if args.check_only:
        print(f"Overlay verified for OSWorld {commit}")
        print("Check-only mode did not rewrite the overlay install manifest")
        return 0

    for record in records:
        src = repo_root() / record["source"]
        dst = osworld_home / record["destination"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    records = [build_record(osworld_home, item) for item in OVERLAY_FILES]

    manifest = {
        "installed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "installer_version": 1,
        "mode": "install",
        "osworld_commit": commit,
        "osworld_home": str(osworld_home),
        "files": records,
    }
    write_json(manifest_path, manifest)
    print(f"Overlay installed for OSWorld {commit}")
    print(f"Wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
