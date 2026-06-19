"""Settings-facing AI provider management + connection status.

Lets an operator (settings.manage) register/enable AI providers and see which
provider credentials are configured in the environment. Secret API keys are
read from settings (``OPENAI_API_KEY`` / ``ANTHROPIC_API_KEY``) — never accepted
or returned here.
"""

from django.conf import settings as django_settings
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView

from crm.ai.domain.enums import AIProviderType
from crm.ai.models import AIModelConfig, AIProvider
from crm.core.api.responses import success_response
from crm.core.security.drf import RequiresPermission
from crm.core.security.permissions import PermissionCode
from crm.organizations.selectors.organizations import resolve_current_organization

ENV_VAR_BY_TYPE: dict[str, str | None] = {
    AIProviderType.OPENAI.value: "OPENAI_API_KEY",
    AIProviderType.ANTHROPIC.value: "ANTHROPIC_API_KEY",
    AIProviderType.GEMINI.value: "GEMINI_API_KEY",
    AIProviderType.FAKE.value: None,
}

PROVIDER_LABELS: dict[str, str] = {
    AIProviderType.OPENAI.value: "OpenAI",
    AIProviderType.ANTHROPIC.value: "Anthropic",
    AIProviderType.GEMINI.value: "Google Gemini",
    AIProviderType.FAKE.value: "Fake (pruebas)",
}


class AIProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIProvider
        fields = ["id", "name", "provider_type", "is_enabled", "priority", "created_at"]
        read_only_fields = ["id", "created_at"]


class _SettingsView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.SETTINGS_MANAGE.value


class AIProvidersView(_SettingsView):
    def get(self, request):
        organization = resolve_current_organization(request)
        providers = AIProvider.objects.filter(organization_id=organization.id).order_by(
            "priority", "-created_at"
        )
        return success_response(request, AIProviderSerializer(providers, many=True).data)

    def post(self, request):
        organization = resolve_current_organization(request)
        serializer = AIProviderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider = serializer.save(organization_id=organization.id, created_by_id=request.user.id)
        return success_response(request, AIProviderSerializer(provider).data, status=201)


class AIProviderDetailView(_SettingsView):
    def _get(self, organization, provider_id):
        provider = AIProvider.objects.filter(
            organization_id=organization.id, id=provider_id
        ).first()
        if provider is None:
            raise NotFound("Provider no encontrado en esta organización")
        return provider

    def get(self, request, provider_id):
        organization = resolve_current_organization(request)
        provider = self._get(organization, provider_id)
        return success_response(request, AIProviderSerializer(provider).data)

    def patch(self, request, provider_id):
        organization = resolve_current_organization(request)
        provider = self._get(organization, provider_id)
        serializer = AIProviderSerializer(provider, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by_id=request.user.id)
        return success_response(request, AIProviderSerializer(provider).data)


class AIConnectionView(_SettingsView):
    """Per provider type: env credential presence + whether it's registered."""

    def get(self, request):
        organization = resolve_current_organization(request)
        records = {
            p.provider_type: p for p in AIProvider.objects.filter(organization_id=organization.id)
        }
        providers = []
        for ptype in [t.value for t in AIProviderType]:
            env_var = ENV_VAR_BY_TYPE.get(ptype)
            configured = True if env_var is None else bool(getattr(django_settings, env_var, ""))
            record = records.get(ptype)
            providers.append(
                {
                    "provider_type": ptype,
                    "label": PROVIDER_LABELS.get(ptype, ptype),
                    "env_var": env_var,
                    "credential_configured": configured,
                    "registered": record is not None,
                    "enabled": bool(record and record.is_enabled),
                }
            )
        active_configs = AIModelConfig.objects.filter(
            organization_id=organization.id, is_active=True
        ).count()
        return success_response(
            request,
            {"providers": providers, "active_model_configs": active_configs},
        )
