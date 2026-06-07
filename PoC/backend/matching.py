from __future__ import annotations

import difflib
import json
import re
from typing import Any

import pandas as pd

from ai_services.matching_ai import run_c1_matching_ai
from ai_services.prioritizer_ai import run_c2_prioritizer_ai
from config import (
    DOMAIN_TO_TEST_CODES,
    EXTERNAL_HMI_VALIDATION_TERMS,
    MAPPING_REVIEW_THRESHOLD,
    MIN_MAPPING_SELECTION_SCORE,
    READY_APPROVAL_THRESHOLD,
    REFERENCE_MAPPINGS_PATH,
    STOPWORDS,
    TECHNICAL_KEYWORD_GROUPS,
)
from test_cases import TEST_CASES
from traceability import infer_review_status, build_mapping_review_reason_codes


# ---------------------------------------------------------------------------
# Tokenization and keyword helpers
# ---------------------------------------------------------------------------

def tokenize_for_matching(text: str) -> set[str]:
    normalized = re.sub(r"[^a-z0-9]+", " ", str(text).lower())
    tokens = {token for token in normalized.split() if len(token) >= 3 and token not in STOPWORDS}
    return tokens


def detect_keyword_groups(text: str) -> set[str]:
    lowered = str(text).lower()
    groups: set[str] = set()
    for group_name, keywords in TECHNICAL_KEYWORD_GROUPS.items():
        if any(keyword in lowered for keyword in keywords):
            groups.add(group_name)
    return groups


def detect_domain_codes(text: str) -> set[str]:
    lowered = str(text).lower()
    codes: set[str] = set()
    for domain_keyword, test_codes in DOMAIN_TO_TEST_CODES.items():
        if domain_keyword in lowered:
            codes.update(test_codes)
    return codes


def jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def calculate_hybrid_match_score(requirement_text: str, asil_level: str, test_case: pd.Series) -> float:
    test_description = str(test_case["description"])
    test_name = str(test_case["test_case_name"])
    test_case_id = str(test_case["test_case_id"])
    test_code = test_case_id.split("-")[1] if "-" in test_case_id else ""

    sequence_score = difflib.SequenceMatcher(None, requirement_text.lower(), test_description.lower()).ratio()

    requirement_tokens = tokenize_for_matching(requirement_text)
    test_tokens = tokenize_for_matching(f"{test_name} {test_description}")
    token_score = jaccard_similarity(requirement_tokens, test_tokens)

    requirement_groups = detect_keyword_groups(requirement_text)
    test_groups = detect_keyword_groups(test_description)
    group_score = jaccard_similarity(requirement_groups, test_groups)

    domain_codes = detect_domain_codes(requirement_text)
    domain_score = 1.0 if test_code in domain_codes else 0.35 if domain_codes else 0.5

    hybrid_score = (
        0.22 * sequence_score
        + 0.33 * token_score
        + 0.28 * group_score
        + 0.17 * domain_score
    )

    if group_score >= 0.50 or domain_score == 1.0:
        hybrid_score += 0.18
    if token_score >= 0.18:
        hybrid_score += 0.10

    return round(min(0.96, max(0.25, hybrid_score)), 2)


def detect_safety_priority_groups(requirement_text: str) -> set[str]:
    requirement_groups = detect_keyword_groups(requirement_text)
    return requirement_groups & {"fault", "fallback", "threshold", "sensor", "communication", "thermal", "electrical", "memory", "actuator"}


# ---------------------------------------------------------------------------
# Boundary and rationale helpers (also used by candidate_workspace)
# ---------------------------------------------------------------------------

def detect_boundary_clues(requirement_text: str) -> list[str]:
    text = requirement_text.lower()
    clues: list[str] = []

    clue_rules = [
        ("Timing constraint", ["within", "ms", "second", "delay", "latency", "timing", "timeout"]),
        ("Fault detection", ["fault", "failure", "invalid", "inconsistent", "implausible", "corruption"]),
        ("Diagnostic behavior", ["diagnostic", "dtc", "trouble code", "freeze-frame", "response"]),
        ("Fallback or degraded mode", ["fallback", "degraded", "limp-home", "safe state", "disable", "suppression"]),
        ("Threshold condition", ["threshold", "exceeds", "below", "above", "minimum", "maximum", "limit"]),
        ("Driver warning / HMI", ["alert", "warning", "display", "indicator", "telltale", "driver"]),
        ("Redundancy / plausibility", ["redundant", "plausibility", "cross-check", "mismatch"]),
        ("Communication loss", ["communication", "timeout", "signal loss", "unavailable", "message"]),
    ]

    for clue_name, keywords in clue_rules:
        if any(keyword in text for keyword in keywords):
            clues.append(clue_name)

    if not clues:
        clues.append("No explicit boundary clue detected; engineer review should confirm hidden conditions.")

    return clues


def build_ai_rationale(requirement_text: str, test_case_name: str, test_case_description: str, match_score: float) -> str:
    clues = detect_boundary_clues(requirement_text)
    main_clue = clues[0] if clues else "semantic similarity"
    match_score_label = "high" if match_score >= 0.85 else "moderate" if match_score >= 0.70 else "low"

    return (
        f"Matched with a {match_score_label} AI match score because the requirement and candidate test share engineering relevance around "
        f"{main_clue.lower()}, technical keyword overlap, domain relevance, and reusable verification intent. "
        f"The test case '{test_case_name}' was selected as a reusable verification candidate based on: {test_case_description}"
    )


# ---------------------------------------------------------------------------
# Reference data and validation helpers
# ---------------------------------------------------------------------------

def load_reference_mappings() -> list[dict[str, Any]]:
    try:
        payload = json.loads(REFERENCE_MAPPINGS_PATH.read_text(encoding="utf-8"))
        reference_mappings = payload.get("reference_mappings", [])
        return reference_mappings if isinstance(reference_mappings, list) else []
    except (OSError, json.JSONDecodeError, TypeError):
        return []


def requires_external_hmi_validation(requirement_text: str) -> bool:
    normalized = str(requirement_text).lower()
    return any(term in normalized for term in EXTERNAL_HMI_VALIDATION_TERMS)


def normalize_c1_review_status(review_status: str, match_score: float) -> str:
    normalized = str(review_status or "").strip().lower()
    if normalized == "external_validation_required":
        return normalized
    if match_score < MIN_MAPPING_SELECTION_SCORE:
        return "weak_fallback"
    if match_score < MAPPING_REVIEW_THRESHOLD:
        return "review_required"
    if match_score < READY_APPROVAL_THRESHOLD and normalized == "ready":
        return "review_recommended"
    if normalized in {
        "ready",
        "review_recommended",
        "review_required",
        "weak_fallback",
        "external_validation_required",
    }:
        return normalized
    if match_score < READY_APPROVAL_THRESHOLD:
        return "review_recommended"
    return "ready"


def normalize_c1_coverage_type(coverage_type: str, match_score: float) -> str:
    normalized = str(coverage_type or "").strip().lower()
    if normalized in {"direct", "partial", "weak", "external_validation_required"}:
        return normalized
    if match_score >= 0.85:
        return "direct"
    if match_score >= MAPPING_REVIEW_THRESHOLD:
        return "partial"
    return "weak"


def mapping_review_fields_from_match(match: dict[str, Any]) -> dict[str, Any]:
    review_status = str(match.get("review_status", "")).strip().lower()
    reason_codes = [str(code) for code in match.get("reason_codes", [])]
    if review_status in {"review_required", "weak_fallback", "external_validation_required"}:
        mapping_status = "MAPPING_REVIEW_REQUIRED"
    elif review_status == "review_recommended":
        mapping_status = "REVIEW_RECOMMENDED"
    else:
        mapping_status = "READY_FOR_APPROVAL"

    if reason_codes:
        reason = "Mapping review context: " + ", ".join(code.lower().replace("_", " ") for code in reason_codes) + "."
    elif mapping_status == "READY_FOR_APPROVAL":
        reason = "Requirement-to-test mapping score is sufficient for engineer approval."
    else:
        reason = "Engineer review is required before this mapping is used as verification evidence."

    return {
        "mappingReviewStatus": mapping_status,
        "mappingReviewReason": reason,
        "mappingReviewReasonCodes": reason_codes,
        "reviewStatus": review_status or "review_required",
    }


# ---------------------------------------------------------------------------
# Regression risk scoring and prioritization
# ---------------------------------------------------------------------------

def calculate_regression_risk_score(asil_level: str, match_score: float, duration_minutes: int, requirement_text: str = "") -> int:
    asil_weight = {"QM": 5, "A": 15, "B": 25, "C": 35, "D": 45}.get(str(asil_level).upper(), 10)
    match_quality_penalty = 25 if match_score < MAPPING_REVIEW_THRESHOLD else 15 if match_score < READY_APPROVAL_THRESHOLD else 5 if match_score < 0.85 else 0
    safety_priority_groups = detect_safety_priority_groups(requirement_text)
    safety_behavior_weight = min(20, len(safety_priority_groups) * 4)
    duration_weight = min(20, max(0, int(duration_minutes) // 180))
    review_gate_weight = 15 if infer_review_status(asil_level, match_score) == "MANUAL_REVIEW_REQUIRED" else 0
    return min(100, asil_weight + match_quality_penalty + safety_behavior_weight + duration_weight + review_gate_weight)


def build_regression_ranking_reason(asil_level: str, match_score: float, duration_minutes: int, requirement_text: str = "") -> str:
    reasons: list[str] = []
    asil = str(asil_level).upper()
    safety_priority_groups = sorted(detect_safety_priority_groups(requirement_text))

    if asil in {"C", "D"}:
        reasons.append(f"ASIL {asil} safety priority")
    elif asil in {"A", "B"}:
        reasons.append(f"ASIL {asil} verification priority")
    else:
        reasons.append("QM baseline verification priority")

    if safety_priority_groups:
        reasons.append("safety behavior indicators: " + ", ".join(safety_priority_groups[:3]))

    if match_score < MAPPING_REVIEW_THRESHOLD:
        reasons.append("low semantic match score requiring mapping review")
    elif match_score < READY_APPROVAL_THRESHOLD:
        reasons.append("cautious approval range requiring engineer attention")
    elif match_score < 0.85:
        reasons.append("moderate semantic match score")

    if duration_minutes >= 2880:
        reasons.append("long-duration execution effort affecting regression schedule")
    elif duration_minutes >= 360:
        reasons.append("medium-duration execution effort")

    if infer_review_status(asil_level, match_score) == "MANUAL_REVIEW_REQUIRED":
        reasons.append("mapping review required before evidence use")

    return "Prioritized because of " + ", ".join(reasons) + "."


def build_deterministic_priority_factor_scores(
    asil_level: str,
    match_score: float,
    duration_minutes: int,
    requirement_text: str = "",
) -> dict[str, float]:
    return {
        "asil": float({"QM": 5, "A": 15, "B": 25, "C": 35, "D": 45}.get(str(asil_level).upper(), 10)),
        "safety_behavior": float(min(20, len(detect_safety_priority_groups(requirement_text)) * 4)),
        "mapping_uncertainty": float(15 if match_score < MAPPING_REVIEW_THRESHOLD else 8 if match_score < READY_APPROVAL_THRESHOLD else 3 if match_score < 0.85 else 0),
        "duration": float(min(10, max(0, int(duration_minutes) // 360))),
        "review_dependency": float(10 if infer_review_status(asil_level, match_score) == "MANUAL_REVIEW_REQUIRED" else 0),
    }


def infer_mapping_uncertainty(match_score: float) -> str:
    if match_score < MAPPING_REVIEW_THRESHOLD:
        return "high"
    if match_score < 0.85:
        return "medium"
    return "low"


def apply_c2_prioritization(match: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(match)
    asil_level = str(enriched.get("asil_level", "QM"))
    match_score = float(enriched.get("final_match_score", enriched.get("match_score", 0)))
    duration_minutes = int(enriched.get("test_duration_minutes", 0))
    requirement_text = str(enriched.get("requirement_description", ""))
    deterministic_score = calculate_regression_risk_score(
        asil_level,
        match_score,
        duration_minutes,
        requirement_text,
    )
    deterministic_rationale = build_regression_ranking_reason(
        asil_level,
        match_score,
        duration_minutes,
        requirement_text,
    )
    deterministic_factor_scores = build_deterministic_priority_factor_scores(
        asil_level,
        match_score,
        duration_minutes,
        requirement_text,
    )
    review_status = str(enriched.get("review_status", "review_required"))
    priority_payload = {
        "test_case_id": enriched.get("matched_test_case_id"),
        "test_case_name": enriched.get("matched_test_case_name"),
        "test_type": enriched.get("test_type"),
        "linked_requirement": {
            "requirement_id": enriched.get("requirement_id"),
            "description": requirement_text,
            "asil_level": asil_level,
        },
        "match_score": match_score,
        "mapping_uncertainty": infer_mapping_uncertainty(match_score),
        "estimated_duration_minutes": duration_minutes,
        "safety_behavior_indicators": sorted(detect_safety_priority_groups(requirement_text)),
        "review_gate_dependency": review_status,
        "deterministic_risk_score": deterministic_score,
        "deterministic_factor_scores": deterministic_factor_scores,
    }
    c2_response = run_c2_prioritizer_ai(priority_payload)
    c2_metadata = c2_response.metadata.model_dump()
    ai_succeeded = bool(c2_metadata.get("ai_used")) and not bool(c2_metadata.get("fallback_used"))
    ai_priority_score = float(c2_response.ai_priority_score) if ai_succeeded else float(deterministic_score)
    final_priority_score = (
        round(0.65 * ai_priority_score + 0.35 * deterministic_score, 2)
        if ai_succeeded
        else float(deterministic_score)
    )
    priority_rationale = str(c2_response.rationale).strip() if ai_succeeded else deterministic_rationale

    enriched.update(
        {
            "deterministic_regression_risk_score": deterministic_score,
            "ai_priority_score": round(ai_priority_score, 3),
            "final_priority_score": final_priority_score,
            "priority_factor_scores": dict(c2_response.factor_scores) if ai_succeeded else deterministic_factor_scores,
            "priority_rationale": priority_rationale,
            "c2_ai_metadata": dict(c2_metadata),
            "regression_risk_score": final_priority_score,
            "regression_ranking_reason": priority_rationale,
        }
    )
    return enriched


# ---------------------------------------------------------------------------
# Core matching
# ---------------------------------------------------------------------------

def match_requirements(requirements: pd.DataFrame) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    reference_mappings = load_reference_mappings()

    for _, row in requirements.reset_index(drop=True).iterrows():
        requirement_description = str(row["description"]).strip()
        requirement_id = str(row["requirement_id"])
        asil_level = str(row["asil_level"])
        scored_matches: list[dict[str, Any]] = []

        for _, test_case in TEST_CASES.iterrows():
            rounded_score = calculate_hybrid_match_score(requirement_description, asil_level, test_case)
            rounded_score = round(float(rounded_score), 2)
            duration_minutes = int(test_case["duration_minutes"])
            scored_matches.append(
                {
                    "requirement_id": requirement_id,
                    "requirement_description": requirement_description,
                    "asil_level": asil_level,
                    "matched_test_case_id": str(test_case["test_case_id"]),
                    "matched_test_case_name": str(test_case["test_case_name"]),
                    "test_type": str(test_case["test_type"]),
                    "test_duration_minutes": duration_minutes,
                    "test_description": str(test_case["description"]),
                    "legacy_rule_score": rounded_score,
                }
            )

        scored_matches.sort(key=lambda item: item["legacy_rule_score"], reverse=True)
        candidate_pool = scored_matches[:20]
        candidate_tests = [
            {
                "test_case_id": item["matched_test_case_id"],
                "test_case_name": item["matched_test_case_name"],
                "test_type": item["test_type"],
                "description": item["test_description"],
                "duration_minutes": item["test_duration_minutes"],
                "semantic_or_candidate_score": item["legacy_rule_score"],
                "legacy_rule_score": item["legacy_rule_score"],
            }
            for item in candidate_pool
        ]
        legacy_rule_scores = [
            {
                "test_case_id": item["matched_test_case_id"],
                "legacy_rule_score": item["legacy_rule_score"],
                "semantic_or_candidate_score": item["legacy_rule_score"],
            }
            for item in candidate_pool
        ]
        c1_response = run_c1_matching_ai(
            requirement={
                "requirement_id": requirement_id,
                "description": requirement_description,
                "asil_level": asil_level,
            },
            candidate_tests=candidate_tests,
            reference_mappings=reference_mappings,
            legacy_rule_scores=legacy_rule_scores,
        )
        c1_metadata = c1_response.metadata.model_dump()
        ai_succeeded = bool(c1_metadata.get("ai_used")) and not bool(c1_metadata.get("fallback_used"))
        candidate_lookup = {item["matched_test_case_id"]: item for item in scored_matches}
        finalized_matches: list[dict[str, Any]] = []

        for selected in c1_response.selected_mappings:
            test_case_id = str(selected.get("test_case_id", ""))
            candidate = candidate_lookup.get(test_case_id)
            if candidate is None:
                continue

            legacy_rule_score = float(candidate["legacy_rule_score"])
            ai_match_score = float(selected.get("ai_match_score", legacy_rule_score)) if ai_succeeded else legacy_rule_score
            final_match_score = (
                round(0.70 * ai_match_score + 0.15 * legacy_rule_score + 0.15 * legacy_rule_score, 3)
                if ai_succeeded
                else legacy_rule_score
            )
            reason_codes = [str(code) for code in selected.get("reason_codes", [])]
            if c1_metadata.get("fallback_used") and "AI_FALLBACK_USED" not in reason_codes:
                reason_codes.append("AI_FALLBACK_USED")
            if final_match_score < MAPPING_REVIEW_THRESHOLD and "LOW_MATCH_SCORE" not in reason_codes:
                reason_codes.append("LOW_MATCH_SCORE")
            coverage_type = normalize_c1_coverage_type(str(selected.get("coverage_type", "")), final_match_score)
            review_status = normalize_c1_review_status(c1_response.review_status, final_match_score)
            ai_rationale = str(selected.get("rationale", "")).strip() if ai_succeeded else ""
            if not ai_rationale:
                ai_rationale = build_ai_rationale(
                    requirement_description,
                    candidate["matched_test_case_name"],
                    candidate["test_description"],
                    final_match_score,
                )

            if requires_external_hmi_validation(requirement_description):
                coverage_type = "external_validation_required"
                review_status = "external_validation_required"
                if "EXTERNAL_HMI_VALIDATION_REQUIRED" not in reason_codes:
                    reason_codes.append("EXTERNAL_HMI_VALIDATION_REQUIRED")
                ai_rationale += " Physical HMI, visual, or audio behavior requires external validation before evidence approval."

            finalized_matches.append(
                {
                    "requirement_id": requirement_id,
                    "requirement_description": requirement_description,
                    "asil_level": asil_level,
                    "matched_test_case_id": test_case_id,
                    "matched_test_case_name": candidate["matched_test_case_name"],
                    "test_type": candidate["test_type"],
                    "test_duration_minutes": candidate["test_duration_minutes"],
                    "match_score": final_match_score,
                    "ai_match_score": round(ai_match_score, 3),
                    "legacy_rule_score": legacy_rule_score,
                    "final_match_score": final_match_score,
                    "coverage_type": coverage_type,
                    "coverageType": coverage_type,
                    "review_status": review_status,
                    "reviewStatus": review_status,
                    "reason_codes": reason_codes,
                    "reasonCodes": reason_codes,
                    "ai_metadata": dict(c1_metadata),
                    "regression_risk_score": calculate_regression_risk_score(
                        asil_level, final_match_score, candidate["test_duration_minutes"], requirement_description
                    ),
                    "regression_ranking_reason": build_regression_ranking_reason(
                        asil_level, final_match_score, candidate["test_duration_minutes"], requirement_description
                    ),
                    "ai_rationale": ai_rationale,
                }
            )

        selected_matches = [
            match for match in finalized_matches
            if float(match.get("match_score", 0)) >= MIN_MAPPING_SELECTION_SCORE
        ]
        if not selected_matches and scored_matches:
            best = scored_matches[0]
            legacy_score = float(best["legacy_rule_score"])
            fallback_reason = "No C1-selected mapping met the minimum mapping threshold; best legacy candidate used."
            reason_codes = ["WEAK_FALLBACK"]
            coverage_type = "weak"
            review_status = "weak_fallback"
            if requires_external_hmi_validation(requirement_description):
                coverage_type = "external_validation_required"
                review_status = "external_validation_required"
                reason_codes.append("EXTERNAL_HMI_VALIDATION_REQUIRED")
            selected_matches = [
                {
                    "requirement_id": requirement_id,
                    "requirement_description": requirement_description,
                    "asil_level": asil_level,
                    "matched_test_case_id": best["matched_test_case_id"],
                    "matched_test_case_name": best["matched_test_case_name"],
                    "test_type": best["test_type"],
                    "test_duration_minutes": best["test_duration_minutes"],
                    "match_score": legacy_score,
                    "ai_match_score": legacy_score,
                    "legacy_rule_score": legacy_score,
                    "final_match_score": legacy_score,
                    "coverage_type": coverage_type,
                    "coverageType": coverage_type,
                    "review_status": review_status,
                    "reviewStatus": review_status,
                    "reason_codes": reason_codes,
                    "reasonCodes": reason_codes,
                    "ai_metadata": {
                        "ai_used": False,
                        "model_name": c1_metadata.get("model_name"),
                        "fallback_used": True,
                        "fallback_reason": fallback_reason,
                    },
                    "regression_risk_score": calculate_regression_risk_score(
                        asil_level, legacy_score, best["test_duration_minutes"], requirement_description
                    ),
                    "regression_ranking_reason": build_regression_ranking_reason(
                        asil_level, legacy_score, best["test_duration_minutes"], requirement_description
                    ),
                    "ai_rationale": build_ai_rationale(
                        requirement_description,
                        best["matched_test_case_name"],
                        best["test_description"],
                        legacy_score,
                    ),
                }
            ]

        results.extend(apply_c2_prioritization(match) for match in selected_matches[:3])

    return results


# ---------------------------------------------------------------------------
# Summary builder
# ---------------------------------------------------------------------------

def make_summary(matches: list[dict[str, Any]], requirement_count: int) -> dict[str, Any]:
    match_df = pd.DataFrame(matches)
    unique_tests = match_df.drop_duplicates(subset=["matched_test_case_id"]).copy()
    asil_order = {"QM": 0, "A": 1, "B": 2, "C": 3, "D": 4}
    asil_display_order = ["QM", "A", "B", "C", "D"]
    highest_asil = "N/A"

    if "asil_level" in match_df.columns and not match_df["asil_level"].empty:
        highest_asil = max(
            match_df["asil_level"].fillna("N/A").astype(str),
            key=lambda value: asil_order.get(value.upper(), -1),
        )

    requirement_best_matches = (
        match_df.sort_values("match_score", ascending=False)
        .drop_duplicates(subset=["requirement_id"], keep="first")
        .copy()
    )
    requirement_level_df = requirement_best_matches.copy()
    requirement_level_df["asil_level"] = requirement_level_df["asil_level"].fillna("N/A").astype(str).str.upper()
    match_df["asil_level"] = match_df["asil_level"].fillna("N/A").astype(str).str.upper()

    requirement_counts_by_asil = (
        requirement_level_df.groupby("asil_level")
        .size()
        .reindex(asil_display_order, fill_value=0)
        .reset_index(name="count")
        .rename(columns={"asil_level": "asilLevel"})
        .to_dict(orient="records")
    )

    test_type_counts = (
        unique_tests.groupby("test_type")
        .size()
        .reset_index(name="count")
        .rename(columns={"test_type": "testType"})
        .to_dict(orient="records")
    )

    coverage_rows: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    time_rows: list[dict[str, Any]] = []

    for asil_level in asil_display_order:
        asil_requirements = requirement_level_df[requirement_level_df["asil_level"] == asil_level]
        asil_matches = match_df[match_df["asil_level"] == asil_level]
        asil_best_matches = requirement_best_matches[requirement_best_matches["asil_level"] == asil_level]
        asil_unique_tests = asil_matches.drop_duplicates(subset=["matched_test_case_id"])
        covered_count = int(asil_matches["requirement_id"].nunique()) if not asil_matches.empty else 0
        requirement_total = int(len(asil_requirements))
        review_count = int(
            asil_best_matches.loc[asil_best_matches["match_score"] < MAPPING_REVIEW_THRESHOLD, "requirement_id"].nunique()
        ) if not asil_best_matches.empty else 0
        coverage_rate = round((covered_count / requirement_total) * 100, 1) if requirement_total else 0

        coverage_rows.append(
            {
                "asilLevel": asil_level,
                "requirements": requirement_total,
                "covered": covered_count,
                "coverageRate": coverage_rate,
            }
        )
        review_rows.append({"asilLevel": asil_level, "reviewNeeded": review_count})
        time_rows.append(
            {
                "asilLevel": asil_level,
                "estimatedMinutes": int(asil_unique_tests["test_duration_minutes"].sum())
                if not asil_unique_tests.empty
                else 0,
            }
        )

    requirement_match_scores = requirement_best_matches["match_score"]
    confidence_distribution = [
        {
            "label": "High Confidence",
            "range": "0.85-1.00",
            "count": int((requirement_match_scores >= 0.85).sum()),
            "status": "good",
        },
        {
            "label": "Acceptable",
            "range": "0.70-0.84",
            "count": int(((requirement_match_scores >= READY_APPROVAL_THRESHOLD) & (requirement_match_scores < 0.85)).sum()),
            "status": "normal",
        },
        {
            "label": "Review Recommended",
            "range": "0.65-0.69",
            "count": int(((requirement_match_scores >= MAPPING_REVIEW_THRESHOLD) & (requirement_match_scores < READY_APPROVAL_THRESHOLD)).sum()),
            "status": "warning",
        },
        {
            "label": "Mapping Review Required",
            "range": "0.55-0.64",
            "count": int(((requirement_match_scores >= MIN_MAPPING_SELECTION_SCORE) & (requirement_match_scores < MAPPING_REVIEW_THRESHOLD)).sum()),
            "status": "danger",
        },
        {
            "label": "Weak Fallback Only",
            "range": "Below 0.55",
            "count": int((requirement_match_scores < MIN_MAPPING_SELECTION_SCORE).sum()),
            "status": "danger",
        },
    ]

    review_items_df = requirement_best_matches[
        requirement_best_matches["match_score"] < MAPPING_REVIEW_THRESHOLD
    ].head(12)

    review_items = [
        {
            "requirementId": str(row["requirement_id"]),
            "asilLevel": str(row["asil_level"]),
            "matchedTestCaseId": str(row["matched_test_case_id"]),
            "matchedTestCaseName": str(row["matched_test_case_name"]),
            "confidence": float(row["match_score"]),
            "mappingReviewReasonCodes": build_mapping_review_reason_codes(
                float(row["match_score"]),
                str(row.get("requirement_description", "")),
                str(row.get("ai_rationale", "")),
            ),
            "action": "Mapping Review Required",
        }
        for _, row in review_items_df.iterrows()
    ]

    longest_tests = (
        unique_tests.sort_values("test_duration_minutes", ascending=False)
        .head(10)[
            ["matched_test_case_id", "matched_test_case_name", "test_type", "test_duration_minutes"]
        ]
        .rename(
            columns={
                "matched_test_case_id": "testCaseId",
                "matched_test_case_name": "testCaseName",
                "test_type": "testType",
                "test_duration_minutes": "durationMinutes",
            }
        )
        .to_dict(orient="records")
    )

    top_reused_tests = (
        match_df.groupby(["matched_test_case_id", "matched_test_case_name", "test_type"])
        .size()
        .reset_index(name="mappedRequirements")
        .sort_values("mappedRequirements", ascending=False)
        .head(10)
        .rename(
            columns={
                "matched_test_case_id": "testCaseId",
                "matched_test_case_name": "testCaseName",
                "test_type": "testType",
            }
        )
        .to_dict(orient="records")
    )

    total_mappings = int(len(match_df))
    low_confidence_count = int((match_df["match_score"] < MAPPING_REVIEW_THRESHOLD).sum())
    review_needed_requirements = int(
        requirement_best_matches.loc[
            requirement_best_matches["match_score"] < MAPPING_REVIEW_THRESHOLD,
            "requirement_id",
        ].nunique()
    )
    high_risk_requirement_count = int(requirement_level_df["asil_level"].isin(["C", "D"]).sum())
    high_risk_review_count = int(
        match_df.loc[
            (match_df["asil_level"].isin(["C", "D"])) & (match_df["match_score"] < 0.70),
            "requirement_id",
        ].nunique()
    )
    total_test_time_minutes = int(unique_tests["test_duration_minutes"].sum())
    average_match_score = round(float(match_df["match_score"].mean()), 3) if total_mappings else 0
    coverage_rate = round((match_df["requirement_id"].nunique() / requirement_count) * 100, 1) if requirement_count else 0
    test_reuse_ratio = round(total_mappings / len(unique_tests), 2) if len(unique_tests) else 0
    average_tests_per_requirement = round(total_mappings / requirement_count, 2) if requirement_count else 0

    executive_summary = (
        f"The uploaded requirement set contains {requirement_count} software safety requirements. "
        f"{coverage_rate}% are currently linked to candidate test coverage across {len(unique_tests)} unique test cases. "
        f"Average AI match score is {round(average_match_score * 100, 1)}%, with "
        f"{review_needed_requirements} requirements requiring engineer review. "
        f"ASIL {highest_asil} is the highest observed safety level, and estimated unique test execution time is "
        f"{round(total_test_time_minutes / 60, 1)} hours."
    )

    return {
        "requirementsUploaded": requirement_count,
        "requirementTestMappings": total_mappings,
        "uniqueTestCases": len(unique_tests),
        "totalTestTimeMinutes": total_test_time_minutes,
        "highestAsilLevel": highest_asil,
        "coverageRate": coverage_rate,
        "averageConfidence": average_match_score,
        "averageMatchScore": average_match_score,
        "lowConfidenceCount": low_confidence_count,
        "reviewNeededRequirements": review_needed_requirements,
        "reviewNeeded": review_needed_requirements,
        "reviewNeededCount": review_needed_requirements,
        "lowConfidenceRequirementCount": review_needed_requirements,
        "highRiskRequirementCount": high_risk_requirement_count,
        "highRiskReviewCount": high_risk_review_count,
        "testReuseRatio": test_reuse_ratio,
        "averageTestsPerRequirement": average_tests_per_requirement,
        "requirementsFullyCovered": int(match_df["requirement_id"].nunique()),
        "uncoveredRequirements": int(max(requirement_count - match_df["requirement_id"].nunique(), 0)),
        "executiveSummary": executive_summary,
        "asilCounts": requirement_counts_by_asil,
        "requirementCountsByAsil": requirement_counts_by_asil,
        "testTypeCounts": test_type_counts,
        "coverageByAsil": coverage_rows,
        "reviewNeededByAsil": review_rows,
        "estimatedTestTimeByAsil": time_rows,
        "confidenceDistribution": confidence_distribution,
        "reviewItems": review_items,
        "longestTests": longest_tests,
        "topReusedTests": top_reused_tests,
    }
