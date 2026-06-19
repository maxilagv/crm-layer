from __future__ import annotations


def apply_audit_filters(queryset, params):
    for field in (
        "action",
        "actor_type",
        "resource_type",
        "resource_id",
        "event_type",
        "severity",
        "access_type",
        "decision_type",
        "provider",
        "success",
        "request_id",
        "correlation_id",
    ):
        value = params.get(field)
        if value not in (None, "") and _has_field(queryset.model, field):
            queryset = queryset.filter(**{field: value})
    return queryset.order_by("-created_at")


def _has_field(model, field: str) -> bool:
    return any(model_field.name == field for model_field in model._meta.fields)
