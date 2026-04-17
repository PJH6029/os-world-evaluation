# OSWorld H200 vLLM Serving Image

Public image target: `ghcr.io/pjh6029/osworld-vllm-h200:<immutable-tag>`.

This is an MLXP explicit custom image. It does not provide managed shell/Jupyter UX. The foreground process is vLLM's OpenAI-compatible server on port `8000`.

## Runtime contract

Common env vars:

- `MODEL_ID` default `Qwen/Qwen3.6-35B-A3B`
- `SERVED_MODEL_NAME` default `$MODEL_ID`
- `HOST` default `0.0.0.0`
- `PORT` default `8000`
- `TENSOR_PARALLEL_SIZE` default `auto` from visible GPUs
- `MAX_MODEL_LEN` default `32768`
- `GPU_MEMORY_UTILIZATION` default `0.90`
- `DTYPE` default `auto`
- `TRUST_REMOTE_CODE` default `1`
- `VLLM_EXTRA_ARGS` default `--generation-config vllm --gdn-prefill-backend triton`
- `HF_HOME` default prefers `$RESERVATION_NVME_ROOT/cache/huggingface`
- `HF_TOKEN` is passed through but never printed

For an 8-H200 reservation, set `TENSOR_PARALLEL_SIZE=8` or leave it unset if all eight GPUs are visible.

## Smoke

After reservation is running:

```bash
kubectl -n p-debug port-forward pod/<pod-name> 8000:8000
curl http://127.0.0.1:8000/v1/models
```

Then run `scripts/images/smoke_vllm_image.sh --endpoint http://127.0.0.1:8000/v1` from this repo.
