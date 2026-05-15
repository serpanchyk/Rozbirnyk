import type { CreateSessionResponse, SessionEvent, SessionStatusResponse } from "./types";

const backendUrl = import.meta.env.VITE_BACKEND_URL ?? "http://localhost:8000";

export function getBackendUrl(): string {
  return backendUrl.replace(/\/$/, "");
}

export async function createSession(
  scenario: string,
  maxActors: number,
  maxStateFiles: number,
): Promise<CreateSessionResponse> {
  const response = await fetch(`${getBackendUrl()}/api/v1/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      scenario,
      max_actors: maxActors,
      max_state_files: maxStateFiles,
    }),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as CreateSessionResponse;
}

export async function startWorldBuilder(sessionId: string): Promise<void> {
  const response = await fetch(
    `${getBackendUrl()}/api/v1/sessions/${sessionId}/world-builder`,
    {
      method: "POST",
    },
  );
  if (!response.ok) {
    throw new Error(await response.text());
  }
}

export async function fetchSession(sessionId: string): Promise<SessionStatusResponse> {
  const response = await fetch(`${getBackendUrl()}/api/v1/sessions/${sessionId}`);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as SessionStatusResponse;
}

export function createSessionEventSource(sessionId: string): EventSource {
  return new EventSource(`${getBackendUrl()}/api/v1/sessions/${sessionId}/events`);
}

export function parseSessionEvent(data: string): SessionEvent {
  return JSON.parse(data) as SessionEvent;
}
