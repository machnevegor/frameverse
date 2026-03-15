export type MovieStatus =
  | "queued"
  | "asr"
  | "sbd"
  | "sbe"
  | "ann"
  | "emb"
  | "completed"
  | "cancelled"
  | "failed_asr"
  | "failed_sbd"
  | "failed_sbe"
  | "failed_ann"
  | "failed_emb";

export type SceneStatus =
  | "queued"
  | "ann"
  | "emb"
  | "completed"
  | "cancelled"
  | "failed_ann"
  | "failed_emb";

export type TaskErrorCode = "timeout" | "unknown";

export interface PaginationInfo {
  page: number;
  per_page: number;
  total_pages: number;
  total_items: number;
  has_next: boolean;
  cursor?: string | null;
}

export interface Progress {
  scenes_detected: number;
  scenes_extracted?: number;
  scenes_annotated?: number;
  scenes_embedded?: number;
}

export interface Task {
  id: string;
  updated_at: string;
  created_at: string;
  movie_id: string;
  movie_title: string;
  status: MovieStatus;
  progress?: Progress | null;
  error_message?: string | null;
  error_code?: TaskErrorCode | null;
  temporal_workflow_id: string;
  temporal_workflow_url: string;
  langfuse_trace_id: string;
  langfuse_trace_url: string;
}

export interface Movie {
  id: string;
  updated_at: string;
  created_at: string;
  title: string;
  year?: number | null;
  slogan?: string | null;
  genres?: string[] | null;
  description?: string | null;
  short_description?: string | null;
  duration?: number | null;
  poster_url?: string | null;
  video_url: string;
  audio_url?: string | null;
  last_task?: Task | null;
}

export interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
  speaker?: string | null;
}

export interface SceneTranscript {
  left_segments?: TranscriptSegment[];
  scene_segments?: TranscriptSegment[];
  right_segments?: TranscriptSegment[];
}

export interface SceneAnnotation {
  text: string;
}

export interface Scene {
  id: string;
  updated_at: string;
  created_at: string;
  status: SceneStatus;
  movie_id: string;
  position: number;
  start: number;
  end: number;
  duration: number;
  transcript: SceneTranscript;
  annotation?: SceneAnnotation | null;
  video_url?: string | null;
}

export interface SceneSearchHit extends Scene {
  score: number;
}

export interface Frame {
  id: string;
  updated_at: string;
  created_at: string;
  movie_id: string;
  scene_id: string;
  position: number;
  timestamp: number;
  score: number;
  image_url: string;
}

export interface PresignData {
  upload_url: string;
  s3_key: string;
  expires_in: number;
}

export interface PresignInput {
  content_type?: string;
}

export interface CreateTaskInput {
  s3_key: string;
  title: string;
  year?: number | null;
  slogan?: string | null;
  genres?: string[] | null;
  description?: string | null;
  short_description?: string | null;
  poster_s3_key?: string | null;
}

export interface SearchScenesInput {
  query: string;
  movie_id?: string | null;
  limit?: number;
}

export interface ApiResponse<T> {
  data: T;
  success: true;
}

export interface ApiListResponse<T> {
  data: T[];
  pagination: PaginationInfo;
  success: true;
}

// Non-terminal statuses that allow cancellation
export const NON_TERMINAL_MOVIE_STATUSES: MovieStatus[] = [
  "queued",
  "asr",
  "sbd",
  "sbe",
  "ann",
  "emb",
];

export const TERMINAL_MOVIE_STATUSES: MovieStatus[] = [
  "completed",
  "cancelled",
  "failed_asr",
  "failed_sbd",
  "failed_sbe",
  "failed_ann",
  "failed_emb",
];

export function isNonTerminalStatus(status: MovieStatus): boolean {
  return (NON_TERMINAL_MOVIE_STATUSES as string[]).includes(status);
}

export function isFailedStatus(status: MovieStatus): boolean {
  return status.startsWith("failed_");
}
