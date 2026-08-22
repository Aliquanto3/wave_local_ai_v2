# syntax=docker/dockerfile:1

# --- Stage: llama-fetch ---
# Fetches and verifies the pinned CPU llama-server release, the same tag and
# checksum trust model docs/setup.md documents for a bare-metal install.
FROM python:3.12-slim AS llama-fetch

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ARG LLAMA_CPP_TAG=b10537
ARG LLAMA_SERVER_ASSET=llama-b10537-bin-ubuntu-x64.tar.gz
ARG LLAMA_SERVER_SHA256=47963587b8e2eee2ecc2ac0884450b2f50c24b35bcff23d68c92694da1d1ac0f

RUN curl -fsSL -o /tmp/llama.tar.gz "https://github.com/ggml-org/llama.cpp/releases/download/${LLAMA_CPP_TAG}/${LLAMA_SERVER_ASSET}" \
    && echo "${LLAMA_SERVER_SHA256}  /tmp/llama.tar.gz" | sha256sum -c - \
    && mkdir -p /opt/llama-cpp \
    && tar -xzf /tmp/llama.tar.gz -C /opt/llama-cpp --strip-components=1 \
    && rm /tmp/llama.tar.gz

# --- Stage: project-build ---
# Installs the project from the locked deps into a self-contained venv, no
# dev dependencies, no editable install (so it survives without src/ present).
FROM python:3.12-slim AS project-build

COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src/ src/

RUN uv sync --locked --no-dev --no-editable

# --- Stage: runtime ---
# Only the installed venv and the fetched llama-server runtime cross into the
# final image: no compiler, no curl, no .git, no source tree.
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system app && useradd --system --gid app --create-home --home-dir /home/app app

COPY --from=llama-fetch /opt/llama-cpp /opt/llama-cpp
ENV PATH="/opt/llama-cpp:/app/.venv/bin:${PATH}" \
    LD_LIBRARY_PATH="/opt/llama-cpp"

COPY --from=project-build /app/.venv /app/.venv

WORKDIR /app
RUN chown -R app:app /app /home/app

ARG SOURCE
ARG REVISION
ENV WAVE_BUILD_SHA="${REVISION}"
LABEL org.opencontainers.image.source="${SOURCE}" \
      org.opencontainers.image.revision="${REVISION}"

USER app

ENTRYPOINT ["wave-local-ai-v2"]
