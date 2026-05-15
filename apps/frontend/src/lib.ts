import type { ActiveModelInfo, ProviderErrorInfo, SessionEvent, SessionStatus } from "./types";

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

export function activeModelLabel(model: ActiveModelInfo | null): string {
  if (model === null) {
    return "Awaiting world builder";
  }
  return model.display_name ?? `${model.provider}:${model.model_id}`;
}

export function failureMessage(
  errorInfo: ProviderErrorInfo | null,
  fallbackError: string | null,
  model: ActiveModelInfo | null,
): string | null {
  if (errorInfo?.error_code === "provider_rate_limited") {
    const activeModel = model?.model_id ?? "the active model/profile";
    return `AWS Bedrock is rate-limiting ${activeModel}. Retry this world build in a moment.`;
  }
  return errorInfo?.message ?? fallbackError;
}
