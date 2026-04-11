---
name: code-documentation
description: Use this skill for writing, updating, or reviewing code documentation (docstrings and module-level docs). Enforces consistent Google-style documentation across Rozbirnyk multi-agent system.
---

## When to use this skill
- Creating or modifying functions, classes, methods, or modules
- Adding or updating FastAPI endpoints
- Working in MCP services (news, opinion, knowledge, probability)
- Editing shared code in packages/common
- Reviewing pull requests for documentation quality

## Documentation Standard

Use **Google-style docstrings** for all code documentation.

Docstrings must describe **intent and behavior**, not implementation details.

## Core Rules

- Every module, class, and public function must have a docstring.
- Private functions must have a docstring if logic is non-trivial.
- Module-level docstring is required for all main modules and `__init__.py`.
- Documentation must be updated whenever code changes.
- First line must be a concise imperative summary (e.g. “Fetch…”, “Compute…”).
- Type hints are mandatory and should not be duplicated in docstrings.

## Required Structure

```python
def example_function(x: int) -> int:
    """Compute transformed value from input signal.

    Args:
        x: Input integer signal. Must be positive.

    Returns:
        Transformed integer result.

    Raises:
        ValueError: If input is invalid.

    Example:
        >>> example_function(5)
        10
    """
```

## Section Usage Rules

- Summary line → always required
- Args → required when parameters exist
- Returns → always required
- Raises → required when exceptions are possible
- Example → required for non-trivial logic
- Note / Warning → only for important constraints or side effects

## System-Specific Rules (Rozbirnyk)

- FastAPI endpoints: docstring is used as API description
- MCP services:
  - must document data flow: input → processing → output
  - must describe role in forecasting pipeline
- packages/common: must be more detailed than normal code
- Logging context (trace_id, session_id, user_id) must be mentioned if relevant
- Async functions must explicitly indicate async behavior if not obvious

## Anti-Patterns

- Do not describe obvious code behavior
- Do not repeat type hints
- Do not document implementation details unless necessary
- Do not use vague summaries like “This function does X”
- Do not leave outdated docstrings after refactoring

## Module-Level Documentation

```python
"""News service module.

Fetches and processes news articles from multiple sources.
Outputs structured data used by opinion and forecasting services.
"""
```

## Enforcement Rule

If documentation does not improve understanding of system behavior:
→ it must be removed or rewritten.

## Application Rule

- On new code → write documentation immediately
- On refactor → update documentation in sync
- On review → enforce completeness and clarity
- Always prioritize clarity of system flow over code-level explanation