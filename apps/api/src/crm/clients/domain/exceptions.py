from rest_framework.exceptions import APIException


class ClientError(APIException):
    status_code = 400
    default_code = "client_error"
    default_detail = "Client error"


class DuplicateActiveClient(ClientError):
    status_code = 409
    default_code = "duplicate_active_client"
    default_detail = "Contact already has an active client"


class DuplicateClientContact(ClientError):
    status_code = 409
    default_code = "duplicate_client_contact"
    default_detail = "Contact is already linked to this client"
