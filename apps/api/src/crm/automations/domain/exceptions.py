class AutomationError(Exception):
    pass


class AutomationPermissionDenied(AutomationError):
    pass


class AutomationLoopDetected(AutomationError):
    pass
