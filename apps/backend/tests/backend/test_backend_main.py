"""Test backend session orchestration endpoints."""

from backend.main import AgentServiceClient, SessionStore, WikiServiceClient, create_app
from backend.models import (
    ActiveModelInfo,
    ProviderErrorInfo,
    SessionEventsResponse,
    WikiFileSummary,
)
from fastapi.testclient import TestClient

MODEL_DISPLAY_NAME = "aws_bedrock:us.anthropic.claude-sonnet-4-20250514-v1:0"
RATE_LIMIT_MESSAGE = (
    "AWS Bedrock is rate-limiting the active model/profile. Retry this run in a moment."
)


class FakeWikiServiceClient(WikiServiceClient):
    """Stub wiki client with deterministic responses."""

    def __init__(self) -> None:
        self.reset_calls: list[str] = []

    async def reset(self, session_id: str) -> None:
        self.reset_calls.append(session_id)

    async def list_files(self, session_id: str) -> list[WikiFileSummary]:
        assert session_id
        return [
            WikiFileSummary(
                path="States/economy.md",
                title="Economy",
                short_description="Baseline.",
                kind="state",
            ),
            WikiFileSummary(
                path="Actors/parliament.md",
                title="Parliament",
                short_description="Decision maker.",
                kind="actor",
            ),
        ]


class FakeAgentServiceClient(AgentServiceClient):
    """Stub agent client with deterministic responses."""

    def __init__(self) -> None:
        self.start_calls: list[dict[str, object]] = []

    async def start_world_builder(
        self,
        session_id: str,
        scenario: str,
        limits,
    ) -> dict[str, object]:
        self.start_calls.append(
            {
                "session_id": session_id,
                "scenario": scenario,
                "max_actors": limits.max_actors,
                "max_state_files": limits.max_state_files,
            }
        )
        return {"run_id": "run-1", "session_id": session_id, "status": "queued"}

    async def get_world_builder_session(self, session_id: str) -> dict[str, object]:
        return {
            "run_id": "run-1",
            "session_id": session_id,
            "status": "completed",
            "stage": "completed",
            "effective_limits": {"max_actors": 4, "max_state_files": 6},
            "error": None,
            "error_info": None,
            "model": {
                "provider": "aws_bedrock",
                "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0",
                "display_name": MODEL_DISPLAY_NAME,
            },
        }

    async def get_world_builder_session_events(
        self,
        session_id: str,
        after_sequence: int,
    ) -> SessionEventsResponse:
        assert session_id
        if after_sequence >= 2:
            return SessionEventsResponse(run_id="run-1", session_id=session_id, events=[])
        return SessionEventsResponse.model_validate(
            {
                "run_id": "run-1",
                "session_id": session_id,
                "events": [
                    {
                        "sequence": 1,
                        "run_id": "run-1",
                        "session_id": session_id,
                        "event": "world_builder.started",
                        "stage": "queued",
                        "message": "Queued",
                        "error_info": None,
                        "model": {
                            "provider": "aws_bedrock",
                            "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0",
                            "display_name": MODEL_DISPLAY_NAME,
                        },
                    },
                    {
                        "sequence": 2,
                        "run_id": "run-1",
                        "session_id": session_id,
                        "event": "world_builder.completed",
                        "stage": "completed",
                        "message": "Done",
                        "error_info": None,
                        "model": {
                            "provider": "aws_bedrock",
                            "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0",
                            "display_name": MODEL_DISPLAY_NAME,
                        },
                    },
                ],
            }
        )


def test_backend_creates_session_and_resets_wiki() -> None:
    wiki_client = FakeWikiServiceClient()
    client = TestClient(
        create_app(
            session_store=SessionStore(),
            agent_client=FakeAgentServiceClient(),
            wiki_client=wiki_client,
        )
    )

    response = client.post(
        "/api/v1/sessions",
        json={
            "scenario": "Brazil joins OPEC",
            "max_actors": 4,
            "max_state_files": 6,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scenario"] == "Brazil joins OPEC"
    assert payload["status"] == "created"
    assert wiki_client.reset_calls == [payload["session_id"]]


def test_backend_starts_world_builder_and_returns_completed_snapshot() -> None:
    agent_client = FakeAgentServiceClient()
    wiki_client = FakeWikiServiceClient()
    client = TestClient(
        create_app(
            session_store=SessionStore(),
            agent_client=agent_client,
            wiki_client=wiki_client,
        )
    )

    create_response = client.post(
        "/api/v1/sessions",
        json={
            "scenario": "Brazil joins OPEC",
            "max_actors": 4,
            "max_state_files": 6,
        },
    )
    session_id = create_response.json()["session_id"]

    start_response = client.post(f"/api/v1/sessions/{session_id}/world-builder")
    assert start_response.status_code == 200
    assert start_response.json()["run_id"] == "run-1"
    assert agent_client.start_calls[0]["session_id"] == session_id

    status_response = client.get(f"/api/v1/sessions/{session_id}")
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["status"] == "completed"
    assert payload["effective_limits"] == {"max_actors": 4, "max_state_files": 6}
    assert payload["model"]["provider"] == "aws_bedrock"
    assert payload["state_files"][0]["path"] == "States/economy.md"
    assert payload["actor_files"][0]["path"] == "Actors/parliament.md"


def test_backend_streams_session_events_over_sse() -> None:
    client = TestClient(
        create_app(
            session_store=SessionStore(),
            agent_client=FakeAgentServiceClient(),
            wiki_client=FakeWikiServiceClient(),
        )
    )
    create_response = client.post(
        "/api/v1/sessions",
        json={"scenario": "Brazil joins OPEC"},
    )
    session_id = create_response.json()["session_id"]
    client.post(f"/api/v1/sessions/{session_id}/world-builder")

    with client.stream("GET", f"/api/v1/sessions/{session_id}/events") as response:
        body = response.read().decode("utf-8")

    assert response.status_code == 200
    assert "event: world_builder.started" in body
    assert "event: world_builder.completed" in body


def test_backend_preserves_typed_provider_failure() -> None:
    class FailingAgentServiceClient(FakeAgentServiceClient):
        async def get_world_builder_session(self, session_id: str) -> dict[str, object]:
            return {
                "run_id": "run-1",
                "session_id": session_id,
                "status": "failed",
                "stage": "failed",
                "effective_limits": {"max_actors": 4, "max_state_files": 6},
                "error": RATE_LIMIT_MESSAGE,
                "error_info": {
                    "error_code": "provider_rate_limited",
                    "message": RATE_LIMIT_MESSAGE,
                    "retryable": True,
                    "provider": "aws_bedrock",
                    "details": {"model_id": "test-model"},
                },
                "model": {
                    "provider": "aws_bedrock",
                    "model_id": "test-model",
                    "display_name": "aws_bedrock:test-model",
                },
            }

        async def get_world_builder_session_events(
            self,
            session_id: str,
            after_sequence: int,
        ) -> SessionEventsResponse:
            if after_sequence >= 1:
                return SessionEventsResponse(run_id="run-1", session_id=session_id, events=[])
            return SessionEventsResponse.model_validate(
                {
                    "run_id": "run-1",
                    "session_id": session_id,
                    "events": [
                        {
                            "sequence": 1,
                            "run_id": "run-1",
                            "session_id": session_id,
                            "event": "world_builder.failed",
                            "stage": "failed",
                            "message": RATE_LIMIT_MESSAGE,
                            "error_info": {
                                "error_code": "provider_rate_limited",
                                "message": RATE_LIMIT_MESSAGE,
                                "retryable": True,
                                "provider": "aws_bedrock",
                                "details": {"model_id": "test-model"},
                            },
                            "model": {
                                "provider": "aws_bedrock",
                                "model_id": "test-model",
                                "display_name": "aws_bedrock:test-model",
                            },
                        }
                    ],
                }
            )

    client = TestClient(
        create_app(
            session_store=SessionStore(),
            agent_client=FailingAgentServiceClient(),
            wiki_client=FakeWikiServiceClient(),
        )
    )
    create_response = client.post(
        "/api/v1/sessions",
        json={"scenario": "Brazil joins OPEC"},
    )
    session_id = create_response.json()["session_id"]
    client.post(f"/api/v1/sessions/{session_id}/world-builder")

    status_response = client.get(f"/api/v1/sessions/{session_id}")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert (
        ProviderErrorInfo.model_validate(status_payload["error_info"]).error_code
        == "provider_rate_limited"
    )
    assert ActiveModelInfo.model_validate(status_payload["model"]).model_id == "test-model"

    with client.stream("GET", f"/api/v1/sessions/{session_id}/events") as response:
        body = response.read().decode("utf-8")

    assert response.status_code == 200
    assert '"error_code": "provider_rate_limited"' in body
    assert '"model_id": "test-model"' in body
