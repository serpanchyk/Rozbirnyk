# --- Stage 1: Build ---
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

COPY pyproject.toml uv.lock ./
COPY packages/common/pyproject.toml ./packages/common/pyproject.toml
COPY packages/common/src ./packages/common/src
COPY apps/agent_service/pyproject.toml ./apps/agent_service/pyproject.toml
COPY apps/agent_service/src ./apps/agent_service/src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --package rozbirnyk_agent_service

# --- Stage 2: Runtime ---
FROM python:3.12-slim-bookworm

WORKDIR /app

COPY --from=builder /opt/venv /app/.venv

COPY apps/agent_service/src ./src
COPY apps/agent_service/config.toml ./config.toml

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

CMD ["python", "-m", "agent_service.main"]
