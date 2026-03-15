import { queryOptions } from "@tanstack/react-query";
import {
  getMovie,
  getMovieTranscript,
  listMovieScenes,
  listMovies,
} from "#/shared/api/client";

export const movieKeys = {
  all: ["movies"] as const,
  list: (page: number, perPage: number) =>
    ["movies", "list", page, perPage] as const,
  detail: (id: string) => ["movies", "detail", id] as const,
  transcript: (id: string) => ["movies", "transcript", id] as const,
  scenes: (id: string) => ["movies", "scenes", id] as const,
};

export const moviesQueryOptions = (page: number, perPage: number) =>
  queryOptions({
    queryKey: movieKeys.list(page, perPage),
    queryFn: () => listMovies(page, perPage),
  });

export const movieQueryOptions = (movieId: string) =>
  queryOptions({
    queryKey: movieKeys.detail(movieId),
    queryFn: () => getMovie(movieId),
    enabled: Boolean(movieId),
  });

export const movieTranscriptQueryOptions = (movieId: string) =>
  queryOptions({
    queryKey: movieKeys.transcript(movieId),
    queryFn: () => getMovieTranscript(movieId),
    enabled: Boolean(movieId),
  });

export const movieScenesQueryOptions = (movieId: string) =>
  queryOptions({
    queryKey: movieKeys.scenes(movieId),
    queryFn: () => listMovieScenes(movieId),
    enabled: Boolean(movieId),
  });
