# syntax=docker/dockerfile:1.7

ARG BASE_IMAGE="vllm/vllm-openai:v0.19.0@sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90"
FROM ${BASE_IMAGE}

ARG BUILD_DATE="unknown"
ARG VCS_REF="unknown"
ARG VLLM_VERSION="0.19.0"

USER root

LABEL org.opencontainers.image.title="OSWorld H200 vLLM OpenAI server" \
      org.opencontainers.image.description="Explicit MLXP custom image for serving LLM/VLM models on H200 reservations with vLLM" \
      org.opencontainers.image.source="https://github.com/pjh6029/os-world-evaluation" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VLLM_VERSION}" \
      ai.snupi.image.role="h200-vllm-serving" \
      ai.snupi.vllm.version="${VLLM_VERSION}"

COPY images/vllm-h200/serve-vllm.sh /usr/local/bin/serve-vllm.sh
RUN chmod 0755 /usr/local/bin/serve-vllm.sh

EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/serve-vllm.sh"]
