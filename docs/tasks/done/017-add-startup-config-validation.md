# 017 — Add Startup Config Validation

## Goal

Fail fast when required startup configuration or credentials are missing,
empty, placeholder-only, or otherwise unusable.

## Status

Done.

## Acceptance Criteria

- Empty environment overrides do not replace valid config defaults.
- `agent_service` rejects invalid Bedrock/LangSmith startup configuration
  before serving requests.
- `agent_service` fails immediately when AWS credentials cannot be resolved
  from the standard provider chain.
- `news_service` rejects placeholder Tavily credentials copied from examples.
- Startup docs describe the new validation behavior and remediation steps.

## Related Docs

- `PROJECT_CONTEXT.md`
- `docs/run-project.md`
- `docs/problems/resolved/startup-config-validation.md`
