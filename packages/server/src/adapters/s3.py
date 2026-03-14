"""S3 storage adapter."""

from __future__ import annotations

from typing import Any

import aioboto3
from botocore.config import Config

from src.config import settings
from src.protocols.storage import StorageProtocol


class S3Adapter(StorageProtocol):
    """Async S3 adapter used by API and workers."""

    def __init__(self) -> None:
        self._session = aioboto3.Session()
        self._bucket = settings.s3_bucket
        self._client_args: dict[str, Any] = {
            "service_name": "s3",
            "endpoint_url": settings.s3_endpoint_url,
            "aws_access_key_id": settings.s3_access_key_id,
            "aws_secret_access_key": settings.s3_secret_access_key,
            "region_name": settings.s3_region,
            "config": Config(signature_version="s3v4"),
        }

    async def ensure_bucket(self) -> None:
        async with self._session.client(**self._client_args) as client:
            response = await client.list_buckets()
            names = {bucket["Name"] for bucket in response.get("Buckets", [])}
            if self._bucket not in names:
                await client.create_bucket(Bucket=self._bucket)

    async def upload(self, key: str, data: bytes, content_type: str) -> None:
        async with self._session.client(**self._client_args) as client:
            await client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)

    async def upload_file(self, key: str, file_path: str, content_type: str) -> None:
        async with self._session.client(**self._client_args) as client:
            await client.upload_file(file_path, self._bucket, key, ExtraArgs={"ContentType": content_type})

    async def download(self, key: str) -> bytes:
        async with self._session.client(**self._client_args) as client:
            response = await client.get_object(Bucket=self._bucket, Key=key)
            body = response["Body"]
            return await body.read()

    async def stream_range(self, key: str, start: int | None, end: int | None) -> tuple[bytes, str, int]:
        async with self._session.client(**self._client_args) as client:
            params: dict[str, Any] = {"Bucket": self._bucket, "Key": key}
            if start is not None or end is not None:
                actual_start = 0 if start is None else start
                range_value = f"bytes={actual_start}-" if end is None else f"bytes={actual_start}-{end}"
                params["Range"] = range_value
            response = await client.get_object(**params)
            body = response["Body"]
            data = await body.read()
            content_type = response.get("ContentType", "application/octet-stream")
            size = response.get("ContentLength", len(data))
            return data, content_type, size

    async def delete_prefix(self, prefix: str) -> None:
        async with self._session.client(**self._client_args) as client:
            paginator = client.get_paginator("list_objects_v2")
            async for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
                contents = page.get("Contents", [])
                if not contents:
                    continue
                await client.delete_objects(
                    Bucket=self._bucket,
                    Delete={"Objects": [{"Key": item["Key"]} for item in contents], "Quiet": True},
                )

    async def generate_presigned_get_url(self, key: str, expires_in: int) -> str:
        async with self._session.client(**self._client_args) as client:
            return await client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_in,
            )

    async def generate_presigned_put_url(self, key: str, expires_in: int, content_type: str) -> str:
        async with self._session.client(**self._client_args) as client:
            return await client.generate_presigned_url(
                ClientMethod="put_object",
                Params={"Bucket": self._bucket, "Key": key, "ContentType": content_type},
                ExpiresIn=expires_in,
            )

    async def exists(self, key: str) -> bool:
        async with self._session.client(**self._client_args) as client:
            try:
                await client.head_object(Bucket=self._bucket, Key=key)
            except Exception:  # noqa: BLE001
                return False
            return True
