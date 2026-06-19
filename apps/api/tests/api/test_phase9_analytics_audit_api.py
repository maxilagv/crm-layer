import pytest

from crm.audit.models import AuditLog
from crm.core.security.permissions import Role
from tests.factories.accounts import UserFactory
from tests.factories.conversations import MessageFactory
from tests.factories.leads import LeadFactory
from tests.factories.organizations import MembershipFactory, OrganizationFactory
from tests.factories.support import SupportTicketFactory
from tests.factories.tasks import TaskFactory


def _member(role: Role = Role.OWNER):
    user = UserFactory(password="correct-password")
    organization = OrganizationFactory(owner=user)
    MembershipFactory(organization=organization, user=user, role=role.value)
    return user, organization


def _auth(api_client, user, organization):
    api_client.force_authenticate(user=user)
    return {"HTTP_X_ORGANIZATION_ID": str(organization.id)}


@pytest.mark.django_db
def test_analytics_dashboard_with_real_data(api_client) -> None:
    user, organization = _member(Role.OWNER)
    MessageFactory(organization_id=organization.id, direction="inbound")
    LeadFactory(organization_id=organization.id)
    SupportTicketFactory(organization_id=organization.id)
    TaskFactory(organization_id=organization.id)

    response = api_client.get(
        "/api/v1/analytics/dashboard/",
        **_auth(api_client, user, organization),
    )

    assert response.status_code == 200
    totals = response.json()["data"]["totals"]
    assert totals["messages_received_total"] == 1
    assert totals["leads_created_total"] == 1
    assert totals["tickets_created_total"] == 1
    assert totals["tasks_created_total"] == 1


@pytest.mark.django_db
def test_analytics_cross_org_isolation(api_client) -> None:
    user, organization = _member(Role.OWNER)
    other = OrganizationFactory()
    MessageFactory(organization_id=organization.id, direction="inbound")
    MessageFactory(organization_id=other.id, direction="inbound")

    response = api_client.get(
        "/api/v1/analytics/conversations/",
        **_auth(api_client, user, organization),
    )

    assert response.status_code == 200
    assert response.json()["data"]["metrics"]["messages_received_total"] == 1


@pytest.mark.django_db
def test_audit_api_requires_permission(api_client) -> None:
    user, organization = _member(Role.VIEWER)

    response = api_client.get("/api/v1/audit/logs/", **_auth(api_client, user, organization))

    assert response.status_code == 403


@pytest.mark.django_db
def test_audit_api_cross_org_isolation(api_client) -> None:
    user, organization = _member(Role.OWNER)
    other = OrganizationFactory()
    AuditLog.objects.create(
        organization_id=organization.id,
        actor_type="system",
        action="lead_scored",
    )
    AuditLog.objects.create(
        organization_id=other.id,
        actor_type="system",
        action="lead_scored",
    )

    response = api_client.get("/api/v1/audit/logs/", **_auth(api_client, user, organization))

    assert response.status_code == 200
    assert response.json()["pagination"]["total"] == 1


@pytest.mark.django_db
def test_system_status_adds_correlation_header(api_client) -> None:
    user, organization = _member(Role.OWNER)

    response = api_client.get(
        "/api/system/status/",
        HTTP_X_REQUEST_ID="req-ok",
        HTTP_X_CORRELATION_ID="corr-ok",
        **_auth(api_client, user, organization),
    )

    assert response.status_code == 200
    assert response["X-Request-ID"] == "req-ok"
    assert response["X-Correlation-ID"] == "corr-ok"
    assert response.json()["data"]["status"] in {"ok", "degraded"}
