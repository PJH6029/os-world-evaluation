#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OSWORLD_HOME="${OSWORLD_HOME:-$ROOT/external/OSWorld}"
RUN_ID="${RUN_ID:-qwen36_osworld_seed36035_$(date -u +%Y%m%dT%H%M%SZ)}"
RESULT_DIR="${RESULT_DIR:-$ROOT/runs/$RUN_ID}"
SAMPLE_META="${SAMPLE_META:-$ROOT/artifacts/manifests/qwen36_osworld_sample_seed36035_meta.json}"

if [[ ! -d "$OSWORLD_HOME" ]]; then
  echo "OSWorld checkout missing: $OSWORLD_HOME" >&2
  echo "Run: python scripts/prepare_osworld.py" >&2
  exit 1
fi

python3 "$ROOT/scripts/install_osworld_overlay.py" --osworld-home "$OSWORLD_HOME" --check-only || \
  python3 "$ROOT/scripts/install_osworld_overlay.py" --osworld-home "$OSWORLD_HOME"

cd "$OSWORLD_HOME"
# Prefer CUDA runtime libraries bundled in the OSWorld uv environment when present;
# this avoids host-library mismatches when torch/easyocr import CUDA wheels.
if [[ -d ".venv/lib/python3.12/site-packages/nvidia/nvjitlink/lib" ]]; then
  export LD_LIBRARY_PATH="$PWD/.venv/lib/python3.12/site-packages/nvidia/nvjitlink/lib:$PWD/.venv/lib/python3.12/site-packages/nvidia/cusparse/lib:$PWD/.venv/lib/python3.12/site-packages/nvidia/cublas/lib:$PWD/.venv/lib/python3.12/site-packages/nvidia/cuda_runtime/lib:${LD_LIBRARY_PATH:-}"
fi
export OPENAI_API_KEY="${OPENAI_API_KEY:-EMPTY}"
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-http://127.0.0.1:8000/v1}"
export QWEN36_MODEL="${QWEN36_MODEL:-Qwen/Qwen3.6-35B-A3B}"
PYTHON_BIN="${PYTHON_BIN:-$OSWORLD_HOME/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi

"$PYTHON_BIN" scripts/python/run_multienv_qwen36.py \
  --provider_name "${OSWORLD_PROVIDER:-docker}" \
  --headless \
  --observation_type screenshot \
  --action_space pyautogui \
  --model "$QWEN36_MODEL" \
  --temperature "${QWEN36_TEMPERATURE:-0}" \
  --top_p "${QWEN36_TOP_P:-0.9}" \
  --max_tokens "${QWEN36_MAX_TOKENS:-32768}" \
  --sleep_after_execution "${OSWORLD_SLEEP_AFTER_EXECUTION:-3}" \
  --max_steps "${OSWORLD_MAX_STEPS:-15}" \
  --num_envs "${OSWORLD_NUM_ENVS:-1}" \
  --client_password "${OSWORLD_CLIENT_PASSWORD:-password}" \
  --test_all_meta_path "$SAMPLE_META" \
  --result_dir "$RESULT_DIR"
