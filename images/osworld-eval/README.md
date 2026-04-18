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

One/full evaluation:

```bash
docker run --rm -it \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --device /dev/kvm \
  -v "$PWD:$PWD" \
  -w "$PWD" \
  -e EVAL_WORK_ROOT="$PWD/osworld-evaluation" \
  -e OPENAI_BASE_URL=http://host.docker.internal:8000/v1 \
  -e OPENAI_API_KEY=EMPTY \
  -e RUN_ID=qwen36_repro_$(date -u +%Y%m%dT%H%M%SZ) \
  ghcr.io/pjh6029/osworld-eval:<tag> all
```
