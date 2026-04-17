#!/usr/bin/env bash
set -euo pipefail
IMAGE=""
ENDPOINT="${OPENAI_BASE_URL:-}"
RUN_ONE=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --image) shift; IMAGE="$1" ;;
    --openai-base-url) shift; ENDPOINT="$1" ;;
    --run-one-task) RUN_ONE=1 ;;
    -h|--help) echo "Usage: $0 --image REF [--openai-base-url URL] [--run-one-task]"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
  shift
done
[ -n "$IMAGE" ] || { echo "--image is required" >&2; exit 2; }
cmd=(docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD/.image-smoke-work:/workspace")
[ ! -e /dev/kvm ] || cmd+=(--device /dev/kvm)
[ -z "$ENDPOINT" ] || cmd+=(-e "OPENAI_BASE_URL=$ENDPOINT" -e OPENAI_API_KEY=EMPTY)
cmd+=("$IMAGE")
if [ "$RUN_ONE" -eq 1 ]; then
  cmd+=(all)
else
  cmd+=(test)
fi
printf '+'; printf ' %q' "${cmd[@]}"; printf '\n'
"${cmd[@]}"
