#!/usr/bin/env python3
"""Validate a Qwen3.6 OSWorld run manifest and referenced hashes."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from osworld_eval_common import DEFAULT_MODEL_ID, load_json, repo_root, sha256_file

REQUIRED_FIELDS = [
    "run_id",
    "created_at",
    "config_hash",
    "sample_seed",
    "sample_manifest",
    "sample_manifest_hash",
    "exclusion_manifest",
    "exclusion_manifest_hash",
    "osworld_commit",
    "model_id",
    "serving_backend",
    "endpoint_redacted",
    "decoding",
    "max_steps",
    "retry_policy",
    "provider",
    "artifact_roots",
]

SECRET_PATTERNS = [re.compile(r"sk-[A-Za-z0-9_\-]{8,}"), re.compile(r"api[_-]?key", re.I), re.compile(r"bearer\s+", re.I)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-manifest", required=True)
    return parser.parse_args()


def resolve(path: str, base: Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else base / p


def check_hash(label: str, manifest: dict[str, Any], path_key: str, hash_key: str, problems: list[str], base: Path) -> None:
    path_value = manifest.get(path_key)
    expected = manifest.get(hash_key)
    if not path_value or not expected:
        problems.append(f"missing {path_key}/{hash_key}")
        return
    path = resolve(str(path_value), base)
    if not path.exists():
        problems.append(f"{label} does not exist: {path}")
        return
    actual = sha256_file(path)
    if actual != expected:
        problems.append(f"{label} hash mismatch: expected {expected}, got {actual}")


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.run_manifest)
    if not manifest_path.is_absolute():
        manifest_path = repo_root() / manifest_path
    manifest = load_json(manifest_path)
    base = repo_root()
    problems: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in manifest or manifest[field] in (None, ""):
            problems.append(f"missing required field: {field}")
    if manifest.get("model_id") != DEFAULT_MODEL_ID:
        problems.append(f"model_id should be {DEFAULT_MODEL_ID}, got {manifest.get('model_id')}")
    endpoint = str(manifest.get("endpoint_redacted", ""))
    if any(p.search(endpoint) for p in SECRET_PATTERNS):
        problems.append("endpoint_redacted appears to contain a secret or API-key label")
    for section in ["decoding", "retry_policy", "provider", "artifact_roots"]:
        if section in manifest and not isinstance(manifest[section], dict):
            problems.append(f"{section} must be an object")
    if "max_steps" in manifest and (not isinstance(manifest["max_steps"], int) or manifest["max_steps"] <= 0):
        problems.append("max_steps must be a positive integer")
    check_hash("sample manifest", manifest, "sample_manifest", "sample_manifest_hash", problems, base)
    check_hash("exclusion manifest", manifest, "exclusion_manifest", "exclusion_manifest_hash", problems, base)
    if manifest.get("overlay_install_manifest") and manifest.get("overlay_install_hash"):
        check_hash("overlay install manifest", manifest, "overlay_install_manifest", "overlay_install_hash", problems, base)
    if problems:
        raise SystemExit("Run manifest validation failed:\n" + "\n".join(problems))
    print(f"Run manifest valid: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
