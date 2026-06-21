"""Enums for the autonomous sales agent ("Cazador")."""

from django.db import models


class CampaignStatus(models.TextChoices):
    DRAFT = "draft", "Borrador"
    ACTIVE = "active", "Activa"
    PAUSED = "paused", "Pausada"
    COMPLETED = "completed", "Completada"
    ARCHIVED = "archived", "Archivada"


class CampaignSource(models.TextChoices):
    GOOGLE_PLACES = "google_places", "Google Places"
    APOLLO = "apollo", "Apollo"


class ProspectStatus(models.TextChoices):
    DISCOVERED = "discovered", "Descubierto"
    QUALIFIED = "qualified", "Calificado"  # passed AI fit, awaiting approval/contact
    APPROVED = "approved", "Aprobado"  # owner approved → outreach queued
    CONTACTED = "contacted", "Contactado"
    REPLIED = "replied", "Respondió"
    INTERESTED = "interested", "Interesado"  # the golden state
    NOT_INTERESTED = "not_interested", "No interesado"
    DISQUALIFIED = "disqualified", "Descalificado"  # AI judged no fit
    DO_NOT_CONTACT = "do_not_contact", "No contactar"
    FAILED = "failed", "Falló"


class ProspectChannel(models.TextChoices):
    WHATSAPP = "whatsapp", "WhatsApp"
    SMS = "sms", "SMS"
    EMAIL = "email", "Email"


# Statuses a prospect can be in once it has been worked (for stats/filtering).
CONTACTED_STATUSES = frozenset(
    {
        ProspectStatus.CONTACTED.value,
        ProspectStatus.REPLIED.value,
        ProspectStatus.INTERESTED.value,
        ProspectStatus.NOT_INTERESTED.value,
    }
)
