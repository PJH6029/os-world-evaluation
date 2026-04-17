#!/usr/bin/env python3
"""Deterministically sample OSWorld no-Google-Drive tasks per app/domain."""

from __future__ import annotations

import argparse
import hashlib
import random
from pathlib import Path
from typing import Any

from osworld_eval_common import (
    DEFAULT_OSWORLD_COMMIT,
    DEFAULT_SEED,
    ensure_expected_osworld_paths,
    git_rev_parse,
    load_json,
    relative_or_abs,
    repo_root,
    sha256_file,
    sha256_json,
    write_json,
)

DRIVE_MARKERS = ("google drive", "google_drive", "gdrive", "drive.google")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--osworld-home", default="external/OSWorld")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--max-per-domain", type=int, default=5)
    parser.add_argument("--out", default="artifacts/manifests/qwen36_osworld_sample_seed36035.json")
    parser.add_argument("--meta-out", default="artifacts/manifests/qwen36_osworld_sample_seed36035_meta.json")
    parser.add_argument("--exclusions-out", default="artifacts/manifests/osworld_google_drive_exclusions.json")
    parser.add_argument("--expected-commit", default=DEFAULT_OSWORLD_COMMIT)
    parser.add_argument("--validate-no-gdrive", action="store_true", help="Validate an existing or newly written manifest")
    return parser.parse_args()


def domain_rng(seed: int, domain: str) -> random.Random:
    digest = hashlib.sha256(f"{seed}:{domain}".encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def config_path(osworld_home: Path, domain: str, task_id: str) -> Path:
    return osworld_home / "evaluation_examples" / "examples" / domain / f"{task_id}.json"


def load_task_config(osworld_home: Path, domain: str, task_id: str) -> tuple[dict[str, Any], str | None]:
    path = config_path(osworld_home, domain, task_id)
    if not path.exists():
        return {}, f"missing task config: {path}"
    try:
        data = load_json(path)
        return data if isinstance(data, dict) else {}, None
    except Exception as exc:  # noqa: BLE001 - report config read failure in manifest
        return {}, f"failed to load task config: {exc}"


def detect_drive_marker(task: dict[str, Any]) -> bool:
    blob = str(task).lower()
    return any(marker in blob for marker in DRIVE_MARKERS)


def build_exclusion_manifest(osworld_home: Path, all_meta: dict[str, list[str]], nogdrive_meta: dict[str, list[str]], commit: str) -> dict[str, Any]:
    excluded: list[dict[str, Any]] = []
    for domain in sorted(all_meta):
        all_ids = {str(task_id) for task_id in all_meta.get(domain, [])}
        nogdrive_ids = {str(task_id) for task_id in nogdrive_meta.get(domain, [])}
        for task_id in sorted(all_ids - nogdrive_ids):
            task, load_error = load_task_config(osworld_home, domain, task_id)
            item = {
                "config_load_error": load_error,
                "config_path": str(config_path(osworld_home, domain, task_id).relative_to(osworld_home)),
                "domain": domain,
                "excluded_reason": "google_drive",
                "instruction": task.get("instruction"),
                "related_apps": task.get("related_apps"),
                "task_id": task_id,
            }
            excluded.append(item)
    return {
        "derivation_rule": "evaluation_examples/test_all.json minus evaluation_examples/test_nogdrive.json at the pinned OSWorld commit",
        "excluded_count": len(excluded),
        "excluded_tasks": excluded,
        "osworld_commit": commit,
        "source_all_manifest": "evaluation_examples/test_all.json",
        "source_nogdrive_manifest": "evaluation_examples/test_nogdrive.json",
    }


def sample_tasks(osworld_home: Path, nogdrive_meta: dict[str, list[str]], seed: int, max_per_domain: int, commit: str) -> tuple[dict[str, Any], dict[str, list[str]]]:
    sampled_tasks: list[dict[str, Any]] = []
    sampled_meta: dict[str, list[str]] = {}
    domain_counts: dict[str, dict[str, int]] = {}
    for domain in sorted(nogdrive_meta):
        candidates = sorted(str(task_id) for task_id in nogdrive_meta[domain])
        rng = domain_rng(seed, domain)
        k = min(max_per_domain, len(candidates))
        selected = rng.sample(candidates, k) if k else []
        sampled_meta[domain] = selected
        domain_counts[domain] = {
            "eligible": len(candidates),
            "sampled": len(selected),
            "shortfall": max(0, max_per_domain - len(candidates)),
        }
        for rank, task_id in enumerate(selected, 1):
            task, load_error = load_task_config(osworld_home, domain, task_id)
            rel_config = str(config_path(osworld_home, domain, task_id).relative_to(osworld_home))
            sampled_tasks.append(
                {
                    "app": domain,
                    "config_load_error": load_error,
                    "config_path": rel_config,
                    "domain": domain,
                    "instruction": task.get("instruction"),
                    "related_apps": task.get("related_apps"),
                    "sample_rank_within_domain": rank,
                    "sample_seed": seed,
                    "task_id": task_id,
                }
            )
    manifest = {
        "manifest_type": "qwen36_osworld_sample",
        "max_tasks_per_domain": max_per_domain,
        "osworld_commit": commit,
        "sample_seed": seed,
        "sampling_algorithm": "For each lexicographically sorted test_nogdrive domain, sort task IDs as strings and sample min(max_per_domain,n) using random.Random(int.from_bytes(sha256(f'{seed}:{domain}')[:8],'big')).sample(...).",
        "sampling_unit": "official evaluation_examples/test_nogdrive.json domain key; multi_apps remains one category",
        "domain_counts": domain_counts,
        "tasks": sampled_tasks,
        "total_sampled": len(sampled_tasks),
    }
    return manifest, sampled_meta


def validate_no_gdrive(manifest: dict[str, Any], exclusion_manifest: dict[str, Any], osworld_home: Path) -> None:
    excluded_ids = {(item["domain"], item["task_id"]) for item in exclusion_manifest.get("excluded_tasks", [])}
    problems: list[str] = []
    for task in manifest.get("tasks", []):
        key = (str(task["domain"]), str(task["task_id"]))
        if key in excluded_ids:
            problems.append(f"sample contains excluded Google Drive task {key}")
        task_config, load_error = load_task_config(osworld_home, key[0], key[1])
        if load_error is None and detect_drive_marker(task_config):
            problems.append(f"sample task metadata contains Google Drive marker {key}")
    if problems:
        raise SystemExit("No-Google-Drive validation failed:\n" + "\n".join(problems))


def main() -> int:
    args = parse_args()
    osworld_home = Path(args.osworld_home)
    if not osworld_home.is_absolute():
        osworld_home = repo_root() / osworld_home
    ensure_expected_osworld_paths(osworld_home)
    commit = git_rev_parse(osworld_home)
    if args.expected_commit and commit != args.expected_commit:
        raise SystemExit(f"OSWorld commit mismatch: expected {args.expected_commit}, got {commit}")

    all_meta = load_json(osworld_home / "evaluation_examples" / "test_all.json")
    nogdrive_meta = load_json(osworld_home / "evaluation_examples" / "test_nogdrive.json")
    if not isinstance(all_meta, dict) or not isinstance(nogdrive_meta, dict):
        raise SystemExit("OSWorld manifests must be JSON objects keyed by domain")

    exclusion_manifest = build_exclusion_manifest(osworld_home, all_meta, nogdrive_meta, commit)
    manifest, sampled_meta = sample_tasks(osworld_home, nogdrive_meta, args.seed, args.max_per_domain, commit)

    exclusions_path = repo_root() / args.exclusions_out
    write_json(exclusions_path, exclusion_manifest)
    exclusion_hash = sha256_file(exclusions_path)
    manifest["google_drive_exclusion_manifest"] = relative_or_abs(exclusions_path, repo_root())
    manifest["google_drive_exclusion_manifest_sha256"] = exclusion_hash
    manifest["sample_manifest_sha256"] = sha256_json({k: v for k, v in manifest.items() if k != "sample_manifest_sha256"})

    out_path = repo_root() / args.out
    meta_path = repo_root() / args.meta_out
    write_json(out_path, manifest)
    write_json(meta_path, sampled_meta)

    if args.validate_no_gdrive:
        validate_no_gdrive(manifest, exclusion_manifest, osworld_home)

    print(f"Wrote sample manifest: {out_path}")
    print(f"Wrote OSWorld sampled meta: {meta_path}")
    print(f"Wrote Google Drive exclusions: {exclusions_path}")
    print(f"Sampled {manifest['total_sampled']} tasks across {len(sampled_meta)} domains")
    print(f"Exclusions: {exclusion_manifest['excluded_count']} tasks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
