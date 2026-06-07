"""Deterministic fallback responses for optional AI services."""

from __future__ import annotations

from typing import Any

from .schemas import (
    AIMetadata,
    C1MatchingResponse,
    C2PrioritizationResponse,
    C3AnomalyResponse,
    C3ReportDraftResponse,
)


def _metadata(reason: str, model_name: str | None = None) -> AIMetadata:
    return AIMetadata(
        ai_used=False,
        model_name=model_name,
        fallback_used=True,
        fallback_reason=reason,
    )


def matching_fallback_response(
    reason: str,
    legacy_rule_scores: list[dict[str, Any]] | None = None,
    model_name: str | None = None,
) -> C1MatchingResponse:
    selected = list(legacy_rule_scores or [])
    return C1MatchingResponse(
        selected_mappings=selected,
        review_status="MANUAL_REVIEW_REQUIRED",
        metadata=_metadata(reason, model_name),
    )


def prioritization_fallback_response(
    reason: str,
    priority_payload: dict[str, Any] | None = None,
    model_name: str | None = None,
) -> C2PrioritizationResponse:
    payload = priority_payload or {}
    score = float(
        payload.get(
            "deterministic_risk_score",
            payload.get("legacy_priority_score", payload.get("regression_risk_score", 0)),
        )
        or 0
    )
    return C2PrioritizationResponse(
        ai_priority_score=score,
        factor_scores=dict(payload.get("deterministic_factor_scores", payload.get("factor_scores", {}))),
        rationale="Deterministic legacy priority data returned because the AI prioritizer was unavailable.",
        metadata=_metadata(reason, model_name),
    )


def anomaly_fallback_response(
    reason: str,
    observation_payload: dict[str, Any] | None = None,
    model_name: str | None = None,
) -> C3AnomalyResponse:
    payload = observation_payload or {}
    observed_behavior = str(
        payload.get("observed_behavior", payload.get("measured_value", "Observation requires manual review."))
    )
    return C3AnomalyResponse(
        verdict="REVIEW",
        anomaly_type="Manual Review Required",
        confidence=0.0,
        observed_behavior=observed_behavior,
        explanation="No AI anomaly judgment was produced; the observation was routed to manual review.",
        recommended_engineer_action="Review the observation and supporting evidence manually.",
        metadata=_metadata(reason, model_name),
    )


def report_drafting_fallback_response(
    reason: str,
    report_payload: dict[str, Any] | None = None,
    model_name: str | None = None,
) -> C3ReportDraftResponse:
    payload = report_payload or {}
    return C3ReportDraftResponse(
        scope_summary=str(payload.get("scope_summary", "Report scope requires deterministic drafting.")),
        safety_context=str(payload.get("safety_context", "Safety context requires engineer review.")),
        traceability_evidence=str(payload.get("traceability_evidence", "Traceability evidence summary unavailable.")),
        test_portfolio_summary=str(payload.get("test_portfolio_summary", "Test portfolio summary unavailable.")),
        anomaly_review_summary=str(payload.get("anomaly_review_summary", "Anomaly review summary unavailable.")),
        engineer_decision_summary=str(payload.get("engineer_decision_summary", "Engineer decision summary unavailable.")),
        limitations=str(
            payload.get(
                "limitations",
                "AI report drafting was not used. Verify all report content manually.",
            )
        ),
        approval_gate_statement=str(
            payload.get(
                "approval_gate_statement",
                "Human approval is required before this draft can be used as verification evidence.",
            )
        ),
        metadata=_metadata(reason, model_name),
    )
