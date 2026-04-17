#!/usr/bin/env python3
"""Index Qwen3.6 OSWorld trajectory artifacts and validate the artifact contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from osworld_eval_common import (
    ALL_FAILURE_TAGS,
    DEFAULT_OSWORLD_COMMIT,
    DEFAULT_SEED,
    VALID_STATUSES,
    iter_jsonl,
    load_json,
    repo_root,
    sha256_file,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--run-manifest", default=None)
    parser.add_argument("--out", default="artifacts/trajectory_index/qwen36_osworld_seed36035.jsonl")
    parser.add_argument("--validate-contract", action="store_true")
    return parser.parse_args()


def find_task_dir(results_dir: Path, domain: str, task_id: str) -> Path | None:
    candidates = list(results_dir.glob(f"**/{domain}/{task_id}"))
    dirs = [p for p in candidates if p.is_dir()]
    return sorted(dirs)[0] if dirs else None


def classify_from_artifacts(task_dir: Path | None) -> tuple[str, float | None, str | None]:
    if task_dir is None:
        return "not_run", None, "no task directory found"
    status_path = task_dir / "status.json"
    if status_path.exists():
        try:
            status = load_json(status_path)
            raw = status.get("status", "unknown")
            return raw if raw in VALID_STATUSES else "unknown", status.get("result"), status.get("error")
        except Exception as exc:  # noqa: BLE001
            return "unknown", None, f"status.json unreadable: {exc}"
    result_path = task_dir / "result.txt"
    if result_path.exists():
        try:
            score = float(result_path.read_text(encoding="utf-8").strip())
            return "success" if score >= 1.0 else "model_failure", score, None
        except Exception as exc:  # noqa: BLE001
            return "unknown", None, f"result.txt unreadable: {exc}"
    if any(task_dir.iterdir()):
        return "unknown", None, "partial artifacts exist without result/status"
    return "not_run", None, "empty task directory"


def suggest_tags(rows: list[dict[str, Any]], status: str, status_reason: str | None = None) -> list[str]:
    if status != "model_failure":
        return []
    if status_reason and "no_parseable_action" in status_reason:
        return ["tool_ui_confusion"]
    if any(row.get("event") == "no_parseable_action" for row in rows):
        return ["tool_ui_confusion"]
    blob = "\n".join(json.dumps(row, ensure_ascii=False).lower() for row in rows)
    tags: list[str] = []
    if any(term in blob for term in ["coordinate", "click", "mouse", "pyautogui", "target"]):
        tags.append("action_grounding")
    if any(term in blob for term in ["screenshot", "see", "visible", "icon", "button", "text", "image"]):
        tags.append("visual_perception")
    if any(term in blob for term in ["repeat", "again", "loop", "terminate", "done", "wrong", "subgoal"]):
        tags.append("planning")
    if any(term in blob for term in ["menu", "dialog", "window", "tab", "app", "application", "tool"]):
        tags.append("tool_ui_confusion")
    return sorted(set(tag for tag in tags if tag in ALL_FAILURE_TAGS)) or ["mixed_uncertain"]


def rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(repo_root()))
    except ValueError:
        return str(path)


def manifest_hash(manifest: dict[str, Any]) -> str | None:
    if manifest.get("_manifest_file_sha256"):
        return manifest.get("_manifest_file_sha256")
    if manifest.get("sample_manifest_sha256"):
        return manifest.get("sample_manifest_sha256")
    default_path = repo_root() / "artifacts/manifests/qwen36_osworld_sample_seed36035.json"
    return sha256_file(default_path) if default_path.exists() else None


def build_row(task: dict[str, Any], task_dir: Path | None, manifest: dict[str, Any], run_manifest: dict[str, Any] | None) -> dict[str, Any]:
    status, score, status_reason = classify_from_artifacts(task_dir)
    traj_file = task_dir / "traj.jsonl" if task_dir else None
    rows = list(iter_jsonl(traj_file)) if traj_file and traj_file.exists() else []
    screenshots = sorted(str(p.name) for p in task_dir.glob("*.png")) if task_dir else []
    recording = task_dir / "recording.mp4" if task_dir and (task_dir / "recording.mp4").exists() else None
    status_json = load_json(task_dir / "status.json") if task_dir and (task_dir / "status.json").exists() else {}
    recording_absence_reason = None if recording else status_json.get("recording_absence_reason") or "recording file absent"
    return {
        "run_id": (run_manifest or {}).get("run_id", "unknown"),
        "sample_seed": manifest.get("sample_seed", DEFAULT_SEED),
        "osworld_commit": manifest.get("osworld_commit", DEFAULT_OSWORLD_COMMIT),
        "overlay_install_hash": (run_manifest or {}).get("overlay_install_hash"),
        "sample_manifest_hash": manifest_hash(manifest),
        "task_id": task.get("task_id"),
        "domain": task.get("domain"),
        "instruction": task.get("instruction"),
        "config_path": task.get("config_path"),
        "sample_rank_within_domain": task.get("sample_rank_within_domain"),
        "status": status,
        "status_reason": status_reason,
        "result_score": score,
        "result_file": rel(task_dir / "result.txt") if task_dir and (task_dir / "result.txt").exists() else None,
        "traj_file": rel(traj_file) if traj_file and traj_file.exists() else None,
        "recording_file": rel(recording),
        "recording_absence_reason": recording_absence_reason,
        "runtime_log": rel(task_dir / "runtime.log") if task_dir and (task_dir / "runtime.log").exists() else None,
        "initial_observation_file": rel(task_dir / "initial_state.png") if task_dir and (task_dir / "initial_state.png").exists() else None,
        "screenshots": screenshots,
        "step_count": len([row for row in rows if row.get("event") == "step" or "step_num" in row]),
        "failure_tags": suggest_tags(rows, status, status_reason),
        "tag_source": "agent_suggested",
        "task_dir": rel(task_dir),
    }


def validate_rows(rows: list[dict[str, Any]]) -> None:
    problems: list[str] = []
    required = ["run_id", "sample_seed", "osworld_commit", "task_id", "domain", "status", "tag_source"]
    for row in rows:
        ident = f"{row.get('domain')}/{row.get('task_id')}"
        for key in required:
            if row.get(key) in (None, ""):
                problems.append(f"{ident}: missing {key}")
        if row.get("status") not in VALID_STATUSES:
            problems.append(f"{ident}: invalid status {row.get('status')}")
        if row.get("status") != "not_run" and not (row.get("traj_file") or row.get("status_reason")):
            problems.append(f"{ident}: attempted row needs traj_file or status_reason")
        if not row.get("recording_file") and not row.get("recording_absence_reason"):
            problems.append(f"{ident}: missing recording_file and recording_absence_reason")
        if row.get("status") == "unknown" and row.get("failure_tags"):
            problems.append(f"{ident}: unknown status cannot carry model-failure tags")
    if problems:
        raise SystemExit("Trajectory contract validation failed:\n" + "\n".join(problems))


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = repo_root() / manifest_path
    manifest = load_json(manifest_path)
    manifest["_manifest_file_sha256"] = sha256_file(manifest_path)
    run_manifest = None
    if args.run_manifest:
        rm_path = Path(args.run_manifest)
        if not rm_path.is_absolute():
            rm_path = repo_root() / rm_path
        run_manifest = load_json(rm_path)
    results_dir = Path(args.results_dir)
    if not results_dir.is_absolute():
        results_dir = repo_root() / results_dir
    rows = [build_row(task, find_task_dir(results_dir, str(task["domain"]), str(task["task_id"])), manifest, run_manifest) for task in manifest.get("tasks", [])]
    if args.validate_contract:
        validate_rows(rows)
    out = Path(args.out)
    if not out.is_absolute():
        out = repo_root() / out
    write_jsonl(out, rows)
    print(f"Indexed {len(rows)} tasks -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
