"""OpenAPI error message constants."""

from src.config import SUPPORTED_IMAGE_UPLOAD_TYPES, SUPPORTED_VIDEO_UPLOAD_TYPES

_SUPPORTED_UPLOAD_TYPES = SUPPORTED_VIDEO_UPLOAD_TYPES + SUPPORTED_IMAGE_UPLOAD_TYPES

PRESIGN_ERROR = {415: f"Content type is not supported. Use {', '.join(_SUPPORTED_UPLOAD_TYPES)}"}
CREATE_TASK_ERROR = {
    400: "Request body is missing or the video file is invalid",
    404: "Video file not found in storage",
    409: "An active task with this movie title already exists",
}
READ_TASK_ERROR = {404: "Task with the given identifier does not exist"}
CANCEL_TASK_ERROR = {
    404: "Task with the given identifier does not exist",
    409: "Task cannot be cancelled in its current state",
}
READ_MOVIE_ERROR = {404: "Movie with the given identifier does not exist"}
DELETE_MOVIE_ERROR = {404: "Movie with the given identifier does not exist"}
MOVIE_VIDEO_ERROR = {404: "Movie with the given identifier does not exist"}
MOVIE_AUDIO_ERROR = {404: "Movie audio with the given identifier does not exist"}
MOVIE_TRANSCRIPT_ERROR = {404: "Movie transcript with the given identifier does not exist"}
MOVIE_SCENES_ERROR = {404: "Movie with the given identifier does not exist"}
SEARCH_SCENES_ERROR = {400: "Search query must not be empty"}
READ_SCENE_ERROR = {404: "Scene with the given identifier does not exist"}
SCENE_VIDEO_ERROR = {404: "Scene video with the given identifier does not exist"}
SCENE_FRAMES_ERROR = {404: "Scene with the given identifier does not exist"}
READ_FRAME_ERROR = {404: "Frame with the given identifier does not exist"}
FRAME_IMAGE_ERROR = {404: "Frame with the given identifier does not exist"}
