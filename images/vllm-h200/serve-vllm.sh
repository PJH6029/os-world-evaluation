#!/usr/bin/env bash
set -euo pipefail

log() { printf '[serve-vllm] %s\n' "$*" >&2; }

MODEL_ID="${MODEL_ID:-Qwen/Qwen3.6-35B-A3B}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-$MODEL_ID}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
DTYPE="${DTYPE:-auto}"
TRUST_REMOTE_CODE="${TRUST_REMOTE_CODE:-1}"
VLLM_EXTRA_ARGS="${VLLM_EXTRA_ARGS:---generation-config vllm --gdn-prefill-backend triton}"

if [ -z "${HF_HOME:-}" ]; then
  if [ -n "${RESERVATION_NVME_ROOT:-}" ] && [ -d "${RESERVATION_NVME_ROOT}" ]; then
    export HF_HOME="${RESERVATION_NVME_ROOT}/cache/huggingface"
  elif [ -n "${RESERVATION_DDN_PERSONAL_DIR:-}" ] && [ -d "${RESERVATION_DDN_PERSONAL_DIR}" ]; then
    export HF_HOME="${RESERVATION_DDN_PERSONAL_DIR}/.cache/huggingface"
  else
    export HF_HOME="/root/.cache/huggingface"
  fi
fi
mkdir -p "${HF_HOME}" || { log "ERROR: HF_HOME is not writable: ${HF_HOME}"; exit 2; }
# HF_TOKEN/HUGGING_FACE_HUB_TOKEN are intentionally passed through to vLLM/Hugging Face libraries,
# but this script never prints their values.
if [ -n "${HF_TOKEN:-}" ] && [ -z "${HUGGING_FACE_HUB_TOKEN:-}" ]; then
  export HUGGING_FACE_HUB_TOKEN="${HF_TOKEN}"
fi

visible_gpus=0
if command -v nvidia-smi >/dev/null 2>&1; then
  visible_gpus="$(nvidia-smi -L 2>/dev/null | grep -c '^GPU ' || true)"
elif [ -d /proc/driver/nvidia/gpus ]; then
  visible_gpus="$(find /proc/driver/nvidia/gpus -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')"
fi
if [ "${visible_gpus}" = "0" ]; then
  log "WARNING: no NVIDIA GPUs detected; vLLM will likely fail unless GPU devices are mounted"
  visible_gpus=1
fi

if [ -z "${TENSOR_PARALLEL_SIZE:-}" ] || [ "${TENSOR_PARALLEL_SIZE:-auto}" = "auto" ]; then
  TENSOR_PARALLEL_SIZE="${visible_gpus}"
fi
if ! [[ "${TENSOR_PARALLEL_SIZE}" =~ ^[0-9]+$ ]] || [ "${TENSOR_PARALLEL_SIZE}" -lt 1 ]; then
  log "ERROR: TENSOR_PARALLEL_SIZE must be a positive integer, got '${TENSOR_PARALLEL_SIZE}'"
  exit 2
fi
if [ "${TENSOR_PARALLEL_SIZE}" -gt "${visible_gpus}" ]; then
  log "ERROR: TENSOR_PARALLEL_SIZE=${TENSOR_PARALLEL_SIZE} exceeds visible GPU count=${visible_gpus}"
  exit 2
fi

shm_mb="$(df -Pm /dev/shm 2>/dev/null | awk 'NR==2 {print $2}' || echo 0)"
if [ "${shm_mb:-0}" -lt 1024 ]; then
  log "WARNING: /dev/shm appears small (${shm_mb:-0} MiB). vLLM Docker deployments often need --ipc=host or larger shared memory."
fi

vllm_version="$(python - <<'PY' 2>/dev/null || true
try:
    import vllm
    print(getattr(vllm, '__version__', 'unknown'))
except Exception:
    print('unknown')
PY
)"

log "vllm_version=${vllm_version}"
log "model_id=${MODEL_ID} served_model_name=${SERVED_MODEL_NAME} host=${HOST} port=${PORT}"
log "visible_gpus=${visible_gpus} tensor_parallel_size=${TENSOR_PARALLEL_SIZE} max_model_len=${MAX_MODEL_LEN} dtype=${DTYPE} gpu_memory_utilization=${GPU_MEMORY_UTILIZATION}"
log "hf_home=${HF_HOME} shm_mb=${shm_mb:-unknown}"
log "extra_args=${VLLM_EXTRA_ARGS}"

args=(
  serve "${MODEL_ID}"
  --host "${HOST}"
  --port "${PORT}"
  --served-model-name "${SERVED_MODEL_NAME}"
  --tensor-parallel-size "${TENSOR_PARALLEL_SIZE}"
  --max-model-len "${MAX_MODEL_LEN}"
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION}"
  --dtype "${DTYPE}"
)
if [ "${TRUST_REMOTE_CODE}" = "1" ] || [ "${TRUST_REMOTE_CODE}" = "true" ]; then
  args+=(--trust-remote-code)
fi
if [ -n "${VLLM_EXTRA_ARGS}" ]; then
  # Intentionally shell-split user-provided vLLM arguments; this is an explicit custom-image contract.
  # shellcheck disable=SC2206
  extra_args=( ${VLLM_EXTRA_ARGS} )
  args+=("${extra_args[@]}")
fi

exec vllm "${args[@]}" "$@"
