"""Cazador 14.1: prospecting campaigns + prospects API (foundation)."""

import pytest
from django.utils import timezone

from crm.core.security.permissions import Role
from crm.prospecting.domain.enums import CampaignSource, ProspectStatus
from crm.prospecting.models import Prospect, ProspectingCampaign
from crm.prospecting.services.email_sender import build_unsubscribe_url
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
def test_prospecting_report_buckets_progress_and_masks_contacts(api_client):
    user, org = _member()
    headers = _auth(api_client, user, org)
    campaign = _make_campaign(org)
    now = timezone.now()
    Prospect.objects.create(
        organization_id=org.id,
        campaign=campaign,
        business_name="Respondio",
        place_id="r1",
        status=ProspectStatus.REPLIED.value,
        replied_at=now,
        touch_count=1,
        owner_email="owner@example.com",
        phone="+5491112345678",
        fit_score=70,
    )
    Prospect.objects.create(
        organization_id=org.id,
        campaign=campaign,
        business_name="Charla",
        place_id="r2",
        status=ProspectStatus.REPLIED.value,
        replied_at=now,
        touch_count=2,
        fit_score=80,
    )
    Prospect.objects.create(
        organization_id=org.id,
        campaign=campaign,
        business_name="Interesado",
        place_id="r3",
        status=ProspectStatus.INTERESTED.value,
        fit_score=90,
    )
    Prospect.objects.create(
        organization_id=org.id,
        campaign=campaign,
        business_name="Contactado",
        place_id="r4",
        status=ProspectStatus.CONTACTED.value,
        touch_count=1,
    )
    Prospect.objects.create(
        organization_id=org.id,
        campaign=campaign,
        business_name="Aprobado",
        place_id="r5",
        status=ProspectStatus.APPROVED.value,
    )
    Prospect.objects.create(
        organization_id=org.id,
        campaign=campaign,
        business_name="Fallido",
        place_id="r6",
        status=ProspectStatus.FAILED.value,
    )
    other = OrganizationFactory()
    other_campaign = _make_campaign(other)
    Prospect.objects.create(
        organization_id=other.id,
        campaign=other_campaign,
        business_name="Otro org",
        place_id="other",
        status=ProspectStatus.REPLIED.value,
        replied_at=now,
    )

    response = api_client.get(
        "/api/v1/prospecting/report/",
        {"campaign_id": str(campaign.id)},
        **headers,
    )

    assert response.status_code == 200
    report = response.json()["data"]
    assert report["buckets"] == {
        "respondieron": 1,
        "se_tuvo_charla": 2,
        "sin_dialogo": 2,
    }
    assert report["totals"]["contactables"] == 5
    assert report["progress_pct"] == 60.0
    assert len(report["contacts"]) == 5
    masked = next(row for row in report["contacts"] if row["business_name"] == "Respondio")
    assert masked["owner_email"] == "ow***@example.com"
    assert masked["phone"] == "***5678"


@pytest.mark.django_db
def test_prospecting_report_empty_campaign_returns_zeroes(api_client):
    user, org = _member()
    headers = _auth(api_client, user, org)
    campaign = _make_campaign(org)

    response = api_client.get(
        "/api/v1/prospecting/report/",
        {"campaign_id": str(campaign.id)},
        **headers,
    )

    assert response.status_code == 200
    report = response.json()["data"]
    assert report["buckets"] == {
        "respondieron": 0,
        "se_tuvo_charla": 0,
        "sin_dialogo": 0,
    }
    assert report["totals"]["contactables"] == 0
    assert report["progress_pct"] == 0.0
    assert report["contacts"] == []


@pytest.mark.django_db
def test_email_unsubscribe_endpoint_marks_prospect_do_not_contact(api_client, settings):
    settings.PUBLIC_APP_URL = "https://crm.example.test"
    org = OrganizationFactory()
    campaign = _make_campaign(org)
    prospect = Prospect.objects.create(
        organization_id=org.id,
        campaign=campaign,
        business_name="Con email",
        place_id="email-opt-out",
        status=ProspectStatus.CONTACTED.value,
        owner_email="owner@example.com",
    )
    url = build_unsubscribe_url(prospect=prospect)
    path = url[url.index("/api/v1/") :]

    response = api_client.get(path)

    assert response.status_code == 200
    assert response.json()["data"]["unsubscribed"] is True
    prospect.refresh_from_db()
    assert prospect.status == ProspectStatus.DO_NOT_CONTACT.value
    assert prospect.metadata["prospecting_opted_out_at"]


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
