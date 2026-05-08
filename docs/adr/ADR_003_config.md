# ADR 003: Hierarchical Type-Safe Configuration Management

## Status
Accepted

## Context
Rozbirnyk is a multi-agent system composed of independent microservices (e.g., `news_service`, `wiki_service`, `agent_service`). Each service requires its own operational settings (ports, log levels) and secure credentials (API keys). 

Managing configurations inconsistently across services leads to deployment failures (e.g., a missing API key only failing mid-simulation) and security risks (e.g., committing secrets to version control). Furthermore, the Dockerized environments require the ability to easily override file-based configurations using environment variables.

## Decision
We will implement a unified, strongly-typed, and hierarchical configuration management system using `pydantic-settings`.

### 1. Separation of Concerns
*   **`config.toml` (Version Controlled):** Contains non-sensitive, static operational defaults (e.g., `port = 8003`, `level = "INFO"`).
*   **`.env` / Environment Variables (Ignored by Git):** Exclusively stores sensitive credentials (e.g., `TAVILY_API_KEY`) and dynamic environment overrides.

### 2. Resolution Priority
Configuration merging is centralized in the `common` package via the `BaseServiceConfig` class. The strict evaluation priority (Highest to Lowest) is:
1.  Explicit initialization arguments
2.  OS Environment variables
3.  `.env` file
4.  `config.toml` file

### 3. Strict Validation & Caching
*   **Fail-Fast Startup:** Using Pydantic's `ConfigDict(extra="forbid")`, services will crash immediately upon startup if required fields are missing, if types are incorrect (e.g., passing a string to a port integer), or if unrecognized configuration keys are present.
*   **Singleton Pattern:** Service configurations will be loaded using Python's `@lru_cache` on the `get_config()` function, ensuring the file I/O parsing only happens once and memory is shared across the service lifecycle.

### 4. Agent Model and MCP Configuration
The `agent_service` owns model and agent-tool runtime settings:
*   **LLM model settings:** `provider`, `model_id`, required `region_name`, `temperature`, and `max_tokens` are validated in `agent_service/schema.py`.
*   **AWS credentials:** Credentials are never stored in `config.toml`; Bedrock uses the standard AWS provider chain such as environment variables, shared profiles, or runtime IAM roles.
*   **MCP server settings:** `wiki_service` and `news_service` connection settings define host, port, transport, and endpoint path so the Tool Registry can discover tools from both services.

## Consequences

### Positive
*   **Type Safety:** Agents and services interact with Python objects (`config.service.port`), not raw dictionaries or easily misspelled string keys.
*   **Security:** Clear boundaries ensure developers know exactly where to put API keys without risking accidental commits.
*   **Deployment Flexibility:** In our Docker Compose environment, we can seamlessly override nested TOML settings using environment variables with a double-underscore delimiter (e.g., `SERVICE__PORT=8080`).
*   **Model Portability:** LLM providers, model IDs, and regions can change without editing graph code, while missing regions fail before the first model call.

### Negative
*   **Boilerplate:** Every new service requires explicit Pydantic models before it can read simple settings.
*   **Dependency Requirement:** Binds the project's foundational configuration layer tightly to the `pydantic` and `pydantic-settings` libraries.

### Mitigation
*   The `common/config.py` module abstracts away the complex multi-source resolution logic. This keeps service-level configuration schema files purely declarative and easy to read.
