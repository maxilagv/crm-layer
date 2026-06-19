class TaskError(Exception):
    pass


class TaskValidationError(TaskError):
    pass


class TaskDuplicateError(TaskError):
    pass


class TaskCommandRejected(TaskError):
    pass


class TaskSnoozeLimitExceeded(TaskError):
    pass
