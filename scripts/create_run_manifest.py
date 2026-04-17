#!/usr/bin/env python3
"""Create a canonical run_manifest.json for Qwen3.6 OSWorld runs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
import socket
from pathlib import Path

from osworld_eval_common import DEFAULT_MODEL_ID, DEFAULT_OSWORLD_COMMIT, DEFAULT_SEED, load_json, repo_root, sha256_file, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--config", default="config/eval.json")
    parser.add_argument("--sample-manifest", default="artifacts/manifests/qwen36_osworld_sample_seed36035.json")
    parser.add_argument("--exclusion-manifest", default="artifacts/manifests/osworld_google_drive_exclusions.json")
    parser.add_argument("--overlay-install-manifest", default="artifacts/osworld_overlay_install.json")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--model-revision", default="unresolved_until_model_download")
    parser.add_argument("--serving-backend", default="not_started")
    parser.add_argument("--serving-backend-version", default="not_started")
    parser.add_argument("--endpoint-redacted", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--top-p", type=float, default=None)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument("--num-envs", type=int, default=None)
    return parser.parse_args()


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else repo_root() / p


def main() -> int:
    args = parse_args()
    run_id = args.run_id or "qwen36_osworld_seed36035_" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = resolve(args.out) if args.out else repo_root() / "artifacts" / "runs" / run_id / "run_manifest.json"
    config = load_json(resolve(args.config))
    overlay_path = resolve(args.overlay_install_manifest)
    decoding = dict(config.get("decoding", {}))
    if args.temperature is not None:
        decoding["temperature"] = args.temperature
    if args.top_p is not None:
        decoding["top_p"] = args.top_p
    if args.max_tokens is not None:
        decoding["max_tokens"] = args.max_tokens
    provider = dict(config.get("provider", {}))
    if args.num_envs is not None:
        provider["num_envs"] = args.num_envs
    max_steps = args.max_steps if args.max_steps is not None else config.get("run", {}).get("max_steps", 15)

    manifest = {
        "run_id": run_id,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "config_hash": sha256_file(resolve(args.config)),
        "sample_seed": config.get("sample", {}).get("seed", DEFAULT_SEED),
        "sample_manifest": args.sample_manifest,
        "sample_manifest_hash": sha256_file(resolve(args.sample_manifest)),
        "exclusion_manifest": args.exclusion_manifest,
        "exclusion_manifest_hash": sha256_file(resolve(args.exclusion_manifest)),
        "overlay_install_manifest": args.overlay_install_manifest if overlay_path.exists() else None,
        "overlay_install_hash": sha256_file(overlay_path) if overlay_path.exists() else None,
        "osworld_commit": config.get("osworld", {}).get("commit", DEFAULT_OSWORLD_COMMIT),
        "model_id": args.model_id,
        "model_revision": args.model_revision,
        "serving_backend": args.serving_backend,
        "serving_backend_version": args.serving_backend_version,
        "endpoint_redacted": args.endpoint_redacted,
        "decoding": decoding,
        "max_steps": max_steps,
        "retry_policy": config.get("retry_policy", {}),
        "provider": provider,
        "host_or_pod_metadata": {"hostname": socket.gethostname(), "platform": platform.platform()},
        "artifact_roots": config.get("artifact_roots", {}),
    }
    write_json(out, manifest)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
