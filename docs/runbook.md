# Qwen3.6 OSWorld Evaluation Runbook

This runbook implements `.omx/plans/plan-qwen36-osworld-eval.md`.

## 1. Prepare OSWorld

```bash
python scripts/prepare_osworld.py
python scripts/prepare_osworld.py --check-only
```

The default commit is `e8ba8fde29889ae7e4377f6f325d736818434a04`.

## 2. Sample tasks reproducibly

```bash
python scripts/sample_osworld_tasks.py --seed 36035 --validate-no-gdrive
sha256sum artifacts/manifests/qwen36_osworld_sample_seed36035.json
```

Outputs:
- `artifacts/manifests/qwen36_osworld_sample_seed36035.json`
- `artifacts/manifests/qwen36_osworld_sample_seed36035_meta.json`
- `artifacts/manifests/osworld_google_drive_exclusions.json`

Sampling unit is the official `test_nogdrive.json` domain key; `multi_apps` remains one category.

## 3. Install/verify OSWorld overlays

```bash
python scripts/install_osworld_overlay.py --dry-run
python scripts/install_osworld_overlay.py
python scripts/install_osworld_overlay.py --check-only
```

The installer records provenance and hashes in `artifacts/osworld_overlay_install.json`.

## 4. Serve Qwen3.6

Use the H200 pod if local serving is needed:

```bash
kubectl -n p-debug exec -it debug-rsv-jeonghunpark-20260417-f36863 -- bash
```

Recommended approach: expose an OpenAI-compatible `/v1` endpoint via vLLM first, falling back to SGLang if needed. Record the exact backend command and model revision in `artifacts/runs/<run_id>/run_manifest.json`.

Set endpoint variables on the OSWorld runner host:

```bash
export OPENAI_BASE_URL=http://127.0.0.1:8000/v1
export OPENAI_API_KEY=EMPTY
export QWEN36_MODEL=Qwen/Qwen3.6-35B-A3B
```

## 5. Required smoke gates

Before a full sampled run, pass:
1. Endpoint image+text smoke.
2. Action-format smoke through the Qwen3.6 agent.
3. One-task OSWorld smoke with trajectory artifacts.
4. Forced-failure/resume smoke proving partial files are not deleted.

## 6. Run sampled evaluation

```bash
OSWORLD_HOME=external/OSWorld scripts/run_sample_eval.sh
```

Use conservative `OSWORLD_NUM_ENVS=1` until endpoint and provider stability are proven.

## 7. Index trajectories and report

```bash
python scripts/create_run_manifest.py --run-id <run_id> --serving-backend <vllm-or-sglang> --model-revision <revision>

python scripts/index_trajectories.py \
  --results-dir runs/<run_id> \
  --manifest artifacts/manifests/qwen36_osworld_sample_seed36035.json \
  --run-manifest artifacts/runs/<run_id>/run_manifest.json \
  --validate-contract

python scripts/analyze_failures.py \
  --trajectory-index artifacts/trajectory_index/qwen36_osworld_seed36035.jsonl \
  --out reports/qwen36_osworld_failure_analysis.md \
  --check-report-links
```

## 8. Completion checklist

- Sample manifest hash is reproducible.
- Google Drive exclusion manifest records 8 excluded tasks at the pinned commit.
- Overlay install manifest hashes pass.
- Run manifest validates.
- Every sampled task is attempted or has `not_run_reason`.
- Every attempted task has trajectory/index evidence or absence reasons.
- Report links resolve and marks tags as agent-suggested.


## Reproducible container images

See [`docs/reproducible-images.md`](docs/reproducible-images.md) for the public GHCR H200 vLLM serving image and local OSWorld evaluation image workflow.

From this directory, see [`reproducible-images.md`](reproducible-images.md).
