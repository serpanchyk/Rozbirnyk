import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { App } from "../App";

vi.mock("../api", () => ({
  createSession: vi.fn().mockResolvedValue({
    session_id: "session-1",
    scenario: "Brazil joins OPEC",
    status: "created",
    requested_limits: { max_actors: 8, max_state_files: 12 },
  }),
  startWorldBuilder: vi.fn().mockResolvedValue(undefined),
  fetchSession: vi.fn().mockResolvedValue({
    session_id: "session-1",
    scenario: "Brazil joins OPEC",
    status: "failed",
    stage: "failed",
    run_id: "run-1",
    requested_limits: { max_actors: 8, max_state_files: 12 },
    effective_limits: { max_actors: 8, max_state_files: 12 },
    error: "AWS Bedrock is rate-limiting the active model/profile. Retry this run in a moment.",
    error_info: {
      error_code: "provider_rate_limited",
      message: "AWS Bedrock is rate-limiting the active model/profile. Retry this run in a moment.",
      retryable: true,
      provider: "aws_bedrock",
      details: { model_id: "test-model" },
    },
    model: {
      provider: "aws_bedrock",
      model_id: "test-model",
      display_name: "aws_bedrock:test-model",
    },
    state_files: [],
    actor_files: [],
  }),
  createSessionEventSource: vi.fn(),
  parseSessionEvent: vi.fn(),
}));

describe("App", () => {
  it("renders active model and typed Bedrock throttling messaging", async () => {
    render(<App />);

    fireEvent.change(screen.getByLabelText("Scenario"), {
      target: { value: "Brazil joins OPEC" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Launch World Builder" }));

    await waitFor(() => {
      expect(screen.getByText("aws_bedrock:test-model")).toBeInTheDocument();
    });

    expect(
      screen.getByText(
        "AWS Bedrock is rate-limiting test-model. Retry this world build in a moment.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Active model")).toBeInTheDocument();
  });
});
