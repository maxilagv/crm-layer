from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView

from crm.automations.api.serializers import (
    AutomationDispatchSerializer,
    AutomationRuleCreateSerializer,
    AutomationRuleSerializer,
    AutomationRuleUpdateSerializer,
    AutomationRunSerializer,
)
from crm.automations.selectors.automation_rules import (
    automation_rule_get_for_organization,
    automation_rules_for_organization,
)
from crm.automations.selectors.automation_runs import (
    automation_run_get_for_organization,
    automation_runs_for_organization,
)
from crm.automations.services.automation_rule_service import AutomationRuleService
from crm.automations.services.trigger_dispatcher import TriggerDispatcher
from crm.core.api.pagination import StandardPagination
from crm.core.api.responses import success_response
from crm.core.security.drf import RequiresPermission
from crm.core.security.permissions import PermissionCode
from crm.organizations.selectors.organizations import resolve_current_organization


def _get_rule_or_404(organization, rule_id):
    rule = automation_rule_get_for_organization(organization, rule_id)
    if rule is None:
        raise NotFound("Automation rule not found in current organization")
    return rule


class AutomationRulesView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.TASKS_MANAGE.value

    @extend_schema(responses={200: AutomationRuleSerializer(many=True)})
    def get(self, request):
        organization = resolve_current_organization(request)
        enabled = request.query_params.get("is_enabled")
        queryset = automation_rules_for_organization(
            organization,
            trigger_type=request.query_params.get("trigger_type"),
            is_enabled=None if enabled is None else enabled.lower() == "true",
            ordering=request.query_params.get("ordering", "priority"),
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(AutomationRuleSerializer(page, many=True).data)

    @extend_schema(
        request=AutomationRuleCreateSerializer, responses={201: AutomationRuleSerializer}
    )
    def post(self, request):
        organization = resolve_current_organization(request)
        serializer = AutomationRuleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rule = AutomationRuleService.create(
            organization=organization,
            actor=request.user,
            **serializer.validated_data,
        )
        return success_response(request, AutomationRuleSerializer(rule).data, status=201)


class AutomationRuleDetailView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.TASKS_MANAGE.value

    @extend_schema(responses={200: AutomationRuleSerializer})
    def get(self, request, rule_id):
        organization = resolve_current_organization(request)
        return success_response(
            request, AutomationRuleSerializer(_get_rule_or_404(organization, rule_id)).data
        )

    @extend_schema(
        request=AutomationRuleUpdateSerializer, responses={200: AutomationRuleSerializer}
    )
    def patch(self, request, rule_id):
        organization = resolve_current_organization(request)
        rule = _get_rule_or_404(organization, rule_id)
        serializer = AutomationRuleUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        rule = AutomationRuleService.update(rule=rule, data=dict(serializer.validated_data))
        rule = automation_rule_get_for_organization(organization, rule.id)
        return success_response(request, AutomationRuleSerializer(rule).data)


class AutomationRuleEnableView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.TASKS_MANAGE.value

    @extend_schema(request=None, responses={200: AutomationRuleSerializer})
    def post(self, request, rule_id):
        organization = resolve_current_organization(request)
        rule = AutomationRuleService.set_enabled(
            rule=_get_rule_or_404(organization, rule_id), enabled=True
        )
        return success_response(request, AutomationRuleSerializer(rule).data)


class AutomationRuleDisableView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.TASKS_MANAGE.value

    @extend_schema(request=None, responses={200: AutomationRuleSerializer})
    def post(self, request, rule_id):
        organization = resolve_current_organization(request)
        rule = AutomationRuleService.set_enabled(
            rule=_get_rule_or_404(organization, rule_id), enabled=False
        )
        return success_response(request, AutomationRuleSerializer(rule).data)


class AutomationRunsView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.TASKS_MANAGE.value

    @extend_schema(responses={200: AutomationRunSerializer(many=True)})
    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = automation_runs_for_organization(
            organization,
            rule_id=request.query_params.get("rule_id"),
            status=request.query_params.get("status"),
            trigger_type=request.query_params.get("trigger_type"),
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(AutomationRunSerializer(page, many=True).data)


class AutomationRunDetailView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.TASKS_MANAGE.value

    @extend_schema(responses={200: AutomationRunSerializer})
    def get(self, request, run_id):
        organization = resolve_current_organization(request)
        run = automation_run_get_for_organization(organization, run_id)
        if run is None:
            raise NotFound("Automation run not found in current organization")
        return success_response(request, AutomationRunSerializer(run).data)


class AutomationDispatchView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.TASKS_MANAGE.value

    @extend_schema(
        request=AutomationDispatchSerializer, responses={200: AutomationRunSerializer(many=True)}
    )
    def post(self, request):
        organization = resolve_current_organization(request)
        serializer = AutomationDispatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        runs = TriggerDispatcher.dispatch(
            organization=organization,
            trigger_type=serializer.validated_data["trigger_type"],
            payload=serializer.validated_data["payload"],
            trigger_event_id=serializer.validated_data.get("trigger_event_id", ""),
        )
        return success_response(request, AutomationRunSerializer(runs, many=True).data)
