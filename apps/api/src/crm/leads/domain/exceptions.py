class LeadError(Exception):
    """Base error for leads domain services."""


class LeadCreationNotAllowed(LeadError):
    """The contact/conversation cannot become a lead."""


class InvalidAIScoringOutput(LeadError):
    """AIGateway did not return usable scoring data."""


class CrossOrganizationLeadError(LeadError):
    """A mutation crossed organization boundaries."""
