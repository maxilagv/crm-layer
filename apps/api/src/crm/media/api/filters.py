"""Query-param parsing helpers for media list endpoints."""


def asset_filters(query_params) -> dict:
    return {
        "source": query_params.get("source"),
        "status": query_params.get("status"),
        "mime_type": query_params.get("mime_type"),
        "owner_type": query_params.get("owner_type"),
        "owner_id": query_params.get("owner_id"),
    }


def image_generation_filters(query_params) -> dict:
    return {
        "status": query_params.get("status"),
        "image_type": query_params.get("image_type"),
        "aspect_ratio": query_params.get("aspect_ratio"),
        "created_by_id": query_params.get("created_by_id"),
    }
