from __future__ import annotations

from typing import Any

from config import MAPPING_REVIEW_THRESHOLD, READY_APPROVAL_THRESHOLD


def infer_coverage_type(match_score: float) -> str:
    if match_score >= 0.85:
        return "Direct Coverage"
    if match_score >= READY_APPROVAL_THRESHOLD:
        return "Partial Coverage"
    if match_score >= MAPPING_REVIEW_THRESHOLD:
        return "Candidate Coverage - Review Recommended"
    return "Candidate Coverage - Mapping Review Required"


def infer_review_status(asil_level: str, match_score: float) -> str:
    score = float(match_score or 0)
    if score < MAPPING_REVIEW_THRESHOLD:
        return "MANUAL_REVIEW_REQUIRED"
    if score < READY_APPROVAL_THRESHOLD:
        return "REVIEW_RECOMMENDED"
    return "READY_FOR_APPROVAL"


def build_mapping_review_reason_codes(match_score: float, requirement_text: str = "", ai_rationale: str = "") -> list[str]:
    normalized_score = float(match_score or 0)
    searchable_text = f"{requirement_text} {ai_rationale}".lower()
    reason_codes: list[str] = []

    if normalized_score < MAPPING_REVIEW_THRESHOLD:
        reason_codes.append("LOW_MATCH_SCORE")
    if any(term in searchable_text for term in ["ambiguous", "unclear", "not clear", "uncertain"]):
        reason_codes.append("AMBIGUOUS_REQUIREMENT")
    if any(term in searchable_text for term in ["weak match", "weak", "limited overlap", "low overlap"]):
        reason_codes.append("WEAK_DOMAIN_ALIGNMENT")
    if any(term in searchable_text for term in ["missing expected response", "expected response missing", "no expected response"]):
        reason_codes.append("MISSING_EXPECTED_RESPONSE")
    if any(term in searchable_text for term in ["no strong historical", "no historical", "no reusable", "insufficient historical"]):
        reason_codes.append("NO_STRONG_HISTORICAL_TEST")

    return reason_codes


def describe_mapping_review_reason(reason_codes: list[str]) -> str:
    if not reason_codes:
        return "Requirement-to-test mapping score is sufficient for engineer approval."

    reason_labels = {
        "LOW_MATCH_SCORE": "low semantic match score",
        "AMBIGUOUS_REQUIREMENT": "ambiguous requirement wording",
        "WEAK_DOMAIN_ALIGNMENT": "weak domain alignment",
        "MISSING_EXPECTED_RESPONSE": "missing or unclear expected response",
        "NO_STRONG_HISTORICAL_TEST": "no strong reusable historical test evidence",
    }
    readable_reasons = [reason_labels.get(code, code.lower().replace("_", " ")) for code in reason_codes]
    return "Mapping review required because of " + ", ".join(readable_reasons) + "."


def infer_mapping_review_status(match_score: float, requirement_text: str = "", ai_rationale: str = "") -> dict[str, Any]:
    reason_codes = build_mapping_review_reason_codes(match_score, requirement_text, ai_rationale)
    if reason_codes:
        return {
            "mappingReviewStatus": "MAPPING_REVIEW_REQUIRED",
            "reviewStatus": "MANUAL_REVIEW_REQUIRED",
            "mappingReviewReason": describe_mapping_review_reason(reason_codes),
            "mappingReviewReasonCodes": reason_codes,
        }
    score = float(match_score or 0)
    review_status = "REVIEW_RECOMMENDED" if score < READY_APPROVAL_THRESHOLD else "READY_FOR_APPROVAL"
    mapping_status = "REVIEW_RECOMMENDED" if score < READY_APPROVAL_THRESHOLD else "READY_FOR_APPROVAL"
    reason = "Review recommended before approval because the mapping score is in the cautious approval range." if score < READY_APPROVAL_THRESHOLD else describe_mapping_review_reason([])
    return {
        "mappingReviewStatus": mapping_status,
        "reviewStatus": review_status,
        "mappingReviewReason": reason,
        "mappingReviewReasonCodes": [],
    }
