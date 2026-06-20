"""Immutable value objects exchanged between media services and storage."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StoredFile:
    storage_key: str
    storage_provider: str
    size_bytes: int
    checksum: str


@dataclass(frozen=True)
class SignedURL:
    url: str
    expires_in: int


@dataclass(frozen=True)
class ValidatedMedia:
    mime_type: str
    size_bytes: int
    checksum: str
    kind: str
