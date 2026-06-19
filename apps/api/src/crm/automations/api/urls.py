from django.urls import path

from .views import (
    AutomationDispatchView,
    AutomationRuleDetailView,
    AutomationRuleDisableView,
    AutomationRuleEnableView,
    AutomationRulesView,
    AutomationRunDetailView,
    AutomationRunsView,
)

urlpatterns = [
    path("rules/", AutomationRulesView.as_view(), name="automation-rules"),
    path(
        "rules/<uuid:rule_id>/", AutomationRuleDetailView.as_view(), name="automation-rule-detail"
    ),
    path(
        "rules/<uuid:rule_id>/enable/",
        AutomationRuleEnableView.as_view(),
        name="automation-rule-enable",
    ),
    path(
        "rules/<uuid:rule_id>/disable/",
        AutomationRuleDisableView.as_view(),
        name="automation-rule-disable",
    ),
    path("runs/", AutomationRunsView.as_view(), name="automation-runs"),
    path("runs/<uuid:run_id>/", AutomationRunDetailView.as_view(), name="automation-run-detail"),
    path("dispatch/", AutomationDispatchView.as_view(), name="automation-dispatch"),
]
