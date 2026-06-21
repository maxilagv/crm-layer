"""Aggregated Cazador reporting without per-prospect AI calls."""

from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Case, CharField, Count, Q, Value, When

from crm.prospecting.domain.enums import ProspectStatus
from crm.prospecting.models import Prospect

BUCKET_REPLIED = "respondieron"
BUCKET_CONVERSATION = "se_tuvo_charla"
BUCKET_NO_DIALOGUE = "sin_dialogo"

CONTACTABLE_STATUSES = (
    ProspectStatus.DISCOVERED.value,
    ProspectStatus.QUALIFIED.value,
    ProspectStatus.APPROVED.value,
    ProspectStatus.CONTACTED.value,
    ProspectStatus.REPLIED.value,
    ProspectStatus.INTERESTED.value,
    ProspectStatus.NOT_INTERESTED.value,
)


@dataclass(frozen=True)
class ProspectingReport:
    contacts: list[dict]
    buckets: dict[str, int]
    progress_pct: float
    totals: dict[str, int | list[dict]]


class ProspectingReportBuilder:
    @staticmethod
    def build(organization, campaign_id=None) -> dict:
        qs = Prospect.objects.filter(
            organization_id=organization.id,
            status__in=CONTACTABLE_STATUSES,
        )
        if campaign_id:
            qs = qs.filter(campaign_id=campaign_id)

        qs = qs.annotate(report_bucket=_bucket_case())
        grouped = list(qs.values("report_bucket", "status").annotate(total=Count("id")))

        buckets = {
            BUCKET_REPLIED: 0,
            BUCKET_CONVERSATION: 0,
            BUCKET_NO_DIALOGUE: 0,
        }
        status_totals: dict[str, int] = {}
        for row in grouped:
            buckets[row["report_bucket"]] = buckets.get(row["report_bucket"], 0) + row["total"]
            status_totals[row["status"]] = status_totals.get(row["status"], 0) + row["total"]

        contactables = sum(buckets.values())
        progress_pct = 0.0
        if contactables:
            progress_pct = round(
                ((buckets[BUCKET_REPLIED] + buckets[BUCKET_CONVERSATION]) / contactables) * 100,
                2,
            )

        contacts = [
            _contact_row(row)
            for row in qs.order_by("-last_touch_at", "-contacted_at", "-created_at").values(
                "id",
                "business_name",
                "status",
                "report_bucket",
                "last_touch_at",
                "fit_score",
                "owner_email",
                "phone",
            )
        ]
        totals = {
            "contactables": contactables,
            "by_status": [
                {"status": status, "total": total}
                for status, total in sorted(status_totals.items())
            ],
        }
        return ProspectingReport(
            contacts=contacts,
            buckets=buckets,
            progress_pct=progress_pct,
            totals=totals,
        ).__dict__


def _bucket_case() -> Case:
    conversation_q = Q(status=ProspectStatus.INTERESTED.value) | (
        Q(replied_at__isnull=False) & (Q(touch_count__gte=2) | Q(follow_up_count__gte=1))
    )
    return Case(
        When(conversation_q, then=Value(BUCKET_CONVERSATION)),
        When(replied_at__isnull=False, then=Value(BUCKET_REPLIED)),
        default=Value(BUCKET_NO_DIALOGUE),
        output_field=CharField(),
    )


def _contact_row(row: dict) -> dict:
    return {
        "id": row["id"],
        "business_name": row["business_name"],
        "status": row["status"],
        "bucket": row["report_bucket"],
        "last_touch_at": row["last_touch_at"],
        "fit_score": row["fit_score"],
        "owner_email": _mask_email(row["owner_email"] or ""),
        "phone": _mask_phone(row["phone"] or ""),
    }


def _mask_email(value: str) -> str:
    if "@" not in value:
        return ""
    name, domain = value.split("@", 1)
    if len(name) <= 2:
        masked = f"{name[:1]}*"
    else:
        masked = f"{name[:2]}***"
    return f"{masked}@{domain}"


def _mask_phone(value: str) -> str:
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) <= 4:
        return ""
    return f"***{digits[-4:]}"
