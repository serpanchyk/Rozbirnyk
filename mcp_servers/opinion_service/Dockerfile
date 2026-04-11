# --- Stage 1: Build ---
FROM astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

RUN --mount=type=bind,source=.,target=/app \
    uv sync --frozen --no-dev --no-editable --package rozbirnyk_opinion_service \

# --- Stage 2: Runtime ---
FROM python:3.12-slim-bookworm

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

COPY mcp_servers/opinion_service/src ./mcp_servers/opinion_service/src

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "-m", "opinion_service.main"]