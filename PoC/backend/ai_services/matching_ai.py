"""Optional C1 requirement-to-test matching AI adapter."""

from __future__ import annotations

from typing import Any

from .config import AI_ENABLED, MODEL_C1_MATCHING
from .fallback import matching_fallback_response
from .llm_client import request_json
from .schemas import C1MatchingResponse


SYSTEM_PROMPT = """You are a software verification matching assistant.
Your task is to select the best requirement-to-test mappings from the supplied
candidate_tests.
Return only a strict JSON object with selected_mappings and review_status.
Do not include markdown, prose outside the JSON object, or extra top-level keys.
Each selected mapping must contain test_case_id, ai_match_score, coverage_type,
rationale, and reason_codes. coverage_type must be direct, partial, weak, or
external_validation_required. review_status must be ready,
review_recommended, review_required, weak_fallback, or
external_validation_required.
Base selections only on the supplied requirement, candidate tests, references,
and legacy scores. Do not invent test case identifiers.
When candidate_tests is non-empty, selected_mappings must contain between one
and three candidate test_case_id values. Never return an empty selected_mappings
list. If no candidate is strong, select the best available candidate with
coverage_type weak and review_status weak_fallback.
ai_match_score is your independent assessment of mapping quality and may differ
from semantic_or_candidate_score and legacy_rule_score.
Required JSON shape:
{"selected_mappings":[{"test_case_id":"candidate ID","ai_match_score":0.0,
"coverage_type":"direct","rationale":"concise explanation",
"reason_codes":[]}],"review_status":"ready"}"""

VALID_COVERAGE_TYPES = {"direct", "partial", "weak", "external_validation_required"}
VALID_REVIEW_STATUSES = {
    "ready",
    "review_recommended",
    "review_required",
    "weak_fallback",
    "external_validation_required",
}
C1_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "selected_mappings": {
            "type": "array",
            "minItems": 1,
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "test_case_id": {"type": "string"},
                    "ai_match_score": {"type": "number", "minimum": 0, "maximum": 1},
                    "coverage_type": {"type": "string", "enum": sorted(VALID_COVERAGE_TYPES)},
                    "rationale": {"type": "string"},
                    "reason_codes": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["test_case_id", "ai_match_score", "coverage_type", "rationale", "reason_codes"],
            },
        },
        "review_status": {"type": "string", "enum": sorted(VALID_REVIEW_STATUSES)},
    },
    "required": ["selected_mappings", "review_status"],
}


def _validate_ai_response(
    data: dict[str, Any],
    candidate_tests: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    selected_mappings = data.get("selected_mappings")
    review_status = str(data.get("review_status", "")).strip().lower()
    if not isinstance(selected_mappings, list) or not selected_mappings:
        raise ValueError("selected_mappings must be a non-empty list.")
    if review_status not in VALID_REVIEW_STATUSES:
        raise ValueError("review_status is missing or invalid.")

    candidate_ids = {str(item.get("test_case_id", "")) for item in candidate_tests}
    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in selected_mappings:
        if not isinstance(item, dict):
            raise ValueError("Each selected mapping must be an object.")

        test_case_id = str(item.get("test_case_id", "")).strip()
        if not test_case_id or test_case_id not in candidate_ids:
            raise ValueError(f"AI selected invalid test_case_id: {test_case_id or 'missing'}.")
        if test_case_id in seen_ids:
            continue

        ai_match_score = float(item.get("ai_match_score"))
        if not 0.0 <= ai_match_score <= 1.0:
            raise ValueError(f"AI match score for {test_case_id} must be between 0 and 1.")

        coverage_type = str(item.get("coverage_type", "")).strip().lower()
        if coverage_type not in VALID_COVERAGE_TYPES:
            raise ValueError(f"AI coverage_type for {test_case_id} is invalid.")

        reason_codes = item.get("reason_codes", [])
        if not isinstance(reason_codes, list):
            raise ValueError(f"AI reason_codes for {test_case_id} must be a list.")

        normalized.append(
            {
                "test_case_id": test_case_id,
                "ai_match_score": round(ai_match_score, 3),
                "coverage_type": coverage_type,
                "rationale": str(item.get("rationale", "")).strip(),
                "reason_codes": [str(code) for code in reason_codes],
            }
        )
        seen_ids.add(test_case_id)

    if not normalized:
        raise ValueError("AI response contained no valid selected mappings.")
    return normalized, review_status


def run_c1_matching_ai(
    requirement: dict[str, Any],
    candidate_tests: list[dict[str, Any]],
    reference_mappings: list[dict[str, Any]] | None = None,
    legacy_rule_scores: list[dict[str, Any]] | None = None,
) -> C1MatchingResponse:
    if not AI_ENABLED:
        return matching_fallback_response(
            "AI_ENABLED is false.",
            legacy_rule_scores,
            MODEL_C1_MATCHING,
        )

    compact_candidates = [
        {
            "test_case_id": candidate.get("test_case_id"),
            "test_case_name": candidate.get("test_case_name"),
            "test_type": candidate.get("test_type"),
            "description": candidate.get("description"),
            "semantic_or_candidate_score": candidate.get("semantic_or_candidate_score"),
            "legacy_rule_score": candidate.get("legacy_rule_score"),
        }
        for candidate in candidate_tests[:10]
    ]
    compact_legacy_scores = [
        {
            "test_case_id": item.get("test_case_id"),
            "legacy_rule_score": item.get("legacy_rule_score"),
        }
        for item in (legacy_rule_scores or [])[:10]
    ]
    result = request_json(
        MODEL_C1_MATCHING,
        SYSTEM_PROMPT,
        {
            "task": "Select one to three best candidate test mappings for this requirement.",
            "requirement": requirement,
            "candidate_tests": compact_candidates,
            "reference_mappings": (reference_mappings or [])[:8],
            "legacy_rule_scores": compact_legacy_scores,
        },
        response_schema=C1_RESPONSE_SCHEMA,
    )
    if not result.data:
        return matching_fallback_response(
            result.metadata.fallback_reason or "C1 matching AI returned no usable response.",
            legacy_rule_scores,
            MODEL_C1_MATCHING,
        )

    try:
        selected_mappings, review_status = _validate_ai_response(result.data, candidate_tests)
        return C1MatchingResponse(
            selected_mappings=selected_mappings,
            review_status=review_status,
            metadata=result.metadata,
        )
    except Exception as exc:
        return matching_fallback_response(
            f"C1 matching AI response validation failed: {exc}",
            legacy_rule_scores,
            MODEL_C1_MATCHING,
        )
