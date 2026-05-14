import { describe, expect, it } from "vitest";

import { activeModelLabel, failureMessage, isTerminalStatus, mergeEvents, stageLabel } from "../lib";
import type { SessionEvent } from "../types";

describe("frontend helpers", () => {
  it("merges events by sequence and sorts them", () => {
    const existing: SessionEvent[] = [
      {
        sequence: 2,
        run_id: "run-1",
        session_id: "session-1",
        event: "world_builder.researching",
        stage: "researching",
        message: "Researching",
        file: null,
        error_info: null,
        model: null,
        created_at: "2026-05-11T00:00:00Z",
      },
    ];
    const incoming: SessionEvent[] = [
      {
        sequence: 1,
        run_id: "run-1",
        session_id: "session-1",
        event: "world_builder.started",
        stage: "queued",
        message: "Queued",
        file: null,
        error_info: null,
        model: null,
        created_at: "2026-05-11T00:00:00Z",
      },
    ];

    expect(mergeEvents(existing, incoming).map((event) => event.sequence)).toEqual([1, 2]);
  });

  it("identifies terminal statuses and formats stage labels", () => {
    expect(isTerminalStatus("completed")).toBe(true);
    expect(isTerminalStatus("running")).toBe(false);
    expect(stageLabel("building_states")).toBe("building states");
    expect(stageLabel(null)).toBe("Awaiting world builder");
  });

  it("formats active model labels and typed rate-limit failures", () => {
    expect(
      activeModelLabel({
        provider: "aws_bedrock",
        model_id: "test-model",
        display_name: "aws_bedrock:test-model",
      }),
    ).toBe("aws_bedrock:test-model");
    expect(
      failureMessage(
        {
          error_code: "provider_rate_limited",
          message: "raw",
          retryable: true,
          provider: "aws_bedrock",
          details: null,
        },
        "fallback",
        {
          provider: "aws_bedrock",
          model_id: "test-model",
          display_name: null,
        },
      ),
    ).toBe("AWS Bedrock is rate-limiting test-model. Retry this world build in a moment.");
  });
});
