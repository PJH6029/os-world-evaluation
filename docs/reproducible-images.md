# Reproducible Images: H200 vLLM Serving + OSWorld Evaluation

This repo owns two public GHCR images:

- `ghcr.io/pjh6029/osworld-vllm-h200:<immutable-tag>`
- `ghcr.io/pjh6029/osworld-eval:<immutable-tag>`

Do not modify `~/code/snupi/mlxp` or MLXP controller configuration for this workflow.

## Canonical tag policy

Use immutable tags:

```text
YYYYMMDD-<git-short-sha>-vllm<version>
```

Example:

```text
20260418-abc1234-vllm0.19.0
```

Do not overwrite tags. Publish a new tag for every change.

## Build and push from the MLXP builder pod

Builder pod:

```bash
kubectl -n p-debug exec -it debug-rsv-jeonghunpark-20260418-7bbfc4 -- bash
```

Inside the pod, copy or clone this repo into a workspace, then authenticate GHCR and build:

```bash
snupi-docker-login   # or ensure gh/crane auth can push ghcr.io/pjh6029
cd /root/work/os-world-evaluation
scripts/images/build_with_buildkit.sh all --push --tag <tag>
```

The script uses:

```text
tcp://buildkitd.p-debug.svc:1234
```

and writes:

```text
artifacts/images/<tag>/image-digests.json
```

## Public image proof

After push, verify public unauthenticated access by digest:

```bash
docker logout ghcr.io || true
docker pull ghcr.io/pjh6029/osworld-vllm-h200@sha256:<digest>
docker pull ghcr.io/pjh6029/osworld-eval@sha256:<digest>
```

or:

```bash
crane manifest ghcr.io/pjh6029/osworld-vllm-h200@sha256:<digest>
crane manifest ghcr.io/pjh6029/osworld-eval@sha256:<digest>
```

## H200 vLLM image usage

Use the serving image as an MLXP explicit custom image. The default foreground process is vLLM OpenAI-compatible serving on port `8000`.

Common env vars:

- `MODEL_ID`, default `Qwen/Qwen3.6-35B-A3B`
- `SERVED_MODEL_NAME`, default `$MODEL_ID`
- `TENSOR_PARALLEL_SIZE`, default auto-detected visible GPU count
- `MAX_MODEL_LEN`, default `32768`
- `GPU_MEMORY_UTILIZATION`, default `0.90`
- `VLLM_EXTRA_ARGS`, default `--generation-config vllm --gdn-prefill-backend triton`
- `HF_HOME`, default prefers `$RESERVATION_NVME_ROOT/cache/huggingface`
- `HF_TOKEN`, passed through without logging

Port-forward example:

```bash
kubectl -n p-debug port-forward pod/<serving-pod> 8000:8000
scripts/images/smoke_vllm_image.sh --endpoint http://127.0.0.1:8000/v1
```

## Local OSWorld evaluation image usage

The local eval image assumes host Docker/KVM and a reachable vLLM endpoint.

Harness-only smoke:

```bash
docker run --rm ghcr.io/pjh6029/osworld-eval:<tag> test
```

Evaluation invocation:

```bash
docker run --rm -it \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --device /dev/kvm \
  -v "$PWD/osworld-work:/workspace" \
  -e OPENAI_BASE_URL=http://host.docker.internal:8000/v1 \
  -e OPENAI_API_KEY=EMPTY \
  -e RUN_ID=qwen36_repro_$(date -u +%Y%m%dT%H%M%SZ) \
  ghcr.io/pjh6029/osworld-eval:<tag> all
```

The image regenerates deterministic sample artifacts, creates and validates a run manifest, runs OSWorld, indexes trajectories, and generates a report.
