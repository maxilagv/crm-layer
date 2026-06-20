"""Shared internal helpers for media services."""


def org_stub(organization_id):
    """Lightweight object carrying ``.id`` for audit calls."""

    class _Org:
        id = organization_id

    return _Org()
