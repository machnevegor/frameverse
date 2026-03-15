import { API_BASE } from "../config/constants";
import type {
  ApiListResponse,
  ApiResponse,
  CreateTaskInput,
  Frame,
  Movie,
  PaginationInfo,
  PresignData,
  PresignInput,
  Scene,
  SceneSearchHit,
  SearchScenesInput,
  Task,
  TranscriptSegment,
} from "./types";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: unknown,
  ) {
    super(`API error ${status}`);
  }
}

async function apiJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(res.status, body);
  }
  if (res.status === 204) return null as T;
  const json = (await res.json()) as ApiResponse<T>;
  return json.data;
}

async function apiList<T>(
  path: string,
  init?: RequestInit,
): Promise<{ data: T[]; pagination: PaginationInfo }> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(res.status, body);
  }
  return res.json() as Promise<ApiListResponse<T>>;
}

export async function presign(input: PresignInput = {}): Promise<PresignData> {
  return apiJson<PresignData>("/presign", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function uploadToS3(
  url: string,
  file: File,
  onProgress?: (pct: number) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    xhr.setRequestHeader("Content-Type", file.type);
    if (onProgress) {
      xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable)
          onProgress(Math.round((e.loaded / e.total) * 100));
      });
    }
    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve();
      else reject(new ApiError(xhr.status, xhr.responseText));
    });
    xhr.addEventListener("error", () =>
      reject(new ApiError(0, "Network error")),
    );
    xhr.send(file);
  });
}

export async function createTask(input: CreateTaskInput): Promise<Task> {
  return apiJson<Task>("/tasks", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function cancelTask(taskId: string): Promise<Task> {
  return apiJson<Task>(`/tasks/${taskId}/cancel`, { method: "POST" });
}

export async function listTasks(
  page = 1,
  perPage = 20,
): Promise<{ data: Task[]; pagination: PaginationInfo }> {
  return apiList<Task>(`/tasks?page=${page}&per_page=${perPage}`);
}

export async function getTask(taskId: string): Promise<Task> {
  return apiJson<Task>(`/tasks/${taskId}`);
}

export async function listMovies(
  page = 1,
  perPage = 20,
): Promise<{ data: Movie[]; pagination: PaginationInfo }> {
  return apiList<Movie>(`/movies?page=${page}&per_page=${perPage}`);
}

export async function getMovie(movieId: string): Promise<Movie> {
  return apiJson<Movie>(`/movies/${movieId}`);
}

export async function deleteMovie(movieId: string): Promise<void> {
  return apiJson<void>(`/movies/${movieId}`, { method: "DELETE" });
}

export async function getMovieTranscript(
  movieId: string,
): Promise<TranscriptSegment[]> {
  return apiJson<TranscriptSegment[]>(`/movies/${movieId}/transcript`);
}

export async function listMovieScenes(movieId: string): Promise<Scene[]> {
  return apiJson<Scene[]>(`/movies/${movieId}/scenes`);
}

export async function searchScenes(
  input: SearchScenesInput,
): Promise<SceneSearchHit[]> {
  return apiJson<SceneSearchHit[]>("/search/scenes", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function getScene(sceneId: string): Promise<Scene> {
  return apiJson<Scene>(`/scenes/${sceneId}`);
}

export async function listSceneFrames(sceneId: string): Promise<Frame[]> {
  return apiJson<Frame[]>(`/scenes/${sceneId}/frames`);
}

export function getSceneVideoUrl(sceneId: string): string {
  return `${API_BASE}/scenes/${sceneId}/video`;
}

export function getMovieVideoUrl(movieId: string): string {
  return `${API_BASE}/movies/${movieId}/video`;
}

export function getFrameImageUrl(frameId: string): string {
  return `${API_BASE}/frames/${frameId}/image`;
}
