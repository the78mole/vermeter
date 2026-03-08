"""S3-compatible object storage service (RustFS / MinIO / AWS S3).

All blocking boto3 calls are wrapped in asyncio.to_thread() so they don't
block the FastAPI event loop.
"""

from __future__ import annotations

import asyncio
import logging
from io import BytesIO
from typing import AsyncIterator

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


def _make_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
    )


async def ensure_bucket() -> None:
    """Create the documents bucket if it does not exist yet."""

    def _create():
        client = _make_client()
        try:
            client.head_bucket(Bucket=settings.S3_BUCKET_DOCUMENTS)
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code in ("404", "NoSuchBucket"):
                client.create_bucket(Bucket=settings.S3_BUCKET_DOCUMENTS)
                logger.info("Created S3 bucket '%s'", settings.S3_BUCKET_DOCUMENTS)
            else:
                raise

    await asyncio.to_thread(_create)


async def upload_object(key: str, data: bytes, content_type: str) -> None:
    """Upload *data* to S3 under the given *key*."""

    def _upload():
        _make_client().put_object(
            Bucket=settings.S3_BUCKET_DOCUMENTS,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    await asyncio.to_thread(_upload)


async def download_object(key: str) -> bytes:
    """Download an object from S3 and return its raw bytes."""

    def _download():
        buf = BytesIO()
        _make_client().download_fileobj(settings.S3_BUCKET_DOCUMENTS, key, buf)
        return buf.getvalue()

    return await asyncio.to_thread(_download)


async def delete_object(key: str) -> None:
    """Delete an object from S3."""

    def _delete():
        _make_client().delete_object(Bucket=settings.S3_BUCKET_DOCUMENTS, Key=key)

    await asyncio.to_thread(_delete)
