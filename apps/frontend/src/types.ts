export type SessionStatus = "created" | "queued" | "running" | "completed" | "failed";

export type BuilderStage =
  | "queued"
  | "researching"
  | "building_states"
  | "building_actors"
  | "collecting_snapshot"
  | "completed"
  | "failed";

export type SessionEventType =
  | "world_builder.started"
  | "world_builder.researching"
  | "world_builder.file_created"
  | "world_builder.completed"
  | "world_builder.failed";

export interface SessionLimits {
  max_actors: number | null;
  max_state_files: number | null;
}

export interface WikiFileSummary {
  path: string;
  title: string;
  short_description: string;
  kind: "state" | "actor" | "timeline" | "unknown";
}

export interface SessionStatusResponse {
  session_id: string;
  scenario: string;
  status: SessionStatus;
  stage: BuilderStage | null;
  run_id: string | null;
  requested_limits: SessionLimits;
  effective_limits: SessionLimits | null;
  error: string | null;
  state_files: WikiFileSummary[];
  actor_files: WikiFileSummary[];
}

export interface SessionEvent {
  sequence: number;
  run_id: string;
  session_id: string;
  event: SessionEventType;
  stage: BuilderStage;
  message: string;
  file: WikiFileSummary | null;
  created_at: string;
}

export interface CreateSessionResponse {
  session_id: string;
  scenario: string;
  status: SessionStatus;
  requested_limits: SessionLimits;
}
