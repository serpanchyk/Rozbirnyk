# Slow Docker Rebuilds

## Summary

`docker compose up --build` was taking longer than expected because the Python
service images were reinstalling dependencies more often than necessary.

## Status

Resolved in Dockerfiles and docs on 2026-05-14.

## What We Know

- The repo builds five images for a normal Compose startup.
- Four Python images each ran `uv sync` in their own build stage.
- Those `uv sync` steps used a whole-repo BuildKit bind mount as their input.
- The repo already excludes large transient directories through `.dockerignore`,
  so oversized context transfer was not the main bottleneck.

## Impact

- Unrelated edits anywhere in the repository could invalidate Python dependency
  installation layers for multiple services.
- Rebuilds after small source or docs changes could still trigger repeated
  dependency reinstalls.
- Repeat builds also missed an explicit package-manager download cache, so
  `uv` and `npm` had less opportunity to reuse previously fetched artifacts.

## Likely Root Cause

- Each Python Dockerfile bound the entire repository into the build step that
  runs `uv sync`, which made the dependency layer sensitive to unrelated file
  changes outside the target service.
- Dependency installation was duplicated across four Python service images.
- The frontend build installed dependencies without an explicit persistent npm
  cache mount.

## Resolution Applied

- Replaced whole-repo bind mounts in Python Dockerfiles with explicit `COPY`
  steps for:
  - `pyproject.toml`
  - `uv.lock`
  - `packages/common`
  - the target service's `pyproject.toml`
  - the target service's `src/`
- Added `--mount=type=cache,target=/root/.cache/uv` to Python dependency
  installation steps.
- Added `--mount=type=cache,target=/root/.npm` to the frontend `npm ci` step.
- Documented the new caching behavior in `docs/run-project.md`.

## Why This Resolves The Main Problem

- Docker can now keep Python dependency layers cached when changes are limited
  to unrelated services, docs, or repo metadata.
- `uv` and `npm` can reuse downloaded artifacts across builds instead of
  starting from an empty package cache each time.
- Rebuild cost is now closer to the actual changed service scope.

## Remaining Risk

- First-time builds still need to resolve and install each image's dependency
  set.
- The four Python services still build separate virtual environments, so there
  is still some duplicated dependency work by design.
- This session could not benchmark a full Docker build because the local
  environment did not permit access to the Docker daemon socket.
