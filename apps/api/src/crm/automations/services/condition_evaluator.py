from crm.automations.domain.rules import evaluate_operator, get_path
from crm.automations.domain.value_objects import ConditionResult


class ConditionEvaluator:
    @staticmethod
    def evaluate_condition(*, condition, payload: dict) -> ConditionResult:
        actual = get_path(payload, condition.field_path)
        passed = evaluate_operator(actual, condition.operator, condition.expected_value)
        reason = (
            f"{condition.field_path} {condition.operator} {condition.expected_value}"
            if passed
            else f"condition_failed:{condition.field_path}"
        )
        return ConditionResult(passed=passed, reason=reason)

    @staticmethod
    def evaluate_inline(*, raw_condition: dict, payload: dict) -> ConditionResult:
        field_path = str(raw_condition.get("field") or raw_condition.get("field_path") or "")
        operator = str(raw_condition.get("operator") or "eq")
        expected = raw_condition.get("value", raw_condition.get("expected_value"))
        actual = get_path(payload, field_path)
        passed = evaluate_operator(actual, operator, expected)
        return ConditionResult(
            passed=passed,
            reason=f"{field_path} {operator} {expected}"
            if passed
            else f"condition_failed:{field_path}",
        )
