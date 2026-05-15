# 007 — Remove Local EFK Observability Stack

## Goal

Simplify local development by removing Elasticsearch, Kibana, and Fluentd from
Docker Compose while preserving structured JSON logs.

## Status

Done.

## Acceptance Criteria

- Docker Compose no longer defines Elasticsearch, Kibana, or Fluentd services.
- Application services still emit structured JSON logs.
- Startup and observability docs describe direct stdout or `docker compose logs`
  usage instead of Kibana-based inspection.

## Related Docs

- `PROJECT_CONTEXT.md`
- `docs/adr/ADR_002_logging.md`
- `docs/run-project.md`
