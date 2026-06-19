"""KnownIssueMatcher: suggest a related active known issue (never auto-closes)."""

from dataclasses import dataclass

from crm.support.domain.enums import KnownIssueStatus
from crm.support.domain.rules import normalize
from crm.support.models import SupportKnownIssue


@dataclass(frozen=True)
class KnownIssueMatch:
    known_issue_id: str
    title: str
    score: int


class KnownIssueMatcher:
    @staticmethod
    def match(*, organization_id, text: str, category: str | None = None) -> KnownIssueMatch | None:
        normalized = normalize(text)
        candidates = SupportKnownIssue.objects.filter(
            organization_id=organization_id,
            status__in=[KnownIssueStatus.ACTIVE, KnownIssueStatus.MONITORING],
        )
        if category:
            candidates = candidates.filter(category=category)

        best: KnownIssueMatch | None = None
        for issue in candidates:
            keywords = [normalize(k) for k in (issue.matching_keywords or [])]
            score = sum(1 for keyword in keywords if keyword and keyword in normalized)
            if score and (best is None or score > best.score):
                best = KnownIssueMatch(known_issue_id=str(issue.id), title=issue.title, score=score)
        return best
