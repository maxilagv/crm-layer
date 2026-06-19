from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from crm.accounts.services.api_keys import verify_api_key


class APIKeyAuthentication(BaseAuthentication):
    keyword = "Api-Key"

    def authenticate(self, request):
        raw_key = request.headers.get("X-API-Key")
        authorization = request.headers.get("Authorization", "")
        if not raw_key and authorization.startswith(f"{self.keyword} "):
            raw_key = authorization.removeprefix(f"{self.keyword} ").strip()
        if not raw_key:
            return None

        api_key = verify_api_key(raw_key)
        if api_key is None:
            raise AuthenticationFailed("Invalid API key")

        user = None
        if api_key.created_by_id:
            user = get_user_model().objects.filter(id=api_key.created_by_id, is_active=True).first()
        if user is None:
            raise AuthenticationFailed("API key is not linked to an active user")

        request.api_key = api_key
        return user, api_key
