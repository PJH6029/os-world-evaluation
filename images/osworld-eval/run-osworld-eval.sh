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
  smoke-one Generate a one-task meta file, then eval + report for that one task
  all       test + eval + report

Required for eval/all/smoke-one:
  OPENAI_BASE_URL=http://host:port/v1
  OPENAI_API_KEY=EMPTY  # default is EMPTY

Host requirements for eval/all/smoke-one:
  - Docker socket mounted at /var/run/docker.sock
  - /dev/kvm mounted when using OSWorld Docker provider with KVM acceleration
USAGE
}

SOURCE_ROOT="${EVAL_SOURCE_ROOT:-/opt/osworld-evaluation}"
WORK_ROOT="${EVAL_WORK_ROOT:-/workspace/osworld-evaluation}"
BUNDLED_OSWORLD_HOME="${BUNDLED_OSWORLD_HOME:-/opt/OSWorld}"
OSWORLD_HOME="${OSWORLD_HOME:-$WORK_ROOT/external/OSWorld}"
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

ensure_osworld_home() {
  if [ -x "${OSWORLD_HOME}/.venv/bin/python" ] && [ -f "${OSWORLD_HOME}/evaluation_examples/test_nogdrive.json" ]; then
    return 0
  fi
  if [ ! -d "${BUNDLED_OSWORLD_HOME}" ]; then
    log "ERROR: bundled OSWorld checkout missing: ${BUNDLED_OSWORLD_HOME}"
    exit 2
  fi
  log "Preparing host-visible OSWorld checkout at ${OSWORLD_HOME} from ${BUNDLED_OSWORLD_HOME}"
  mkdir -p "$(dirname "${OSWORLD_HOME}")"
  rsync -a --delete "${BUNDLED_OSWORLD_HOME}/" "${OSWORLD_HOME}/"
}

check_endpoint() {
  if [ -z "${OPENAI_BASE_URL:-}" ]; then
    log "ERROR: OPENAI_BASE_URL is required for eval/all/smoke-one"
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
  mkdir -p "${WORK_ROOT}"
  local sentinel="${WORK_ROOT}/.host-visible-sentinel"
  printf 'host-visible-check\n' >"${sentinel}"
  if ! docker run --rm -v "${WORK_ROOT}:${WORK_ROOT}:ro" busybox:1.36.1 test -f "${sentinel}" >/dev/null 2>&1; then
    log "ERROR: WORK_ROOT=${WORK_ROOT} is not visible to the host Docker daemon at the same absolute path."
    log "Mount your workdir at the same path, e.g. -v "$PWD:$PWD" -e EVAL_WORK_ROOT="$PWD/osworld-evaluation", not -v "$PWD:/workspace"."
    exit 2
  fi
}

set_cuda_library_path() {
  if [ -d "${OSWORLD_HOME}/.venv/lib/python3.12/site-packages/nvidia/nvjitlink/lib" ]; then
    export LD_LIBRARY_PATH="${OSWORLD_HOME}/.venv/lib/python3.12/site-packages/nvidia/nvjitlink/lib:${OSWORLD_HOME}/.venv/lib/python3.12/site-packages/nvidia/cusparse/lib:${OSWORLD_HOME}/.venv/lib/python3.12/site-packages/nvidia/cublas/lib:${OSWORLD_HOME}/.venv/lib/python3.12/site-packages/nvidia/cuda_runtime/lib:${LD_LIBRARY_PATH:-}"
  fi
}

sample_with_osworld_home() {
  local sample_home="$1"
  python3 scripts/sample_osworld_tasks.py --osworld-home "${sample_home}" --seed 36035 --validate-no-gdrive
}

run_tests() {
  prepare_workdir
  python3 -m compileall scripts overlays tests
  python3 -m unittest discover -s tests -v
  sample_with_osworld_home "${BUNDLED_OSWORLD_HOME}"
}

run_sample() {
  prepare_workdir
  sample_with_osworld_home "${BUNDLED_OSWORLD_HOME}"
}


ensure_docker_vm_image() {
  if [ "${OSWORLD_PROVIDER:-docker}" != "docker" ]; then
    return 0
  fi
  ensure_osworld_home
  local vm_dir="${OSWORLD_HOME}/docker_vm_data"
  local zip_path="${vm_dir}/Ubuntu.qcow2.zip"
  local qcow_path="${vm_dir}/Ubuntu.qcow2"
  mkdir -p "${vm_dir}"
  if [ -f "${zip_path}" ] && [ ! -f "${qcow_path}" ]; then
    if ! "${OSWORLD_HOME}/.venv/bin/python" - <<PYZIP
import sys, zipfile
path = "${zip_path}"
try:
    with zipfile.ZipFile(path) as zf:
        bad = zf.testzip()
except Exception:
    sys.exit(1)
sys.exit(0 if bad is None else 1)
PYZIP
    then
      log "Removing corrupt/incomplete OSWorld VM archive: ${zip_path}"
      rm -f "${zip_path}"
    fi
  fi
  log "Ensuring OSWorld Docker VM image exists at host-visible path ${vm_dir}"
  (cd "${OSWORLD_HOME}" && "${OSWORLD_HOME}/.venv/bin/python" - <<'PYVM'
from desktop_env.providers.docker.manager import DockerVMManager
path = DockerVMManager().get_vm_path("Ubuntu", "us-east-1")
print(path)
PYVM
  )
}

run_eval() {
  prepare_workdir
  check_endpoint
  check_docker_runtime
  ensure_osworld_home
  set_cuda_library_path
  python3 scripts/install_osworld_overlay.py --osworld-home "${OSWORLD_HOME}" --check-only || python3 scripts/install_osworld_overlay.py --osworld-home "${OSWORLD_HOME}" --force-managed
  ensure_docker_vm_image
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
  local sample_meta="${OSWORLD_SAMPLE_META:-${WORK_ROOT}/artifacts/manifests/qwen36_osworld_sample_seed36035_meta.json}"
  export QWEN36_MAX_TOKENS="${QWEN36_MAX_TOKENS:-2048}"
  OSWORLD_HOME="${OSWORLD_HOME}" \
  RUN_ID="${RUN_ID}" \
  RESULT_DIR="${WORK_ROOT}/runs/${RUN_ID}" \
  SAMPLE_META="${sample_meta}" \
  PYTHON_BIN="${OSWORLD_HOME}/.venv/bin/python" \
  OPENAI_BASE_URL="${OPENAI_BASE_URL}" \
  OPENAI_API_KEY="${OPENAI_API_KEY}" \
  QWEN36_MODEL="${QWEN36_MODEL}" \
  bash scripts/run_sample_eval.sh
}

run_report() {
  prepare_workdir
  python3 scripts/validate_run_manifest.py --run-manifest "artifacts/runs/${RUN_ID}/run_manifest.json"
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

run_smoke_one() {
  run_sample
  python3 - <<'PY'
import json, pathlib
meta = json.loads(pathlib.Path('artifacts/manifests/qwen36_osworld_sample_seed36035_meta.json').read_text())
domain = sorted(meta)[0]
out = {domain: [meta[domain][0]]}
path = pathlib.Path('artifacts/manifests/qwen36_osworld_smoke_meta.json')
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
print(path)
PY
  OSWORLD_SAMPLE_META="${WORK_ROOT}/artifacts/manifests/qwen36_osworld_smoke_meta.json" run_eval
  run_report
}

cmd="${1:-help}"
case "${cmd}" in
  help|-h|--help) usage ;;
  test) run_tests ;;
  sample) run_sample ;;
  eval) run_sample; run_eval ;;
  report) run_report ;;
  smoke-one) run_smoke_one ;;
  all) run_tests; run_eval; run_report ;;
  *) log "ERROR: unknown command: ${cmd}"; usage; exit 2 ;;
esac
