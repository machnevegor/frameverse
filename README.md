# Frameverse

Frameverse is a multimodal movie search platform. It turns a full-length film
into a structured, searchable scene index so users can describe a moment,
motive, dialogue fragment, or visual situation and jump to the right timestamp.

Public entry points:

- `https://frameverse.ru/` - web application
- `https://frameverse.ru/api/v0` - API

## What This Repository Contains

This repository is a monorepo with two application packages:

- `packages/client` - the web application for browsing movies, tasks, scenes,
  and search results
- `packages/server` - the backend API and background processing pipeline

The repository also includes infrastructure configuration for local and server
deployment through `Docker Compose`, `Dokploy`, and `Traefik`.

External infrastructure such as `S3`, `PostgreSQL`, and `pgvector` is
provisioned separately and is not started by this repository's
`docker-compose.yml`.

## Core Processing Pipeline

Frameverse preprocesses a movie through five stages:

1. `ASR` - speech-to-text transcription with time-aligned segments
2. `SBD` - scene boundary detection
3. `SBE` - scene artifact extraction: clips, keyframes, and transcript slices
4. `ANN` - scene annotation using visual and textual context
5. `EMB` - embedding generation for semantic retrieval

After the pipeline finishes, a movie becomes a structured search asset with
scenes, frames, transcripts, annotations, and vectors ready for semantic search.

## Repository Structure

```text
packages/
  client/   # frontend application
  server/   # API, workers, and pipeline logic
docker-compose.yml
```

## Technology Stack

### `packages/server`

Backend and worker package for movie ingestion, orchestration, indexing, and
retrieval.

Main technologies:

- Python `3.12`
- `Litestar` for the HTTP API
- `OpenAPI` with Scalar for API schema and docs
- `Temporal` for workflow orchestration and background jobs
- `Langfuse` for tracing and prompt management
- `Advanced Alchemy`, `Pydantic`, and `pydantic-settings`
- `asyncpg` and `pgvector` for PostgreSQL access and vector search
- `aioboto3` for S3-compatible object storage
- `SceneDetect` and `ffmpeg` for video processing
- `uvicorn` for serving the API
- `ruff` and `pytest` for linting and tests

Runtime responsibilities:

- accept uploads and manage movie metadata
- run the preprocessing pipeline
- expose movie, scene, frame, transcript, task, and search endpoints
- orchestrate long-running jobs through Temporal workers
- store and retrieve structured scene data for search

### `packages/client`

Frontend package for operating the platform and exploring indexed movies.

Main technologies:

- `React 19`
- `TanStack Start`
- `TanStack Router`
- `TanStack Query`
- `Vite`
- `TypeScript`
- `Tailwind CSS 4`
- `Radix UI`
- `Biome`, `Prettier`, and `Vitest`

Runtime responsibilities:

- provide the operator-facing UI
- display movies, scenes, and processing tasks
- call the backend API
- surface semantic search results and playback navigation

## Running The Packages

### Option 1: Full stack with Docker Compose

Use this option to run the repository in its intended multi-service form.

```bash
docker compose up --build
```

`docker-compose.yml` defines:

- `client`
- `server`
- `worker`
- `temporal`
- `temporal-ui`
- Temporal bootstrap helpers for database setup and namespace creation

It does not provision `S3`, `PostgreSQL`, or `pgvector`. These dependencies are
expected to be available as external services.

This setup is designed to work behind `Traefik` and on a `Dokploy` host, using
the external `dokploy-network`.

### Option 2: Run `packages/client`

Requirements:

- Node.js `20.19+` or `22.12+`
- `pnpm 10`

Install and start:

```bash
cd packages/client
pnpm install
pnpm dev
```

Other useful commands:

```bash
pnpm build
pnpm preview
pnpm lint
pnpm fmt
```

### Option 3: Run `packages/server`

Requirements:

- Python `3.12`
- `uv`
- external dependencies required by the backend environment:
  - PostgreSQL with `pgvector`
  - S3-compatible object storage
  - Temporal
  - model provider credentials
  - Langfuse project credentials

Install dependencies:

```bash
cd packages/server
uv sync
```

Run the API:

```bash
uv run uvicorn src.main:app --reload
```

Run the Temporal worker:

```bash
uv run python -m src.workers.run
```

## Deployment Notes

This repository is prepared for containerized deployment:

- `Docker Compose` defines the multi-service topology
- `Dokploy` is the intended deployment environment
- `Traefik` routes the public web app, API, and Temporal UI
- `S3`, `PostgreSQL`, and `pgvector` are provisioned outside this repository's
  `docker-compose.yml`
- the backend exposes `OpenAPI` schema/docs
- `Temporal` handles orchestration of long-running pipeline jobs
- `Langfuse` provides tracing and prompt management for LLM-powered steps

## Why Frameverse

Frameverse is built for search beyond keywords. Instead of indexing a movie as a
single media file, it indexes the movie as scenes enriched with transcript,
visual context, annotations, and embeddings, making semantic video retrieval
practical.
