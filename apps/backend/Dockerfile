# --- Stage 1: Build ---
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

RUN --mount=type=bind,source=.,target=/app \
    uv sync --frozen --no-dev --no-editable --package rozbirnyk_backend

# --- Stage 2: Runtime ---
FROM python:3.12-slim-bookworm

WORKDIR /app

COPY --from=builder /opt/venv /app/.venv

COPY apps/backend/src ./src
COPY apps/backend/config.toml ./config.toml

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

CMD ["python", "-m", "backend.main"]
