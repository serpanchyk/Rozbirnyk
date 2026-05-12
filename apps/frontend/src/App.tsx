import { useEffect, useRef, useState } from "react";

import {
  createSession,
  createSessionEventSource,
  fetchSession,
  parseSessionEvent,
  startWorldBuilder,
} from "./api";
import { isTerminalStatus, mergeEvents, stageLabel } from "./lib";
import type { SessionEvent, SessionStatusResponse } from "./types";

const eventTypes = [
  "world_builder.started",
  "world_builder.researching",
  "world_builder.file_created",
  "world_builder.completed",
  "world_builder.failed",
] as const;

export function App() {
  const [scenario, setScenario] = useState("");
  const [maxActors, setMaxActors] = useState(8);
  const [maxStateFiles, setMaxStateFiles] = useState(12);
  const [session, setSession] = useState<SessionStatusResponse | null>(null);
  const [events, setEvents] = useState<SessionEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
    };
  }, []);

  useEffect(() => {
    if (session?.session_id === undefined || session === null) {
      return;
    }
    if (isTerminalStatus(session.status)) {
      return;
    }

    const eventSource = createSessionEventSource(session.session_id);
    eventSourceRef.current = eventSource;

    const handleEvent = async (messageEvent: MessageEvent<string>) => {
      const parsedEvent = parseSessionEvent(messageEvent.data);
      setEvents((currentEvents) => mergeEvents(currentEvents, [parsedEvent]));
      setSession((currentSession) => {
        if (currentSession === null) {
          return currentSession;
        }
        return {
          ...currentSession,
          status:
            parsedEvent.event === "world_builder.completed"
              ? "completed"
              : parsedEvent.event === "world_builder.failed"
                ? "failed"
                : "running",
          stage: parsedEvent.stage,
          error:
            parsedEvent.event === "world_builder.failed" ? parsedEvent.message : currentSession.error,
        };
      });

      if (
        parsedEvent.event === "world_builder.completed" ||
        parsedEvent.event === "world_builder.failed"
      ) {
        eventSource.close();
        eventSourceRef.current = null;
        try {
          const refreshedSession = await fetchSession(parsedEvent.session_id);
          setSession(refreshedSession);
        } catch (fetchError) {
          setError(fetchError instanceof Error ? fetchError.message : String(fetchError));
        } finally {
          setLoading(false);
        }
      }
    };

    for (const eventType of eventTypes) {
      eventSource.addEventListener(eventType, handleEvent as unknown as EventListener);
    }

    eventSource.onerror = () => {
      eventSource.close();
      eventSourceRef.current = null;
      setError("Lost live connection to backend events.");
      setLoading(false);
    };

    return () => {
      eventSource.close();
      eventSourceRef.current = null;
    };
  }, [session?.session_id, session?.status]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedScenario = scenario.trim();
    if (!trimmedScenario) {
      setError("Scenario is required.");
      return;
    }

    setLoading(true);
    setError(null);
    setEvents([]);

    try {
      const createdSession = await createSession(trimmedScenario, maxActors, maxStateFiles);
      await startWorldBuilder(createdSession.session_id);
      const initialSession = await fetchSession(createdSession.session_id);
      setSession(initialSession);
    } catch (submitError) {
      setLoading(false);
      setError(submitError instanceof Error ? submitError.message : String(submitError));
    }
  }

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <p className="eyebrow">Rozbirnyk</p>
        <h1>Build a plausible world before the simulation begins.</h1>
        <p className="lede">
          Submit a scenario, watch the World Builder research and synthesize context, and inspect
          the created actor and state files as soon as they land.
        </p>
      </section>

      <section className="workspace-grid">
        <section className="card form-card">
          <div className="card-header">
            <span className="section-kicker">Scenario Intake</span>
            <h2>Start a world build</h2>
          </div>
          <form className="scenario-form" onSubmit={handleSubmit}>
            <label>
              <span>Scenario</span>
              <textarea
                value={scenario}
                onChange={(inputEvent) => setScenario(inputEvent.target.value)}
                placeholder="What if the EU bans open-source AI models?"
                rows={6}
              />
            </label>

            <div className="limits-grid">
              <label>
                <span>Max actors</span>
                <input
                  type="number"
                  min={1}
                  value={maxActors}
                  onChange={(inputEvent) => setMaxActors(Number(inputEvent.target.value))}
                />
              </label>
              <label>
                <span>Max state files</span>
                <input
                  type="number"
                  min={1}
                  value={maxStateFiles}
                  onChange={(inputEvent) => setMaxStateFiles(Number(inputEvent.target.value))}
                />
              </label>
            </div>

            <button className="primary-button" type="submit" disabled={loading}>
              {loading ? "Building world..." : "Launch World Builder"}
            </button>
          </form>
          {error ? <p className="error-banner">{error}</p> : null}
        </section>

        <section className="card status-card">
          <div className="card-header">
            <span className="section-kicker">Live Progress</span>
            <h2>World Builder status</h2>
          </div>

          <div className="status-badges">
            <div>
              <span className="badge-label">Status</span>
              <span className="badge-value">{session?.status ?? "idle"}</span>
            </div>
            <div>
              <span className="badge-label">Stage</span>
              <span className="badge-value">{stageLabel(session?.stage ?? null)}</span>
            </div>
            <div>
              <span className="badge-label">Session</span>
              <span className="badge-value session-id">{session?.session_id ?? "not started"}</span>
            </div>
          </div>

          <ol className="event-timeline">
            {events.length === 0 ? (
              <li className="timeline-empty">Events will appear here when the build starts.</li>
            ) : (
              events.map((progressEvent) => (
                <li key={progressEvent.sequence} className="timeline-event">
                  <div className="timeline-marker" />
                  <div className="timeline-content">
                    <div className="timeline-meta">
                      <span>{progressEvent.event}</span>
                      <span>{stageLabel(progressEvent.stage)}</span>
                    </div>
                    <p>{progressEvent.message}</p>
                    {progressEvent.file ? (
                      <code>{progressEvent.file.path}</code>
                    ) : null}
                  </div>
                </li>
              ))
            )}
          </ol>
        </section>
      </section>

      <section className="results-grid">
        <FilePanel title="State Files" files={session?.state_files ?? []} />
        <FilePanel title="Actor Files" files={session?.actor_files ?? []} />
      </section>
    </main>
  );
}

function FilePanel({
  title,
  files,
}: {
  title: string;
  files: SessionStatusResponse["state_files"];
}) {
  return (
    <section className="card files-card">
      <div className="card-header">
        <span className="section-kicker">World Snapshot</span>
        <h2>{title}</h2>
      </div>
      {files.length === 0 ? (
        <p className="empty-copy">No files available yet.</p>
      ) : (
        <ul className="file-list">
          {files.map((file) => (
            <li key={file.path}>
              <div className="file-title-row">
                <strong>{file.title}</strong>
                <code>{file.path}</code>
              </div>
              <p>{file.short_description}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
