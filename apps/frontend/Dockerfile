# --- Stage 1: Build ---
FROM astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

RUN --mount=type=bind,source=.,target=/app \
    uv sync --frozen --no-dev --no-editable --package rozbirnyk_frontend

# --- Stage 2: Runtime ---
FROM python:3.12-slim-bookworm

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

COPY apps/frontend/src ./src
COPY apps/frontend/config.toml ./config.toml

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

CMD ["streamlit", "run", "src/frontend/main.py"]
