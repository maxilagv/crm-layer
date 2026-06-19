from __future__ import annotations

from crm.analytics.services.alert_service import AlertService


def check_organization_alerts(*, organization, date=None):
    return AlertService.check_alerts(organization=organization, date=date)
