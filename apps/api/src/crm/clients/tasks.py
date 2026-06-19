"""Clients Celery workers.

No background work is required for clients in Phase 7 (registration/lifecycle are
synchronous). This module exists for autodiscovery and future tasks (e.g.
``clients.sync_contact_types``).
"""
