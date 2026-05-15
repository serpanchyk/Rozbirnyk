# --- Stage 1: Build ---
FROM node:20-bookworm-slim AS builder

WORKDIR /app/apps/frontend

COPY apps/frontend/package.json apps/frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

COPY apps/frontend/ ./

ARG VITE_BACKEND_URL=http://localhost:8000
ENV VITE_BACKEND_URL=${VITE_BACKEND_URL}

RUN npm run build

# --- Stage 2: Runtime ---
FROM node:20-bookworm-slim

WORKDIR /app/apps/frontend

COPY --from=builder /app/apps/frontend/package.json ./package.json
COPY --from=builder /app/apps/frontend/package-lock.json ./package-lock.json
COPY --from=builder /app/apps/frontend/node_modules ./node_modules
COPY --from=builder /app/apps/frontend/dist ./dist

EXPOSE 8501

CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "8501"]
