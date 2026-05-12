import type { SessionEvent, SessionStatus } from "./types";

export function mergeEvents(
  existingEvents: SessionEvent[],
  incomingEvents: SessionEvent[],
): SessionEvent[] {
  const eventsBySequence = new Map<number, SessionEvent>();
  for (const event of existingEvents) {
    eventsBySequence.set(event.sequence, event);
  }
  for (const event of incomingEvents) {
    eventsBySequence.set(event.sequence, event);
  }
  return [...eventsBySequence.values()].sort((left, right) => left.sequence - right.sequence);
}

export function isTerminalStatus(status: SessionStatus): boolean {
  return status === "completed" || status === "failed";
}

export function stageLabel(stage: string | null): string {
  if (stage === null) {
    return "Awaiting world builder";
  }
  return stage.replaceAll("_", " ");
}
