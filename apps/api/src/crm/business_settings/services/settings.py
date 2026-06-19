from django.db import transaction

from crm.audit.services import audit_event_create


def get_or_create_settings[SettingsModel](
    model: type[SettingsModel],
    *,
    organization,
) -> SettingsModel:
    record, _created = model.objects.get_or_create(organization_id=organization.id)
    return record


def safe_changes(before: dict, after: dict) -> dict:
    changes = {}
    for key, new_value in after.items():
        old_value = before.get(key)
        if old_value != new_value:
            changes[key] = {"before": old_value, "after": new_value}
    return changes


@transaction.atomic
def update_settings_record(
    *,
    record,
    serializer,
    actor,
    organization,
    request=None,
):
    before = serializer.__class__(record).data
    serializer.save()
    record.refresh_from_db()
    after = serializer.__class__(record).data
    changes = safe_changes(dict(before), dict(after))
    if changes:
        audit_event_create(
            event_type="settings_updated",
            actor=actor,
            organization=organization,
            request=request,
            resource_type=record._meta.db_table,
            resource_id=str(record.id),
            changes=changes,
        )
    return record
