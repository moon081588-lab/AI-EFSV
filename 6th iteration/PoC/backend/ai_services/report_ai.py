"""Optional C3b report drafting AI adapter."""

from __future__ import annotations

from typing import Any

from .config import AI_ENABLED, MODEL_C3_REPORT
from .fallback import report_drafting_fallback_response
from .llm_client import request_json
from .schemas import C3ReportDraftResponse


SYSTEM_PROMPT = """You are a functional-safety verification report drafting assistant.
Return only a strict JSON object containing scope_summary, safety_context,
traceability_evidence, test_portfolio_summary, anomaly_review_summary,
engineer_decision_summary, limitations, and approval_gate_statement.
Do not include markdown or extra top-level keys. Base every statement only on
the supplied structured evidence. Keep each section concise.
This is draft decision-support text based on simulated evidence. Do not claim
ISO 26262 certification or compliance, production readiness, real ECU or HIL
execution, final safety approval, or completed physical HMI validation.
The backend-provided report_status and approval_gate are authoritative. Never
change or override them."""

REPORT_FIELDS = (
    "scope_summary",
    "safety_context",
    "traceability_evidence",
    "test_portfolio_summary",
    "anomaly_review_summary",
    "engineer_decision_summary",
    "limitations",
    "approval_gate_statement",
)
UNSUPPORTED_CLAIMS = {
    "is iso 26262 certified",
    "has achieved iso 26262 certification",
    "iso 26262 certification achieved",
    "is iso 26262 compliant",
    "iso 26262 compliance achieved",
    "certified compliant",
    "production ready",
    "ready for production",
    "production readiness confirmed",
    "real ecu execution",
    "actual ecu execution",
    "ecu execution completed",
    "real hil execution",
    "actual hil execution",
    "hil execution completed",
    "final safety approval granted",
    "final safety approval confirmed",
    "fully approved for release",
    "physical hmi validation completed",
    "physical hmi validation passed",
    "physical hmi validation is complete",
}
REPORT_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        field_name: {"type": "string"}
        for field_name in REPORT_FIELDS
    },
    "required": list(REPORT_FIELDS),
}


def _validate_report_response(data: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for field_name in REPORT_FIELDS:
        value = str(data.get(field_name, "")).strip()
        if not value:
            raise ValueError(f"{field_name} is required.")
        if len(value) > 1800:
            raise ValueError(f"{field_name} is too long.")
        normalized[field_name] = value

    combined = " ".join(normalized.values()).lower()
    unsupported = sorted(claim for claim in UNSUPPORTED_CLAIMS if claim in combined)
    if unsupported:
        raise ValueError(f"Unsupported report claim detected: {unsupported[0]}.")
    return normalized


def run_c3_report_drafter_ai(report_payload: dict[str, Any]) -> C3ReportDraftResponse:
    if not AI_ENABLED:
        return report_drafting_fallback_response(
            "AI_ENABLED is false.",
            report_payload,
            MODEL_C3_REPORT,
        )

    result = request_json(
        MODEL_C3_REPORT,
        SYSTEM_PROMPT,
        report_payload,
        response_schema=REPORT_RESPONSE_SCHEMA,
    )
    if not result.data:
        return report_drafting_fallback_response(
            result.metadata.fallback_reason or "C3b report AI returned no usable response.",
            report_payload,
            MODEL_C3_REPORT,
        )

    try:
        report_fields = _validate_report_response(result.data)
        return C3ReportDraftResponse(
            **report_fields,
            metadata=result.metadata,
        )
    except Exception as exc:
        return report_drafting_fallback_response(
            f"C3b report AI response validation failed: {exc}",
            report_payload,
            MODEL_C3_REPORT,
        )
