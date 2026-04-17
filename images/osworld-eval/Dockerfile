# syntax=docker/dockerfile:1.7

FROM docker:28-cli AS docker-cli

FROM python:3.12-slim-bookworm

ARG BUILD_DATE="unknown"
ARG VCS_REF="unknown"
ARG OSWORLD_REPO="https://github.com/xlang-ai/OSWorld.git"
ARG OSWORLD_COMMIT="e8ba8fde29889ae7e4377f6f325d736818434a04"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OSWORLD_HOME=/opt/OSWorld \
    EVAL_SOURCE_ROOT=/opt/osworld-evaluation \
    EVAL_WORK_ROOT=/workspace/osworld-evaluation \
    UV_NO_CACHE=1

LABEL org.opencontainers.image.title="OSWorld evaluation harness" \
      org.opencontainers.image.description="Local OSWorld evaluation image for running sampled OSWorld tasks against a reserved vLLM endpoint" \
      org.opencontainers.image.source="https://github.com/pjh6029/os-world-evaluation" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      ai.snupi.image.role="osworld-eval" \
      ai.snupi.osworld.commit="${OSWORLD_COMMIT}"

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      bash ca-certificates curl git jq less procps rsync unzip zip wget build-essential \
      libasound2 libatk-bridge2.0-0 libatk1.0-0 libcairo2 libcups2 libdbus-1-3 \
      libdrm2 libgbm1 libglib2.0-0 libgtk-3-0 libnss3 libpango-1.0-0 \
      libx11-6 libxcomposite1 libxdamage1 libxext6 libxfixes3 libxkbcommon0 \
      libxrandr2 libxrender1 libxss1 libxtst6 libgl1 openssh-client \
 && rm -rf /var/lib/apt/lists/* \
 && UV_INSTALL_DIR=/usr/local/bin UV_NO_MODIFY_PATH=1 sh -c "$(curl -LsSf https://astral.sh/uv/install.sh)"

COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker

RUN git clone "${OSWORLD_REPO}" "${OSWORLD_HOME}" \
 && cd "${OSWORLD_HOME}" \
 && git checkout "${OSWORLD_COMMIT}" \
 && uv sync --no-dev --frozen

WORKDIR /opt/osworld-evaluation
COPY . /opt/osworld-evaluation
COPY images/osworld-eval/run-osworld-eval.sh /usr/local/bin/run-osworld-eval.sh
RUN chmod 0755 /usr/local/bin/run-osworld-eval.sh

ENTRYPOINT ["/usr/local/bin/run-osworld-eval.sh"]
CMD ["help"]
