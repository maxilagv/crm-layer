from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from crm.accounts.api.serializers import (
    APIKeyCreatedSerializer,
    APIKeyCreateSerializer,
    APIKeySerializer,
    AuthMeSerializer,
    LoginSerializer,
    LogoutSerializer,
    RefreshSerializer,
    StatusResponseSerializer,
    TokenPairResponseSerializer,
    TokenRefreshResponseSerializer,
    UserCreateSerializer,
    UserPatchSerializer,
    UserPublicSerializer,
)
from crm.accounts.selectors.users import users_for_organization
from crm.accounts.services.api_keys import create_api_key, revoke_api_key
from crm.accounts.services.auth import authenticate_user, logout_user
from crm.accounts.services.users import create_user_for_organization
from crm.audit.services import audit_event_create
from crm.core.api.pagination import StandardPagination
from crm.core.api.responses import success_response
from crm.core.security.drf import RequiresPermission
from crm.core.security.permissions import PermissionCode
from crm.organizations.selectors.organizations import (
    current_membership_for_request,
    resolve_current_organization,
)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_scope = "login"

    @extend_schema(
        request=LoginSerializer,
        responses={200: TokenPairResponseSerializer},
        tags=["auth"],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = authenticate_user(
            request=request,
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        return success_response(
            request,
            {
                "access": result.access,
                "refresh": result.refresh,
                "token_type": "Bearer",
            },
        )


class LogoutView(APIView):
    @extend_schema(
        request=LogoutSerializer,
        responses={200: StatusResponseSerializer},
        tags=["auth"],
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        logout_user(request=request, refresh_token=serializer.validated_data["refresh"])
        return success_response(request, {"status": "logged_out"})


class RefreshView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_scope = "login"

    @extend_schema(
        request=RefreshSerializer,
        responses={200: TokenRefreshResponseSerializer},
        tags=["auth"],
    )
    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token_serializer = TokenRefreshSerializer(data=serializer.validated_data)
        token_serializer.is_valid(raise_exception=True)
        return success_response(request, token_serializer.validated_data)


class MeView(APIView):
    @extend_schema(responses={200: AuthMeSerializer}, tags=["auth"])
    def get(self, request):
        resolve_current_organization(request)
        return success_response(
            request,
            AuthMeSerializer(instance=request.user, context={"request": request}).data,
        )


class UsersView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.SETTINGS_MANAGE.value

    @extend_schema(responses={200: UserPublicSerializer(many=True)}, tags=["users"])
    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = users_for_organization(organization)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        data = UserPublicSerializer(page, many=True).data
        return paginator.get_paginated_response(data)

    @extend_schema(
        request=UserCreateSerializer,
        responses={201: UserPublicSerializer},
        tags=["users"],
    )
    def post(self, request):
        organization = resolve_current_organization(request)
        actor_membership = current_membership_for_request(request)
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = create_user_for_organization(
            organization=organization,
            actor=request.user,
            actor_membership=actor_membership,
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            name=serializer.validated_data["name"],
            phone=serializer.validated_data.get("phone", ""),
            role=serializer.validated_data["role"],
            request=request,
        )
        return success_response(request, UserPublicSerializer(user).data, status=201)


class UserDetailView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.SETTINGS_MANAGE.value

    def get_user(self, request, user_id):
        organization = resolve_current_organization(request)
        user = users_for_organization(organization).filter(id=user_id).first()
        if user is None:
            raise NotFound("User not found in current organization")
        return organization, user

    @extend_schema(responses={200: UserPublicSerializer}, tags=["users"])
    def get(self, request, user_id):
        _organization, user = self.get_user(request, user_id)
        return success_response(request, UserPublicSerializer(user).data)

    @extend_schema(
        request=UserPatchSerializer,
        responses={200: UserPublicSerializer},
        tags=["users"],
    )
    def patch(self, request, user_id):
        organization, user = self.get_user(request, user_id)
        serializer = UserPatchSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        before = UserPublicSerializer(user).data
        serializer.save()
        after = UserPublicSerializer(user).data
        audit_event_create(
            event_type="user_updated",
            actor=request.user,
            organization=organization,
            request=request,
            resource_type="accounts_user",
            resource_id=str(user.id),
            changes={
                key: {"before": before.get(key), "after": after.get(key)}
                for key in after
                if before.get(key) != after.get(key)
            },
        )
        return success_response(request, after)


class APIKeysView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.SETTINGS_MANAGE.value

    @extend_schema(responses={200: APIKeySerializer(many=True)}, tags=["api-keys"])
    def get(self, request):
        organization = resolve_current_organization(request)
        from crm.accounts.models import APIKey

        keys = APIKey.objects.filter(organization_id=organization.id).order_by("-created_at")
        return success_response(request, APIKeySerializer(keys, many=True).data)

    @extend_schema(
        request=APIKeyCreateSerializer,
        responses={201: APIKeyCreatedSerializer},
        tags=["api-keys"],
    )
    def post(self, request):
        organization = resolve_current_organization(request)
        serializer = APIKeyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        created = create_api_key(
            organization=organization,
            name=serializer.validated_data["name"],
            scopes=serializer.validated_data.get("scopes", []),
            expires_at=serializer.validated_data.get("expires_at"),
            created_by=request.user,
            request=request,
        )
        data = APIKeySerializer(created.record).data
        data["key"] = created.raw_key
        return success_response(request, data, status=201)


class APIKeyDetailView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.SETTINGS_MANAGE.value

    @extend_schema(responses={200: StatusResponseSerializer}, tags=["api-keys"])
    def delete(self, request, api_key_id):
        organization = resolve_current_organization(request)
        from crm.accounts.models import APIKey

        api_key = APIKey.objects.filter(id=api_key_id, organization_id=organization.id).first()
        if api_key is None:
            raise PermissionDenied("API key not found in current organization")
        revoke_api_key(
            api_key=api_key,
            actor=request.user,
            organization=organization,
            request=request,
        )
        return success_response(request, {"status": "revoked"})
