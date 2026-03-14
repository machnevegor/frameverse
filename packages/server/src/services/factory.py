"""Service graph factories."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.assemblyai import AssemblyAIAdapter
from src.adapters.openrouter import OpenRouterAdapter
from src.adapters.s3 import S3Adapter
from src.adapters.scenedetect import SceneDetectAdapter
from src.services.pipeline import PipelineService

_storage = S3Adapter()
_asr = AssemblyAIAdapter()
_sbd_sbe = SceneDetectAdapter()
_openrouter = OpenRouterAdapter()


def get_storage() -> S3Adapter:
    """Return shared storage adapter."""
    return _storage


def get_emb() -> OpenRouterAdapter:
    """Return shared embedding adapter."""
    return _openrouter


def build_pipeline_service(session: AsyncSession) -> PipelineService:
    """Build pipeline service for one DB session."""
    return PipelineService(
        session,
        storage=_storage,
        asr=_asr,
        sbd=_sbd_sbe,
        sbe=_sbd_sbe,
        ann=_openrouter,
        emb=_openrouter,
    )
