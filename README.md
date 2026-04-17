# Qwen3.6 OSWorld Qualitative Evaluation

This repository contains a reproducible harness for evaluating `Qwen/Qwen3.6-35B-A3B` on a sampled OSWorld subset and producing trajectory-backed qualitative failure analysis.

The goal is **failure analysis**, not a full OSWorld leaderboard submission. The analysis focuses on:

1. bad visual perception,
2. bad action grounding,
3. planning errors,
4. tool/UI confusion.

## Key design

- Official OSWorld is a pinned external checkout, not vendored source.
- Sampling uses official `evaluation_examples/test_nogdrive.json` and selects up to 5 tasks per domain with seed `36035`.
- Google Drive exclusions are recorded explicitly from `test_all.json - test_nogdrive.json`.
- Qwen3.6 is consumed through an OpenAI-compatible multimodal endpoint.
- Trajectories preserve initial observations, screenshots, raw model outputs, parsed actions, errors, and absence reasons.

## Quickstart

```bash
python scripts/prepare_osworld.py
python scripts/sample_osworld_tasks.py --seed 36035 --validate-no-gdrive
python scripts/install_osworld_overlay.py --dry-run
python scripts/install_osworld_overlay.py
```

Then serve Qwen3.6 through an OpenAI-compatible endpoint and run:

```bash
export OPENAI_BASE_URL=http://127.0.0.1:8000/v1
export OPENAI_API_KEY=EMPTY
export QWEN36_MODEL=Qwen/Qwen3.6-35B-A3B
OSWORLD_HOME=external/OSWorld scripts/run_sample_eval.sh
```

See `docs/runbook.md` for the full smoke-test and verification workflow.

## Important artifacts

- `config/eval.json` — canonical configuration.
- `scripts/sample_osworld_tasks.py` — deterministic sampler and Google Drive exclusion recorder.
- `scripts/install_osworld_overlay.py` — auditable overlay installer.
- `overlays/osworld/` — Qwen3.6 OSWorld agent/runner overlay.
- `scripts/create_run_manifest.py` — canonical run manifest generator.
- `scripts/index_trajectories.py` — trajectory indexer and contract validator.
- `scripts/analyze_failures.py` — qualitative report generator.
- `docs/failure_taxonomy.md` — coding taxonomy.
- `docs/runbook.md` — operational runbook.

## Local verification

```bash
python -m compileall scripts overlays tests
python -m unittest discover -s tests -v
```

If `/tmp/osworld-official` exists or `external/OSWorld` has been prepared, run sampler smoke checks:

```bash
python scripts/sample_osworld_tasks.py --osworld-home /tmp/osworld-official --seed 36035 --validate-no-gdrive
python scripts/sample_osworld_tasks.py --osworld-home /tmp/osworld-official --seed 36035 --validate-no-gdrive
sha256sum artifacts/manifests/qwen36_osworld_sample_seed36035.json
```
