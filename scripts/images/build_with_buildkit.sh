#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILDKIT_ADDR="${BUILDKIT_ADDR:-tcp://buildkitd.p-debug.svc:1234}"
REGISTRY="${REGISTRY:-ghcr.io/pjh6029}"
TARGET="${1:-}"
PUSH=0
DRY_RUN=0
OUTPUT_OCI=""
TAG=""
VLLM_VERSION="${VLLM_VERSION:-0.19.0}"
OSWORLD_COMMIT="${OSWORLD_COMMIT:-e8ba8fde29889ae7e4377f6f325d736818434a04}"
USE_FALLBACK=0
VLLM_BASE_IMAGE="vllm/vllm-openai:v0.19.0@sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90"
VLLM_FALLBACK_BASE_IMAGE="ghcr.io/pjh6029/snupi-prod-base:cu124-20260414"
EVAL_BASE_IMAGE="python:3.12-slim-bookworm@sha256:d97792894a6a4162cae14da44542a83c75e56c77a27b92d58f3f83b7bc961292"

usage() {
  cat <<'USAGE'
Usage: build_with_buildkit.sh <vllm-h200|osworld-eval|all> [options]

Options:
  --push                 Push to registry
  --dry-run              Print commands only
  --output-oci <dir>     Write OCI tar(s) to directory instead of push
  --tag <tag>            Immutable tag (default: YYYYMMDD-<git-short>-vllm<version>)
  --registry <registry>  Default ghcr.io/pjh6029
  --fallback-vllm-base   Build serving image from Dockerfile.snupi-base-fallback
USAGE
}

die() { echo "$*" >&2; exit 1; }
run_cmd() {
  if [ "$DRY_RUN" -eq 1 ]; then printf '+'; printf ' %q' "$@"; printf '\n'; else "$@"; fi
}

[ -n "$TARGET" ] || { usage; exit 0; }
shift || true
while [ "$#" -gt 0 ]; do
  case "$1" in
    --push) PUSH=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --output-oci) shift; OUTPUT_OCI="${1:?missing output dir}" ;;
    --tag) shift; TAG="${1:?missing tag}" ;;
    --registry) shift; REGISTRY="${1:?missing registry}" ;;
    --fallback-vllm-base) USE_FALLBACK=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
  shift
done
case "$TARGET" in vllm-h200|osworld-eval|all) ;; *) die "unknown target: $TARGET" ;; esac
[ "$PUSH" -eq 1 ] || [ -n "$OUTPUT_OCI" ] || [ "$DRY_RUN" -eq 1 ] || die "choose --push, --output-oci, or --dry-run"

if [ -z "$TAG" ]; then
  short="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo nogit)"
  TAG="$(date -u +%Y%m%d)-${short}-vllm${VLLM_VERSION}"
fi
BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
VCS_REF="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
DIGEST_DIR="$ROOT/artifacts/images/$TAG"
if [ "$DRY_RUN" -eq 1 ] && [ -z "$OUTPUT_OCI" ] && [ "$PUSH" -eq 0 ]; then
  OUTPUT_OCI="$DIGEST_DIR/oci"
fi
mkdir -p "$DIGEST_DIR"
DIGEST_JSON="$DIGEST_DIR/image-digests.json"

ghcr_login() {
  [ "$PUSH" -eq 1 ] || return 0
  [ "${GHCR_SKIP_LOGIN:-0}" != "1" ] || return 0
  if command -v crane >/dev/null 2>&1; then
    user="${GHCR_USERNAME:-PJH6029}"
    if [ -n "${GHCR_TOKEN:-}" ]; then
      printf "%s" "$GHCR_TOKEN" | crane auth login ghcr.io -u "$user" --password-stdin >/dev/null
    elif command -v gh >/dev/null 2>&1; then
      user="${GHCR_USERNAME:-$(gh api user -q .login 2>/dev/null || echo PJH6029)}"
      gh auth token | crane auth login ghcr.io -u "$user" --password-stdin >/dev/null
    fi
  fi
}

build_one() {
  local name="$1"
  local dockerfile="$2"
  local base_image="$3"
  local image="$REGISTRY/$name:$TAG"
  local -a cmd=(buildctl --addr "$BUILDKIT_ADDR" build --frontend dockerfile.v0 --local context="$ROOT" --local dockerfile="$ROOT" --opt platform=linux/amd64 --opt filename="$dockerfile" --opt build-arg:BUILD_DATE="$BUILD_DATE" --opt build-arg:VCS_REF="$VCS_REF" --opt build-arg:VLLM_VERSION="$VLLM_VERSION" --opt build-arg:OSWORLD_COMMIT="$OSWORLD_COMMIT")
  if [ "$PUSH" -eq 1 ]; then
    cmd+=(--output "type=image,name=$image,push=true")
  else
    mkdir -p "$OUTPUT_OCI"
    cmd+=(--output "type=oci,dest=$OUTPUT_OCI/$name-$TAG.oci.tar,name=$image")
  fi
  run_cmd "${cmd[@]}"
  if [ "$DRY_RUN" -eq 0 ] && [ "$PUSH" -eq 1 ] && command -v crane >/dev/null 2>&1; then
    digest="$(crane digest "$image")"
  else
    digest=""
  fi
  printf '%s\t%s\t%s\t%s\t%s\n' "$name" "$image" "$digest" "$dockerfile" "$base_image" >>"$DIGEST_DIR/.images.tsv"
}

ghcr_login
rm -f "$DIGEST_DIR/.images.tsv"
if [ "$TARGET" = vllm-h200 ] || [ "$TARGET" = all ]; then
  df="images/vllm-h200/Dockerfile"
  [ "$USE_FALLBACK" -eq 0 ] || df="images/vllm-h200/Dockerfile.snupi-base-fallback"
  base="$VLLM_BASE_IMAGE"
  [ "$USE_FALLBACK" -eq 0 ] || base="$VLLM_FALLBACK_BASE_IMAGE"
  build_one osworld-vllm-h200 "$df" "$base"
fi
if [ "$TARGET" = osworld-eval ] || [ "$TARGET" = all ]; then
  build_one osworld-eval images/osworld-eval/Dockerfile "$EVAL_BASE_IMAGE"
fi

if [ "$DRY_RUN" -eq 0 ]; then
  python3 - "$DIGEST_DIR/.images.tsv" "$DIGEST_JSON" "$TAG" "$VCS_REF" "$BUILD_DATE" "$VLLM_VERSION" "$OSWORLD_COMMIT" <<'PY'
import json, sys, pathlib
rows=[]
for line in pathlib.Path(sys.argv[1]).read_text().splitlines():
    name, image, digest, dockerfile, base_image = line.split('\t')
    rows.append({"name": name, "image": image, "digest": digest, "digest_ref": f"{image.split(':',1)[0]}@{digest}" if digest else None, "dockerfile": dockerfile, "base_image": base_image})
out={"tag": sys.argv[3], "git_commit": sys.argv[4], "build_timestamp": sys.argv[5], "vllm_version": sys.argv[6], "osworld_commit": sys.argv[7], "images": rows}
pathlib.Path(sys.argv[2]).write_text(json.dumps(out, indent=2, sort_keys=True)+"\n")
print(sys.argv[2])
PY
fi
