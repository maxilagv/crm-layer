"""Domain exceptions for the contacts module.

These subclass DRF's APIException so the global enveloped exception handler
renders them with a stable ``error.code`` and the right status, without views
having to translate them by hand.
"""

from rest_framework.exceptions import APIException


class Conflict(APIException):
    status_code = 409
    default_code = "conflict"
    default_detail = "Resource conflict"


class PhoneConflictError(Conflict):
    default_code = "phone_already_exists"
    default_detail = "Phone number already belongs to another contact"


class ContactMergeError(APIException):
    status_code = 400
    default_code = "contact_merge_error"
    default_detail = "Contacts cannot be merged"
