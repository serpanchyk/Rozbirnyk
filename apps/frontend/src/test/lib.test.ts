import { describe, expect, it } from "vitest";

import { isTerminalStatus, mergeEvents, stageLabel } from "../lib";
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
});
