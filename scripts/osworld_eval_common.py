#!/usr/bin/env python3
"""Shared utilities for the Qwen3.6 OSWorld evaluation harness."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Iterable

DEFAULT_OSWORLD_REPO = "https://github.com/xlang-ai/OSWorld.git"
DEFAULT_OSWORLD_COMMIT = "e8ba8fde29889ae7e4377f6f325d736818434a04"
DEFAULT_SEED = 36035
DEFAULT_MODEL_ID = "Qwen/Qwen3.6-35B-A3B"

REQUIRED_OSWORLD_PATHS = [
    "evaluation_examples/test_all.json",
    "evaluation_examples/test_nogdrive.json",
    "scripts/python/run_multienv_qwen3vl.py",
    "mm_agents/qwen3vl_agent.py",
    "lib_run_single.py",
]

PRIMARY_FAILURE_TAGS = [
    "visual_perception",
    "action_grounding",
    "planning",
    "tool_ui_confusion",
]

ALL_FAILURE_TAGS = PRIMARY_FAILURE_TAGS + ["mixed_uncertain"]
VALID_STATUSES = {"success", "model_failure", "environment_invalid", "not_run", "unknown"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_json(path: os.PathLike[str] | str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: os.PathLike[str] | str, data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def canonical_json_bytes(data: Any) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: os.PathLike[str] | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_json(data: Any) -> str:
    return sha256_bytes(canonical_json_bytes(data))


def run(cmd: list[str], cwd: os.PathLike[str] | str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def git_rev_parse(path: os.PathLike[str] | str) -> str:
    cp = run(["git", "rev-parse", "HEAD"], cwd=path)
    return cp.stdout.strip()


def ensure_expected_osworld_paths(osworld_home: os.PathLike[str] | str) -> list[str]:
    root = Path(osworld_home)
    missing = [rel for rel in REQUIRED_OSWORLD_PATHS if not (root / rel).exists()]
    if missing:
        raise FileNotFoundError(
            "OSWorld checkout is missing required paths: " + ", ".join(missing)
        )
    return REQUIRED_OSWORLD_PATHS.copy()


def relative_or_abs(path: Path, base: Path | None = None) -> str:
    try:
        return str(path.relative_to(base or repo_root()))
    except ValueError:
        return str(path)


def iter_jsonl(path: os.PathLike[str] | str) -> Iterable[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    yield obj
                else:
                    yield {"_line": line_no, "_non_object": obj}
            except json.JSONDecodeError as exc:
                yield {"_line": line_no, "_decode_error": str(exc), "raw": line}


def write_jsonl(path: os.PathLike[str] | str, rows: Iterable[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            f.write("\n")
