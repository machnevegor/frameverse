# Frameverse Server

Backend package for the Frameverse API, processing pipeline, and background
workers.

It is responsible for movie ingestion, pipeline orchestration, scene indexing,
semantic search, and retrieval of movie, scene, frame, and task data.

## Stack

- Python `3.12`
- `Litestar`
- `OpenAPI` with Scalar
- `Temporal`
- `Langfuse`
- `Advanced Alchemy`
- `Pydantic`
- `pydantic-settings`
- `asyncpg`
- `pgvector`
- `aioboto3`
- `SceneDetect`
- `ffmpeg`
- `uvicorn`
- `ruff`
- `pytest`

## Responsibilities

- expose the HTTP API
- run the movie preprocessing pipeline
- orchestrate background jobs through Temporal workers
- store and retrieve structured search data
- integrate with object storage and model providers

## Architecture

The backend is organized into three layers:

1. `Protocol` - abstract contracts for external systems
2. `Adapter` - provider-specific implementations of those contracts
3. `Service` - business logic that connects adapters, storage, and pipeline
   steps

This design keeps the system modular and makes it easier to swap providers,
models, and infrastructure components.

## Requirements

- Python `3.12`
- `uv`
- PostgreSQL with `pgvector`
- S3-compatible object storage
- Temporal
- Langfuse credentials
- model provider credentials

External infrastructure such as `PostgreSQL`, `pgvector`, and `S3` is expected
to be provisioned separately.

## Install

```bash
uv sync
```

## Main Commands

Run the API:

```bash
uv run uvicorn src.main:app --reload
```

Run the Temporal worker:

```bash
uv run python -m src.workers.run
```

Run linting:

```bash
uv run ruff check .
```

Run tests:

```bash
uv run pytest
```

## Pipeline

The server processes movies through five stages:

1. `ASR` - speech transcription
2. `SBD` - scene boundary detection
3. `SBE` - scene artifact extraction
4. `ANN` - scene annotation
5. `EMB` - embedding generation

The result is a searchable scene index built from transcript, annotation, and
visual representations.
