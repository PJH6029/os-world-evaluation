#!/usr/bin/env bash
set -euo pipefail

log() { printf '[osworld-eval] %s\n' "$*" >&2; }
usage() {
  cat <<'USAGE'
Usage: run-osworld-eval.sh <command>

Commands:
  help      Show this help
  test      Copy harness to EVAL_WORK_ROOT and run unit tests + deterministic sampling
  sample    Generate deterministic OSWorld sample manifests
  eval      Run OSWorld sampled evaluation against OPENAI_BASE_URL
  report    Validate run manifest, index trajectories, and generate report
  all       test + eval + report

Required for eval/all:
  OPENAI_BASE_URL=http://host:port/v1
  OPENAI_API_KEY=EMPTY  # default is EMPTY

Host requirements for eval/all:
  - Docker socket mounted at /var/run/docker.sock
  - /dev/kvm mounted when using OSWorld Docker provider with KVM acceleration
USAGE
}

SOURCE_ROOT="${EVAL_SOURCE_ROOT:-/opt/osworld-evaluation}"
WORK_ROOT="${EVAL_WORK_ROOT:-/workspace/osworld-evaluation}"
OSWORLD_HOME="${OSWORLD_HOME:-/opt/OSWorld}"
RUN_ID="${RUN_ID:-qwen36_osworld_seed36035_$(date -u +%Y%m%dT%H%M%SZ)}"
OPENAI_API_KEY="${OPENAI_API_KEY:-EMPTY}"
QWEN36_MODEL="${QWEN36_MODEL:-Qwen/Qwen3.6-35B-A3B}"

prepare_workdir() {
  mkdir -p "${WORK_ROOT}"
  rsync -a --delete \
    --exclude '.git/' --exclude '.omx/' --exclude 'external/' --exclude 'runs/' \
    --exclude '.cache/' --exclude '__pycache__/' --exclude '.pytest_cache/' \
    "${SOURCE_ROOT}/" "${WORK_ROOT}/"
  cd "${WORK_ROOT}"
}

check_endpoint() {
  if [ -z "${OPENAI_BASE_URL:-}" ]; then
    log "ERROR: OPENAI_BASE_URL is required for eval/all"
    exit 2
  fi
  export OPENAI_API_KEY OPENAI_BASE_URL QWEN36_MODEL
}

check_docker_runtime() {
  if [ ! -S /var/run/docker.sock ]; then
    log "ERROR: /var/run/docker.sock is not mounted; run with -v /var/run/docker.sock:/var/run/docker.sock"
    exit 2
  fi
  if ! docker info >/dev/null 2>&1; then
    log "ERROR: docker CLI cannot reach host Docker daemon"
    exit 2
  fi
  if [ ! -e /dev/kvm ]; then
    log "WARNING: /dev/kvm is absent; OSWorld Docker provider may be slow or fail without KVM"
  fi
}

set_cuda_library_path() {
  if [ -d "${OSWORLD_HOME}/.venv/lib/python3.12/site-packages/nvidia/nvjitlink/lib" ]; then
    export LD_LIBRARY_PATH="${OSWORLD_HOME}/.venv/lib/python3.12/site-packages/nvidia/nvjitlink/lib:${OSWORLD_HOME}/.venv/lib/python3.12/site-packages/nvidia/cusparse/lib:${OSWORLD_HOME}/.venv/lib/python3.12/site-packages/nvidia/cublas/lib:${OSWORLD_HOME}/.venv/lib/python3.12/site-packages/nvidia/cuda_runtime/lib:${LD_LIBRARY_PATH:-}"
  fi
}

run_tests() {
  prepare_workdir
  set_cuda_library_path
  python3 -m compileall scripts overlays tests
  python3 -m unittest discover -s tests -v
  python3 scripts/sample_osworld_tasks.py --osworld-home "${OSWORLD_HOME}" --seed 36035 --validate-no-gdrive
}

run_sample() {
  prepare_workdir
  python3 scripts/sample_osworld_tasks.py --osworld-home "${OSWORLD_HOME}" --seed 36035 --validate-no-gdrive
}

run_eval() {
  prepare_workdir
  check_endpoint
  check_docker_runtime
  set_cuda_library_path
  python3 scripts/install_osworld_overlay.py --osworld-home "${OSWORLD_HOME}" --check-only || python3 scripts/install_osworld_overlay.py --osworld-home "${OSWORLD_HOME}" --force-managed
  python3 scripts/create_run_manifest.py \
    --run-id "${RUN_ID}" \
    --serving-backend "${SERVING_BACKEND:-vllm}" \
    --serving-backend-version "${SERVING_BACKEND_VERSION:-unknown}" \
    --model-revision "${MODEL_REVISION:-unknown}" \
    --endpoint-redacted "${OPENAI_BASE_URL}" \
    --temperature "${QWEN36_TEMPERATURE:-0}" \
    --top-p "${QWEN36_TOP_P:-0.9}" \
    --max-tokens "${QWEN36_MAX_TOKENS:-2048}" \
    --max-steps "${OSWORLD_MAX_STEPS:-15}" \
    --num-envs "${OSWORLD_NUM_ENVS:-1}"
  OSWORLD_HOME="${OSWORLD_HOME}" \
  RUN_ID="${RUN_ID}" \
  RESULT_DIR="${WORK_ROOT}/runs/${RUN_ID}" \
  SAMPLE_META="${WORK_ROOT}/artifacts/manifests/qwen36_osworld_sample_seed36035_meta.json" \
  PYTHON_BIN="${OSWORLD_HOME}/.venv/bin/python" \
  OPENAI_BASE_URL="${OPENAI_BASE_URL}" \
  OPENAI_API_KEY="${OPENAI_API_KEY}" \
  QWEN36_MODEL="${QWEN36_MODEL}" \
  bash scripts/run_sample_eval.sh
}

run_report() {
  prepare_workdir
  RUN_ID="${RUN_ID}" python3 scripts/validate_run_manifest.py --run-manifest "artifacts/runs/${RUN_ID}/run_manifest.json"
  python3 scripts/index_trajectories.py \
    --results-dir "runs/${RUN_ID}" \
    --manifest artifacts/manifests/qwen36_osworld_sample_seed36035.json \
    --run-manifest "artifacts/runs/${RUN_ID}/run_manifest.json" \
    --out artifacts/trajectory_index/qwen36_osworld_seed36035.jsonl \
    --validate-contract
  python3 scripts/analyze_failures.py \
    --trajectory-index artifacts/trajectory_index/qwen36_osworld_seed36035.jsonl \
    --out reports/qwen36_osworld_failure_analysis.md \
    --check-report-links
}

cmd="${1:-help}"
case "${cmd}" in
  help|-h|--help) usage ;;
  test) run_tests ;;
  sample) run_sample ;;
  eval) run_sample; run_eval ;;
  report) run_report ;;
  all) run_tests; run_eval; run_report ;;
  *) log "ERROR: unknown command: ${cmd}"; usage; exit 2 ;;
esac
