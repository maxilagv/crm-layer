class SalesError(Exception):
    """Base error for sales services."""


class SalesReplyBlocked(SalesError):
    """The reply cannot be sent because a deterministic policy blocked it."""


class CrossOrganizationSalesError(SalesError):
    """A sales mutation crossed organization boundaries."""
