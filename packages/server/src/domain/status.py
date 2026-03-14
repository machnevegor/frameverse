from enum import StrEnum


class TaskErrorCode(StrEnum):
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class MovieStatus(StrEnum):
    QUEUED = "queued"
    ASR = "asr"  # transcription
    SBD = "sbd"  # shot boundary detection
    SBE = "sbe"  # shot boundary extraction
    ANN = "ann"  # annotation
    EMB = "emb"  # embedding
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED_ASR = "failed_asr"
    FAILED_SBD = "failed_sbd"
    FAILED_SBE = "failed_sbe"
    FAILED_ANN = "failed_ann"
    FAILED_EMB = "failed_emb"


class NonTerminalMovieStatus(StrEnum):
    QUEUED = "queued"
    ASR = "asr"
    SBD = "sbd"
    SBE = "sbe"
    ANN = "ann"
    EMB = "emb"


class TerminalMovieStatus(StrEnum):
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED_ASR = "failed_asr"
    FAILED_SBD = "failed_sbd"
    FAILED_SBE = "failed_sbe"
    FAILED_ANN = "failed_ann"
    FAILED_EMB = "failed_emb"


class FailedMovieStatus(StrEnum):
    FAILED_ASR = "failed_asr"
    FAILED_SBD = "failed_sbd"
    FAILED_SBE = "failed_sbe"
    FAILED_ANN = "failed_ann"
    FAILED_EMB = "failed_emb"


class SceneStatus(StrEnum):
    QUEUED = "queued"
    ANN = "ann"
    EMB = "emb"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED_ANN = "failed_ann"
    FAILED_EMB = "failed_emb"


class NonTerminalSceneStatus(StrEnum):
    QUEUED = "queued"
    ANN = "ann"
    EMB = "emb"


class TerminalSceneStatus(StrEnum):
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED_ANN = "failed_ann"
    FAILED_EMB = "failed_emb"


class FailedSceneStatus(StrEnum):
    FAILED_ANN = "failed_ann"
    FAILED_EMB = "failed_emb"
