# Startup Config Validation

## Summary

Services could enter noisy restart loops or fail later than necessary when
required configuration was empty, placeholder-based, or unavailable through the
expected runtime provider chain.

## Status

Resolved on 2026-05-14.

## Evidence

- `agent_service` restarted repeatedly when Docker Compose injected
  `MODEL__REGION_NAME=""`, overriding the configured Bedrock region.
- AWS credential issues were only discovered during startup crashes or first
  Bedrock use instead of being reported as one explicit startup validation
  error.
- Example placeholder secret values such as `replace-me` could be copied into
  local `.env` files and fail later than necessary.

## Impact

- Slower diagnosis during local startup.
- Unclear operator feedback about whether the issue was config shape, missing
  credentials, or provider access.
- Extra Docker/container churn from restart loops.

## Root Cause

- Empty environment values were treated as real overrides.
- Required external prerequisites such as AWS credentials were not validated at
  a dedicated startup boundary.
- Placeholder example secrets were not rejected explicitly.

## Chosen Fix

- Ignore empty environment values during settings loading.
- Validate required Bedrock/LangSmith/Tavily values more strictly at config
  load time.
- Run an `agent_service` startup preflight that resolves AWS credentials before
  the service boots.
- Update Docker Compose defaults and startup docs so failures are immediate and
  actionable.
