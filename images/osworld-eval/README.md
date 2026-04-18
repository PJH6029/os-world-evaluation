# OSWorld Evaluation Image

Public image target: `ghcr.io/pjh6029/osworld-eval:<immutable-tag>`.

This image packages Python 3.12, OSWorld at the pinned commit, and this repo's evaluation harness. It assumes a vLLM endpoint is already reachable.

## Host requirements for evaluation

- Docker Engine with `/var/run/docker.sock` mounted into the container.
- `/dev/kvm` mounted for accelerated OSWorld Docker provider when available.
- Enough disk for OSWorld VM/cache and run artifacts.
- `OPENAI_BASE_URL` pointing to the reserved serving pod, often via `kubectl port-forward`.

## Examples

Harness-only smoke:

```bash
docker run --rm ghcr.io/pjh6029/osworld-eval:<tag> test
```

One/full evaluation on Linux with `kubectl port-forward ... 8000:8000` already
running:

```bash
EVAL_IMAGE='ghcr.io/pjh6029/osworld-eval@sha256:cb9467e8116b240fdbb2b8d88f5d1d1966c51f100d9623ad1ecf099ae7b799ba'
RUN_ID="qwen36_repro_$(date -u +%Y%m%dT%H%M%SZ)"

docker run --rm -it \
  --network host \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --device /dev/kvm \
  -v "$PWD:$PWD" \
  -w "$PWD" \
  -e EVAL_WORK_ROOT="$PWD/osworld-evaluation" \
  -e OSWORLD_HOME="$PWD/osworld-evaluation/external/OSWorld" \
  -e OPENAI_BASE_URL=http://127.0.0.1:8000/v1 \
  -e OPENAI_API_KEY=EMPTY \
  -e QWEN36_MODEL=Qwen/Qwen3.6-35B-A3B \
  -e RUN_ID="$RUN_ID" \
  -e OSWORLD_NUM_ENVS=4 \
  -e OSWORLD_MAX_STEPS=15 \
  -e OSWORLD_SLEEP_AFTER_EXECUTION=3 \
  "$EVAL_IMAGE" all
```

Use the same absolute-path bind (`-v "$PWD:$PWD"`) rather than mapping the repo
to `/workspace`; OSWorld's Docker provider creates nested containers through the
host Docker daemon, so host-visible paths must match.
