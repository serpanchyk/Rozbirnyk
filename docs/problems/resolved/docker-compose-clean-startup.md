# Docker Compose Clean Startup

## Summary

The documented clean startup flow is:

```text
docker compose down --remove-orphans
docker compose up --build -d
```

In practice, that flow can fail because Docker refuses to stop or replace the
existing backend container, leaving stale Compose-managed containers in
`Created` state and preventing a clean reconciliation.

## Status

Resolved in docs and Compose configuration on 2026-05-14.

## What We Know

- `docker compose down --remove-orphans` failed while stopping
  `rozbirnyk-frontend` with a Docker daemon `permission denied` error.
- A later `docker compose up --build -d` could build images successfully.
- `wiki-service`, `news-service`, and `agent-service` could be started and
  became healthy.
- `backend` could not be cleanly recreated because Docker refused to stop the
  currently running `rozbirnyk-backend` container.
- Compose also produced an extra backend container in `Created` state during
  the failed replacement path.

Observed stale containers during debugging:

- `fca13d580a62_rozbirnyk-backend`
- `e7321a9d90f4_rozbirnyk-backend`

## Evidence

Observed Docker errors:

```text
cannot stop container ... permission denied
```

and:

```text
Error when allocating new name: Conflict. The container name
"/rozbirnyk-backend" is already in use ...
```

Final observed practical state on 2026-05-14:

- `frontend`: healthy
- `backend`: healthy, but still the older running container
- `redis`: healthy
- `news-service`: healthy
- `wiki-service`: healthy
- `agent-service`: healthy
- extra backend container: `Created`

## Impact

- The documented startup command path is not reliably idempotent.
- Stack upgrades can leave stale containers behind.
- Operators can end up with a partially refreshed deployment where some
  services use new images and others continue running older containers.
- Troubleshooting becomes slower because service health and Compose state can
  disagree.

## Likely Root Cause

- Docker daemon or host-level permissions are blocking container stop/recreate
  operations for some existing containers.
- Compose recovery after a failed recreate leaves orphaned `Created`
  containers.
- The project currently depends on a clean down/up cycle, so daemon-level
  stop failures break the expected workflow.

## Resolution Applied

- Changed the default startup flow in `docs/run-project.md` to:

  ```text
  docker compose up --build -d
  ```

  instead of forcing `docker compose down --remove-orphans` before each start.
- Kept teardown commands in the docs only for explicit cleanup and reset cases.
- Removed fixed `container_name` declarations from `docker-compose.yaml` so
  Compose can manage recreation without hard container-name conflicts.
- Updated agent instructions to use `up --build -d` as the normal startup path.

## Why This Resolves The Main Problem

- `docker compose up --build -d` is the normal idempotent Compose workflow and
  avoids unnecessary stop/remove cycles during everyday startup.
- Removing explicit container names avoids a class of recreate failures where
  stale containers block replacement with name conflicts.
- Cleanup remains documented, but it is now an explicit recovery/reset action
  instead of a mandatory part of every start.

## Useful Follow-Up Features

- A scripted health/reconciliation command for local startup.
- Better startup diagnostics that summarize stale containers and failed
  service swaps.
- Optional automation to detect and clean non-running duplicate Compose
  containers for the same service.

## Remaining Risk

- A host-level Docker daemon `permission denied` stop failure can still happen
  on a broken local Docker installation, but it is no longer part of the
  default startup path.
- If that daemon issue reappears during an explicit cleanup or recreate, the
  documented recovery step is to restart Docker and rerun the normal startup
  command.
