# syntax=docker/dockerfile:1

# Python 3.13 with uv preinstalled.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # uv: compile to bytecode for faster startup and copy (not link) from cache
    # so the image is self-contained.
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    # Hugging Face / transformers model cache (mount a volume here to persist
    # downloaded weights across container restarts).
    HF_HOME=/cache/huggingface

WORKDIR /app

# Install dependencies first, using only the lockfile/manifest so this layer is
# cached and reused unless the dependencies actually change. The bind mounts are
# ephemeral; only the resulting virtualenv (UV_PROJECT_ENVIRONMENT) is persisted.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy the application source. This is a uv "virtual" project (no package to
# build/install), so the source runs directly from the venv on PATH.
COPY app ./app

# Put the project's virtualenv on PATH so `uvicorn` resolves directly.
ENV PATH="/app/.venv/bin:$PATH"

# Ensure the transformers cache directory exists.
RUN mkdir -p "$HF_HOME"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
