from django.db import models


class OpportunityStage(models.TextChoices):
    NEW = "new", "New"
    QUALIFYING = "qualifying", "Qualifying"
    PROPOSAL = "proposal", "Proposal"
    NEGOTIATION = "negotiation", "Negotiation"
    WON = "won", "Won"
    LOST = "lost", "Lost"


class FollowupStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    DONE = "done", "Done"
    POSTPONED = "postponed", "Postponed"
    CANCELLED = "cancelled", "Cancelled"


class ObjectionType(models.TextChoices):
    PRICE = "price", "Price"
    TIME = "time", "Time"
    TRUST = "trust", "Trust"
    NEED = "need", "Need"
    NOT_INTERESTED = "not_interested", "Not interested"
    OTHER = "other", "Other"


class PlaybookStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    DRAFT = "draft", "Draft"
    ARCHIVED = "archived", "Archived"


class CallRequestStatus(models.TextChoices):
    REQUESTED = "requested", "Requested"
    OWNER_NOTIFIED = "owner_notified", "Owner notified"
    SCHEDULED = "scheduled", "Scheduled"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    EXPIRED = "expired", "Expired"


class SalesIntent(models.TextChoices):
    NEW_INTEREST = "new_interest", "New interest"
    ASKING_PRICE = "asking_price", "Asking price"
    ASKING_HOW_IT_WORKS = "asking_how_it_works", "Asking how it works"
    HAS_PROBLEM = "has_problem", "Has problem"
    WANTS_CALL = "wants_call", "Wants call"
    OBJECTING_PRICE = "objecting_price", "Objecting price"
    OBJECTING_TIME = "objecting_time", "Objecting time"
    NOT_INTERESTED = "not_interested", "Not interested"
    QUALIFIED = "qualified", "Qualified"
    UNQUALIFIED = "unqualified", "Unqualified"
    SPAM = "spam", "Spam"
    OTHER = "other", "Other"
