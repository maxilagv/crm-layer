"""MediaValidator: thin service wrapper over storage.validators."""

from crm.media.domain.value_objects import ValidatedMedia
from crm.media.storage.validators import validate_media


class MediaValidator:
    @staticmethod
    def validate(
        *, content: bytes, mime_type: str, file_name: str, require_known_mime: bool = True
    ) -> ValidatedMedia:
        return validate_media(
            content=content,
            mime_type=mime_type,
            file_name=file_name,
            require_known_mime=require_known_mime,
        )
