"""Application settings and pipeline constants."""

from pydantic import Field
from pydantic_settings import BaseSettings

# Shot boundary detection
SBD_THRESHOLD = 55.0

# Shot boundary extraction
SBE_COPY_CONCURRENCY = 4
SBE_REENCODE_CONCURRENCY = 1
SBE_KEYFRAME_ALIGNMENT_TOLERANCE_SEC = 0.02

# Keyframes
KEYFRAMES_CONCURRENCY = 1
KEYFRAMES_EXTRACTION_TIMEOUT_SEC = 10
KEYFRAMES_FRAME_SAMPLE_STEP = 2
KEYFRAMES_PER_SCENE = 5
KEYFRAMES_MIN_GAP_SEC = 1.5
KEYFRAMES_MIN_SCORE_PERCENTILE = 70

# Annotation
ANN_CONCURRENCY = 25
ANN_PREVIOUS_SCENES_CONTEXT_NUM = 5
ANN_TRANSCRIPT_SIDE_CONTEXT_SEC = 15.0
ANN_PROMPT_NAME = "scene-annotation-prompt"

# Embedding
EMB_CONCURRENCY = 20
EMB_TXT_DIMENSIONS = 1024
EMB_IMG_DIMENSIONS = 2048

# Search
SEARCH_CANDIDATES_PER_CHANNEL = 20
SEARCH_MAX_MOVIE_GROUPS = 5
SEARCH_MAX_SCENES_PER_GROUP = 3
SEARCH_MAX_LLM_ITERATIONS = 3
SEARCH_LLM_MAX_TOKENS = 4096
SEARCH_LLM_MAX_SCENES = 20  # max text scenes per tool result sent to LLM
SEARCH_LLM_MAX_IMAGES = 5  # max images per tool result sent to LLM
SEARCH_SCORE_THRESHOLD = 0.40  # min similarity in any channel to include scene in tool result
SEARCH_IMAGE_THRESHOLD = 0.70  # min image similarity to attach a screenshot
SEARCH_RERANK_PROMPT_NAME = "scene-search-rerank-prompt"

# URLs
ASSEMBLYAI_BASE_URL = "https://api.assemblyai.com/v2"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
PRESIGNED_URL_TTL_SEC = 3600

# Upload types
SUPPORTED_VIDEO_UPLOAD_TYPES = ("video/mp4",)
SUPPORTED_IMAGE_UPLOAD_TYPES = ("image/webp",)


class Settings(BaseSettings):
    # DB
    database_url: str = Field(alias="DATABASE_URL")

    # App
    base_url: str = Field(alias="BASE_URL")
    base_path: str = Field(alias="BASE_PATH")

    # S3
    s3_endpoint_url: str = Field(alias="S3_ENDPOINT_URL")
    s3_region: str = Field(alias="S3_REGION")
    s3_bucket: str = Field(alias="S3_BUCKET")
    s3_access_key_id: str = Field(alias="S3_ACCESS_KEY_ID")
    s3_secret_access_key: str = Field(alias="S3_SECRET_ACCESS_KEY")

    # Model selection
    asr_model: str = Field(alias="ASR_MODEL")
    ann_model: str = Field(alias="ANN_MODEL")
    emb_txt_model: str = Field(alias="EMB_TXT_MODEL")
    emb_img_model: str = Field(alias="EMB_IMG_MODEL")
    llm_model: str = Field(alias="LLM_MODEL")

    # Model providers
    assemblyai_api_key: str = Field(alias="ASSEMBLYAI_API_KEY")
    openrouter_api_key: str = Field(alias="OPENROUTER_API_KEY")

    # Temporal
    temporal_address: str = Field(alias="TEMPORAL_ADDRESS")
    temporal_namespace: str = Field(alias="TEMPORAL_NAMESPACE")
    temporal_task_queue: str = Field(alias="TEMPORAL_TASK_QUEUE")
    temporal_public_url: str = Field(alias="TEMPORAL_PUBLIC_URL")

    # Observability
    langfuse_public_key: str = Field(alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(alias="LANGFUSE_SECRET_KEY")
    langfuse_base_url: str = Field(alias="LANGFUSE_BASE_URL")
    langfuse_public_url: str = Field(alias="LANGFUSE_PUBLIC_URL")


settings = Settings()
