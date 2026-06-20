# `crm.media` — Private media, transcription & image generation

Stores every binary artifact (WhatsApp audio, dashboard uploads, AI-generated
images) as a **private** `MediaAsset`, transcribes audio and generates images —
always through the `AIGateway`, never a provider SDK, and never Meta directly.

## Boundaries (non-negotiable)

- **No AI SDKs here.** Audio transcription and image generation go through
  `crm.ai.services.ai_gateway.AIGateway` (`transcribe_audio`, `generate_image`).
  There is no `from openai import …` / `from anthropic import …` anywhere in this
  package, and no import from `crm.ai.providers`.
- **No direct Meta calls.** WhatsApp media is fetched through
  `WhatsAppMediaClientAdapter`, a thin wrapper over the `crm.whatsapp` module's
  `MediaClient`. There is no Graph API URL in this package.
- **Files are private by default.** `storage_key` is never serialized. Downloads
  are only possible through a short-lived signed URL.
- **Files are never downloaded in a webhook request.** All fetching/transcription
  /generation happens in Celery workers.

## Layout

```
domain/      enums, policies (allowed MIME, size cap, TTL), rules, events, value objects, exceptions
storage/     BaseStorage, LocalPrivateStorage, S3PrivateStorage, validators, signed_urls
services/    media_asset_creator, media_storage, media_downloader, audio_transcription,
             audio_processing, image_generation, generated_asset_storage, media_cleanup
selectors/   read queries (org-scoped)
api/         thin views, serializers (storage_key excluded), permissions, filters, urls
tasks.py     Celery workers (idempotent, retry-safe)
```

## Models (`media_*` tables)

| Model | Purpose |
|-------|---------|
| `MediaAsset` | The stored file: `owner_type/owner_id`, `mime_type`, `size_bytes`, `checksum` (sha256), `storage_provider`, `storage_key` (**never exposed**), `status`. `is_downloadable` ⇔ status in {stored, processed} and a key is present. |
| `Transcription` | Result of `AIGateway.transcribe_audio`: `text`, `language`, `duration_seconds`, `provider`, `model`, `ai_run_id`. |
| `MediaProcessingJob` | Per-operation job row (download/transcribe/process) with status + attempts for idempotency/observability. |
| `ImageGenerationRequest` | A request to generate an image: `prompt`, `image_type`, `aspect_ratio`, `status`, `result_media_asset`. |
| `GeneratedImage` | History of generated images linked to the request and the private asset. |

## Storage & signed URLs

- `LocalPrivateStorage` writes under `MEDIA_PRIVATE_ROOT` (default
  `BASE_DIR/private_media`) using a tenant-prefixed key
  `org/YYYY/MM/DD/uuid_filename`. `S3PrivateStorage` uploads with a private ACL
  and issues presigned URLs.
- `build_storage_key` + `is_safe_storage_key` reject path traversal
  (`..`, leading `/`, `//`, backslashes, NUL). `open_file` re-validates the key.
- Local signed URLs point at the token-protected `media-internal-download`
  endpoint (`TimestampSigner`, salt `crm.media.signed-download`, TTL
  `MEDIA_SIGNED_URL_TTL_SECONDS`, default 300s). The `storage_key` never appears
  in the URL.
- `validators.validate_media` enforces empty/size (`MEDIA_MAX_SIZE_BYTES`, default
  25 MB) / dangerous-extension / MIME / kind checks before anything is written.

## Endpoints (`/api/v1/media/`, `/api/v1/image-generations/`)

| Method & path | Permission | Notes |
|---|---|---|
| `GET/POST assets/` | `contacts.view` / `contacts.update` | list / upload (multipart) |
| `GET assets/{id}/` | `contacts.view` | metadata (no `storage_key`) |
| `GET assets/{id}/download-url/` | `contacts.view` | returns a signed URL + TTL |
| `GET internal/download/?token=` | AllowAny (token-gated) | streams bytes for local signed URLs |
| `POST transcriptions/` | `contacts.view` | enqueues/returns a transcription |
| `GET/POST image-generations/` | read / write | list / request (runs on a worker) |
| `GET image-generations/{id}/` | read | request status + result asset |
| `POST image-generations/{id}/send-to-contact/` | write | delivers via the whatsapp outbound layer |

## Workers (`crm.media.tasks`)

`media.download_whatsapp_media`, `media.transcribe_audio`, `media.process_audio`,
`media.generate_image`, `media.store_generated_image`, `media.cleanup_failed_jobs`.
All are idempotent (dedupe by reference/asset) and retry-safe (autoretry on
`RetryableMediaError`).

## Tests

`tests/unit/test_media.py` (private storage, checksum/size, validation,
path-traversal, signed URLs) and `tests/unit/test_phase7_pipeline.py` (whatsapp
download via fake adapter, transcription, image generation) plus
`tests/api/test_phase7_api.py` and `tests/unit/test_phase7_anti_coupling.py`.
