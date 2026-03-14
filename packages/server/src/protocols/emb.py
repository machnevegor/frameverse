"""Embedding provider protocol."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class EMBProtocol(Protocol):
    """Contract for embedding adapters."""

    async def embed_texts(
        self,
        texts: list[str],
        *,
        trace_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> list[list[float]]: ...

    async def embed_images(
        self,
        image_urls: list[str],
        *,
        trace_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> list[list[float]]: ...
