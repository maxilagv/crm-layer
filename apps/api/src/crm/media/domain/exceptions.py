"""Media domain exceptions (DRF-enveloped where they reach the API)."""

from rest_framework.exceptions import APIException


class MediaError(Exception):
    code = "media_error"


class MediaValidationError(APIException):
    status_code = 400
    default_code = "media_validation_error"
    default_detail = "Media file failed validation"


class UnsupportedMediaType(MediaValidationError):
    status_code = 415
    default_code = "unsupported_media_type"
    default_detail = "Unsupported media type"


class MediaTooLarge(MediaValidationError):
    status_code = 413
    default_code = "media_too_large"
    default_detail = "Media file is too large"


class EmptyMediaFile(MediaValidationError):
    default_code = "empty_media_file"
    default_detail = "Media file is empty"


class UnsafeStorageKey(MediaError):
    code = "unsafe_storage_key"


class MediaAssetNotDownloadable(APIException):
    status_code = 409
    default_code = "media_not_downloadable"
    default_detail = "Media asset is not available for download"


class TranscriptionNotAudio(MediaError):
    code = "transcription_not_audio"


class RetryableMediaError(MediaError):
    """Persisted failure that a Celery worker may retry."""

    code = "media_retryable"
