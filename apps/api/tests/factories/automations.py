import uuid

import factory

from crm.automations.domain.enums import AutomationRunStatus, AutomationTriggerType
from crm.automations.models import AutomationRule, AutomationRun


class AutomationRuleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AutomationRule

    organization_id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Rule {n}")
    trigger_type = AutomationTriggerType.MESSAGE_RECEIVED


class AutomationRunFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AutomationRun

    rule = factory.SubFactory(AutomationRuleFactory)
    organization_id = factory.SelfAttribute("rule.organization_id")
    trigger_type = AutomationTriggerType.MESSAGE_RECEIVED
    status = AutomationRunStatus.SUCCESS
