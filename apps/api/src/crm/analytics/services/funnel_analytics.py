from __future__ import annotations

from django.db.models import Count

from crm.analytics.models import AnalyticsFunnelSnapshot
from crm.leads.models import Lead


class FunnelAnalytics:
    @staticmethod
    def build_for_day(*, organization, date) -> AnalyticsFunnelSnapshot:
        leads = Lead.objects.filter(organization_id=organization.id, created_at__date__lte=date)
        stage_counts = {
            row["stage"]: row["count"] for row in leads.values("stage").annotate(count=Count("id"))
        }
        status_counts = {
            row["status"]: row["count"]
            for row in leads.values("status").annotate(count=Count("id"))
        }
        score_distribution = {
            "0_30": leads.filter(score__lte=30).count(),
            "31_55": leads.filter(score__gte=31, score__lte=55).count(),
            "56_75": leads.filter(score__gte=56, score__lte=75).count(),
            "76_100": leads.filter(score__gte=76).count(),
        }
        snapshot, _created = AnalyticsFunnelSnapshot.objects.update_or_create(
            organization_id=organization.id,
            date=date,
            defaults={
                "stage_counts": stage_counts,
                "status_counts": status_counts,
                "score_distribution": score_distribution,
                "totals": {"leads": leads.count()},
            },
        )
        return snapshot
