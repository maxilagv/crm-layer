"""Cazador 14.1: prospecting campaigns + prospects API (foundation)."""

import pytest

from crm.core.security.permissions import Role
from crm.prospecting.domain.enums import CampaignSource
from crm.prospecting.models import Prospect, ProspectingCampaign
from tests.factories.accounts import UserFactory
from tests.factories.organizations import MembershipFactory, OrganizationFactory


def _member(role: Role = Role.OWNER):
    user = UserFactory()
    organization = OrganizationFactory(owner=user)
    MembershipFactory(organization=organization, user=user, role=role.value)
    return user, organization


def _auth(api_client, user, organization):
    api_client.force_authenticate(user=user)
    return {"HTTP_X_ORGANIZATION_ID": str(organization.id)}


def _make_campaign(org, **kwargs):
    defaults = dict(
        organization_id=org.id,
        name="Gomerías Palermo",
        vertical="gomerías",
        query="gomerías en Palermo",
    )
    defaults.update(kwargs)
    return ProspectingCampaign.objects.create(**defaults)


@pytest.mark.django_db
def test_campaign_create_list_detail_patch(api_client):
    user, org = _member()
    headers = _auth(api_client, user, org)

    created = api_client.post(
        "/api/v1/prospecting/campaigns/",
        {
            "name": "Talleres CABA",
            "query": "talleres mecánicos en CABA",
            "vertical": "talleres",
            "target_profile": "Sin web, sin reservas online, pocas fotos.",
            "min_fit_score": 65,
            "daily_cap": 15,
            "source": "apollo",
        },
        format="json",
        **headers,
    )
    assert created.status_code == 201
    campaign_id = created.json()["data"]["id"]
    assert created.json()["data"]["status"] == "draft"
    assert created.json()["data"]["source"] == "apollo"

    listed = api_client.get("/api/v1/prospecting/campaigns/", **headers)
    assert listed.status_code == 200
    assert any(c["id"] == campaign_id for c in listed.json()["data"])

    patched = api_client.patch(
        f"/api/v1/prospecting/campaigns/{campaign_id}/",
        {"status": "active", "daily_cap": 30},
        format="json",
        **headers,
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["status"] == "active"
    assert patched.json()["data"]["daily_cap"] == 30


@pytest.mark.django_db
def test_prospects_list_filter_and_patch(api_client):
    user, org = _member()
    headers = _auth(api_client, user, org)
    campaign = _make_campaign(org)
    p1 = Prospect.objects.create(
        organization_id=org.id,
        campaign=campaign,
        business_name="Gomería Sur",
        place_id="place-1",
        fit_score=82,
        status="qualified",
    )
    Prospect.objects.create(
        organization_id=org.id,
        campaign=campaign,
        business_name="Gomería Norte",
        place_id="place-2",
        fit_score=40,
        status="disqualified",
    )

    res = api_client.get(
        "/api/v1/prospecting/prospects/",
        {"campaign_id": str(campaign.id), "min_fit_score": 70},
        **headers,
    )
    assert res.status_code == 200
    items = res.json()["data"]
    assert len(items) == 1
    assert items[0]["business_name"] == "Gomería Sur"

    patched = api_client.patch(
        f"/api/v1/prospecting/prospects/{p1.id}/",
        {"status": "approved"},
        format="json",
        **headers,
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["status"] == "approved"


@pytest.mark.django_db
def test_viewer_can_view_but_not_manage(api_client):
    user, org = _member(Role.VIEWER)
    headers = _auth(api_client, user, org)
    # Viewer has prospecting.view
    assert api_client.get("/api/v1/prospecting/campaigns/", **headers).status_code == 200
    # ...but not prospecting.manage
    res = api_client.post(
        "/api/v1/prospecting/campaigns/",
        {"name": "x", "query": "y"},
        format="json",
        **headers,
    )
    assert res.status_code == 403


@pytest.mark.django_db
def test_campaign_is_org_scoped(api_client):
    user, org = _member()
    headers = _auth(api_client, user, org)
    other = OrganizationFactory()
    foreign = _make_campaign(other)
    res = api_client.get(f"/api/v1/prospecting/campaigns/{foreign.id}/", **headers)
    assert res.status_code == 404


@pytest.mark.django_db
def test_discover_endpoint_queues_task_for_manager(api_client, monkeypatch):
    from crm.prospecting import tasks as prospecting_tasks

    calls = []
    monkeypatch.setattr(
        prospecting_tasks.discover_batch,
        "delay",
        lambda **kwargs: calls.append(kwargs),
    )
    user, org = _member()
    headers = _auth(api_client, user, org)
    campaign = _make_campaign(org)

    res = api_client.post(f"/api/v1/prospecting/campaigns/{campaign.id}/discover/", **headers)
    assert res.status_code == 202
    assert res.json()["data"]["queued"] is True
    assert calls == [{"campaign_id": str(campaign.id)}]


@pytest.mark.django_db
def test_discover_endpoint_blocks_concurrent_runs(api_client, monkeypatch):
    from crm.prospecting import tasks as prospecting_tasks

    calls = []
    monkeypatch.setattr(
        prospecting_tasks.discover_batch, "delay", lambda **kwargs: calls.append(kwargs)
    )
    user, org = _member()
    headers = _auth(api_client, user, org)
    campaign = _make_campaign(org)
    url = f"/api/v1/prospecting/campaigns/{campaign.id}/discover/"

    first = api_client.post(url, **headers)
    second = api_client.post(url, **headers)
    assert first.status_code == 202
    # Second POST is blocked by the cooldown lock — quota is not double-spent.
    assert second.status_code == 429
    assert len(calls) == 1


@pytest.mark.django_db
def test_apollo_discover_endpoint_uses_same_permission_and_cooldown(api_client, monkeypatch):
    from crm.prospecting import tasks as prospecting_tasks

    calls = []
    monkeypatch.setattr(
        prospecting_tasks.discover_batch, "delay", lambda **kwargs: calls.append(kwargs)
    )
    user, org = _member()
    headers = _auth(api_client, user, org)
    campaign = _make_campaign(org, source=CampaignSource.APOLLO.value)
    url = f"/api/v1/prospecting/campaigns/{campaign.id}/discover/"

    first = api_client.post(url, **headers)
    second = api_client.post(url, **headers)
    assert first.status_code == 202
    assert second.status_code == 429
    assert calls == [{"campaign_id": str(campaign.id)}]

    viewer, viewer_org = _member(Role.VIEWER)
    viewer_headers = _auth(api_client, viewer, viewer_org)
    viewer_campaign = _make_campaign(viewer_org, source=CampaignSource.APOLLO.value)
    assert (
        api_client.post(
            f"/api/v1/prospecting/campaigns/{viewer_campaign.id}/discover/",
            **viewer_headers,
        ).status_code
        == 403
    )


@pytest.mark.django_db
def test_run_outreach_endpoint_queues_task_for_manager(api_client, monkeypatch):
    from crm.prospecting import tasks as prospecting_tasks

    calls = []
    monkeypatch.setattr(
        prospecting_tasks.run_outreach,
        "delay",
        lambda **kwargs: calls.append(kwargs),
    )
    user, org = _member()
    headers = _auth(api_client, user, org)
    campaign = _make_campaign(org)

    res = api_client.post(f"/api/v1/prospecting/campaigns/{campaign.id}/run-outreach/", **headers)
    assert res.status_code == 202
    assert calls == [{"campaign_id": str(campaign.id)}]


@pytest.mark.django_db
def test_discover_and_outreach_require_manage(api_client, monkeypatch):
    from crm.prospecting import tasks as prospecting_tasks

    # Even if a viewer somehow reaches the task, it must never run.
    monkeypatch.setattr(
        prospecting_tasks.discover_batch, "delay", lambda **kwargs: pytest.fail("should not run")
    )
    monkeypatch.setattr(
        prospecting_tasks.run_outreach, "delay", lambda **kwargs: pytest.fail("should not run")
    )
    user, org = _member(Role.VIEWER)
    headers = _auth(api_client, user, org)
    campaign = _make_campaign(org)

    assert (
        api_client.post(
            f"/api/v1/prospecting/campaigns/{campaign.id}/discover/", **headers
        ).status_code
        == 403
    )
    assert (
        api_client.post(
            f"/api/v1/prospecting/campaigns/{campaign.id}/run-outreach/", **headers
        ).status_code
        == 403
    )
