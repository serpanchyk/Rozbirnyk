COPY mcp_servers/knowledge_service/config.toml ./config.toml
COPY --from=builder /app/.venv /app/.venv
RUN --mount=type=bind,source=.,target=/app \
    uv sync --frozen --no-dev --no-editable --package rozbirnyk_knowledge_service
# --- Stage 1: Build ---
# Copy only necessary files for dependency installation
COPY pyproject.toml uv.lock ./
COPY mcp_servers/knowledge_service/pyproject.toml ./mcp_servers/knowledge_service/
COPY packages/common/pyproject.toml ./packages/common/

# Install dependencies
RUN uv sync --frozen --no-dev --no-editable --package rozbirnyk_knowledge_service
ENV UV_COMPILE_BYTECODE=1

RUN --mount=type=bind,source=.,target=/app \
    uv sync --frozen --no-dev --no-editable --package rozbirnyk_knowledge_service

# --- Stage 2: Runtime ---
# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv ./.venv

# Copy the application code
WORKDIR /app
COPY mcp_servers/knowledge_service/config.toml ./
COPY --from=builder /app/.venv /app/.venv
# Set environment variables

COPY mcp_servers/knowledge_service/src ./src
COPY mcp_servers/knowledge_service/config.toml ./config.toml
# Run the application

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

CMD ["python", "-m", "knowledge_service.main"]