"""SupportTriageService: deterministic priority/category, optionally refined by AI.

Rules run first (keywords + support level). When an AI extraction is available
its category fills gaps and its priority can only RAISE — never silently lower —
the deterministic result. The backend always owns the final classification.
"""

from crm.support.domain import policies
from crm.support.domain.enums import (
    TicketCategory,
    TicketPriority,
    TicketStatus,
    max_priority,
)
from crm.support.domain.rules import normalize
from crm.support.domain.value_objects import TriageResult

from .support_policy import SupportPolicyAdapter

_BUMP = {
    TicketPriority.LOW.value: TicketPriority.MEDIUM.value,
    TicketPriority.MEDIUM.value: TicketPriority.HIGH.value,
    TicketPriority.HIGH.value: TicketPriority.URGENT.value,
}


class SupportTriageService:
    @staticmethod
    def triage(
        *,
        text: str,
        organization_id=None,
        support_level: str | None = None,
        ai_priority: str | None = None,
        ai_category: str | None = None,
        missing_information: list[str] | None = None,
    ) -> TriageResult:
        normalized = normalize(text)
        reasons: list[str] = []

        category = TicketCategory.UNKNOWN.value
        for candidate, keywords in policies.CATEGORY_KEYWORDS.items():
            if any(keyword in normalized for keyword in keywords):
                category = candidate
                reasons.append(f"keyword_category:{candidate}")
                break
        if category == TicketCategory.UNKNOWN.value and ai_category in TicketCategory.values:
            category = ai_category

        priority = policies.default_priority()
        org_urgent = [normalize(k) for k in SupportPolicyAdapter.urgent_keywords(organization_id)]
        if any(keyword in normalized for keyword in policies.CRITICAL_KEYWORDS):
            priority = TicketPriority.CRITICAL.value
            reasons.append("critical_keyword")
        elif any(keyword in normalized for keyword in policies.URGENT_KEYWORDS) or any(
            keyword and keyword in normalized for keyword in org_urgent
        ):
            priority = TicketPriority.URGENT.value
            reasons.append("urgent_keyword")

        if (
            support_level in policies.ELEVATING_SUPPORT_LEVELS
            and priority in _BUMP
            and priority not in (TicketPriority.URGENT.value, TicketPriority.CRITICAL.value)
        ):
            priority = _BUMP[priority]
            reasons.append(f"support_level_elevation:{support_level}")

        # AI may raise priority but never lower it.
        if ai_priority in TicketPriority.values:
            raised = max_priority(priority, ai_priority)
            if raised != priority:
                reasons.append(f"ai_raised_priority:{ai_priority}")
                priority = raised

        suggested_status = None
        if missing_information:
            suggested_status = TicketStatus.WAITING_CLIENT.value
            reasons.append("missing_information")

        requires_owner = priority in (
            TicketPriority.URGENT.value,
            TicketPriority.CRITICAL.value,
        ) or (support_level == "vip" and priority == TicketPriority.HIGH.value)

        return TriageResult(
            priority=priority,
            category=category,
            reasons=reasons,
            requires_owner_notification=requires_owner,
            suggested_status=suggested_status,
        )
