"""EvalRunner: deterministic evaluation of prompts/schemas/safety.

Each dataset case carries the model output to evaluate (``model_output``) plus
the inbound text. The runner validates the output against the purpose schema,
runs SafetyGuard, compares against ``expected_behavior`` / ``expected_output``
and persists an AIEvalResult. No real providers are ever called.
"""

import logging
from decimal import Decimal
from pathlib import Path

import yaml
from django.utils import timezone

from crm.ai.domain.enums import AIPurpose, SafetyDecision
from crm.ai.models import AIEvalCase, AIEvalResult
from crm.ai.services.safety_guard import SafetyGuard
from crm.ai.services.structured_output import StructuredOutputValidator

logger = logging.getLogger(__name__)

DATASETS_DIR = Path(__file__).resolve().parent.parent / "evals" / "datasets"

SUITES = {
    "sales_agent": "sales_conversations.yaml",
    "support_agent": "support_cases.yaml",
    "support_audio_transcripts": "support_audio_transcripts.yaml",
    "lead_scoring": "lead_scoring_cases.yaml",
    "task_extraction": "task_extraction_cases.yaml",
    "risk_classifier": "risk_cases.yaml",
    "audio_ticket": "audio_ticket_cases.yaml",
    "objection_handling": "objection_handling_cases.yaml",
    "handoff_cases": "handoff_cases.yaml",
}

_REPLY_PURPOSES = {AIPurpose.SALES_REPLY.value, AIPurpose.SUPPORT_REPLY.value}


class EvalRunner:
    @staticmethod
    def seed_suite(*, organization_id, suite_name: str) -> int:
        """Load a YAML dataset into AIEvalCase rows (idempotent by case key)."""
        filename = SUITES.get(suite_name)
        if filename is None:
            raise ValueError(f"Unknown eval suite '{suite_name}'")
        data = yaml.safe_load((DATASETS_DIR / filename).read_text(encoding="utf-8"))
        created = 0
        for case in data.get("cases", []):
            _, was_created = AIEvalCase.objects.get_or_create(
                organization_id=organization_id,
                suite_name=suite_name,
                case_key=case["key"],
                defaults={
                    "purpose": data["purpose"],
                    "input_payload": case.get("input", {}),
                    "expected_output": case.get("expected_output"),
                    "expected_behavior": case.get("expected_behavior", ""),
                    "tags": case.get("tags", []),
                },
            )
            created += int(was_created)
        return created

    @staticmethod
    def run_case(case: AIEvalCase) -> AIEvalResult:
        payload = case.input_payload or {}
        model_output = payload.get("model_output") or {}
        inbound_text = str(payload.get("inbound_text", ""))
        metrics: dict = {}
        passed = True
        error = ""

        validation = StructuredOutputValidator.validate(case.purpose, model_output)
        metrics["schema_valid"] = validation.is_valid

        decision = SafetyDecision.SEND.value
        if case.purpose in _REPLY_PURPOSES or case.purpose == AIPurpose.RISK_CLASSIFICATION.value:
            safety = SafetyGuard.evaluate_reply(
                organization_id=case.organization_id,
                proposed_reply=str(model_output.get("reply", payload.get("proposed_reply", ""))),
                inbound_text=inbound_text,
                model_risk_level=str(model_output.get("risk_level", "low")),
                model_requests_handoff=bool(model_output.get("should_handoff", False)),
            )
            decision = safety.decision
            metrics["safety_decision"] = decision
            metrics["risk_level"] = safety.risk_level

        if case.expected_behavior == "schema_invalid":
            passed = not validation.is_valid
        elif case.expected_behavior == "schema_valid":
            passed = validation.is_valid
        elif case.expected_behavior:
            passed = validation.is_valid and decision == case.expected_behavior
            metrics["expected_decision"] = case.expected_behavior

        expected_output = case.expected_output or {}
        if passed and expected_output and validation.is_valid:
            data = validation.data or {}
            for key, expected_value in expected_output.items():
                if key == "tasks_count":
                    actual = len(data.get("tasks", []))
                    metrics["tasks_count"] = actual
                    if actual != expected_value:
                        passed = False
                elif data.get(key) != expected_value:
                    metrics[f"mismatch_{key}"] = data.get(key)
                    passed = False

        return AIEvalResult.objects.create(
            organization_id=case.organization_id,
            eval_case=case,
            provider="fake",
            model="eval",
            actual_output={"output": model_output, "decision": decision},
            passed=passed,
            score=Decimal("1") if passed else Decimal("0"),
            metrics=metrics,
            error_message=error,
        )

    @classmethod
    def run_suite(cls, *, organization_id, suite_name: str) -> dict:
        cls.seed_suite(organization_id=organization_id, suite_name=suite_name)
        cases = AIEvalCase.objects.filter(
            organization_id=organization_id, suite_name=suite_name, is_active=True
        )
        results = [cls.run_case(case) for case in cases]
        total = len(results)
        passed = sum(1 for result in results if result.passed)
        schema_valid = sum(1 for result in results if result.metrics.get("schema_valid"))
        report = {
            "suite": suite_name,
            "total": total,
            "passed": passed,
            "pass_rate": round(passed / total, 4) if total else None,
            "schema_validity_rate": round(schema_valid / total, 4) if total else None,
            "ran_at": timezone.now().isoformat(),
        }
        logger.info(
            "Eval suite finished",
            extra={"event": "ai.eval_suite_finished", "metadata": report},
        )
        return report

    @classmethod
    def run_all(cls, *, organization_id) -> list[dict]:
        return [
            cls.run_suite(organization_id=organization_id, suite_name=suite) for suite in SUITES
        ]
