from django.db import models


class LeadStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    WON = "won", "Won"
    LOST = "lost", "Lost"
    UNQUALIFIED = "unqualified", "Unqualified"
    NURTURING = "nurturing", "Nurturing"
    ARCHIVED = "archived", "Archived"


class LeadStage(models.TextChoices):
    NEW = "new", "New"
    CONTACTED = "contacted", "Contacted"
    QUALIFYING = "qualifying", "Qualifying"
    WARM = "warm", "Warm"
    HOT = "hot", "Hot"
    CALL_REQUESTED = "call_requested", "Call requested"
    CALL_SCHEDULED = "call_scheduled", "Call scheduled"
    PROPOSAL_PENDING = "proposal_pending", "Proposal pending"
    WON = "won", "Won"
    LOST = "lost", "Lost"
    NURTURING = "nurturing", "Nurturing"
    UNQUALIFIED = "unqualified", "Unqualified"


class LeadTemperature(models.TextChoices):
    COLD = "cold", "Cold"
    WARM = "warm", "Warm"
    HOT = "hot", "Hot"
    CRITICAL = "critical", "Critical"


class BudgetSignal(models.TextChoices):
    NONE = "none", "None"
    UNKNOWN = "unknown", "Unknown"
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CONFIRMED = "confirmed", "Confirmed"


class LeadUrgency(models.TextChoices):
    UNKNOWN = "unknown", "Unknown"
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class AuthoritySignal(models.TextChoices):
    UNKNOWN = "unknown", "Unknown"
    INFLUENCER = "influencer", "Influencer"
    DECISION_MAKER = "decision_maker", "Decision maker"
    LIKELY_DECISION_MAKER = "likely_decision_maker", "Likely decision maker"


class StageChangedByType(models.TextChoices):
    USER = "user", "User"
    AI_AGENT = "ai_agent", "AI agent"
    SYSTEM = "system", "System"
    AUTOMATION = "automation", "Automation"
    WORKER = "worker", "Worker"


class LeadSourceType(models.TextChoices):
    WHATSAPP = "whatsapp", "WhatsApp"
    MANUAL = "manual", "Manual"
    WEBSITE = "website", "Website"
    REFERRAL = "referral", "Referral"
    CAMPAIGN = "campaign", "Campaign"
    IMPORT = "import", "Import"
    UNKNOWN = "unknown", "Unknown"
