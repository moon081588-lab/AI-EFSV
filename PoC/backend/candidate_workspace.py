from __future__ import annotations

import re
from typing import Any

import pandas as pd

from ai_services.generate_tc_ai import generate_test_case_ai
from matching import (
    build_ai_rationale,
    calculate_hybrid_match_score,
    calculate_regression_risk_score,
    detect_boundary_clues,
    mapping_review_fields_from_match,
)
from test_cases import TEST_CASES
from traceability import infer_coverage_type, infer_mapping_review_status

# Requirements whose best match falls below this threshold get an AI-generated TC.
GENERATE_TC_THRESHOLD = 0.60


def decompose_requirement_clauses(requirement_id: str, requirement_text: str) -> list[dict[str, Any]]:
    text = str(requirement_text).strip()
    if not text:
        return []

    # Normalize whitespace
    normalized = re.sub(r"\s+", " ", text).strip()
    split_pattern = (
        r"\s*(?:;|\.|\band\b(?=\s+(?:detect|store|record|alert|warn|display|enter|transition|disable|enable|limit|reduce|suppress|open|close|fallback|communicate|verify|monitor|prevent|maintain|trigger|request|set|reset)\b))\s*"
    )
    raw_parts = [
        part.strip(" ,.;")
        for part in re.split(split_pattern, normalized, flags=re.IGNORECASE)
        if part.strip(" ,.;")
    ]

    if len(raw_parts) <= 1:
        raw_parts = [normalized]

    clauses: list[dict[str, Any]] = []
    for index, clause_text in enumerate(raw_parts, start=1):
        if len(clause_text) < 8:
            continue
        boundary_clues = detect_boundary_clues(clause_text)
        clauses.append(
            {
                "clauseId": f"{requirement_id}-C{index:02d}",
                "clauseText": clause_text,
                "verificationIntent": boundary_clues[0] if boundary_clues else "Requirement behavior",
                "boundaryClues": boundary_clues,
            }
        )

    if not clauses:
        clauses.append(
            {
                "clauseId": f"{requirement_id}-C01",
                "clauseText": normalized,
                "verificationIntent": "Requirement behavior",
                "boundaryClues": detect_boundary_clues(normalized),
            }
        )

    return clauses


def generate_candidate_test_case(requirement_id: str, requirement_text: str, asil_level: str, boundary_clues: list[str]) -> dict[str, Any]:
    primary_clue = boundary_clues[0] if boundary_clues else "Requirement behavior"
    normalized_asil = str(asil_level).upper()

    return {
        "candidateTestCaseId": f"AI-{requirement_id}",
        "candidateTestCaseName": f"AI-Derived Verification for {requirement_id}",
        "objective": f"Verify that the ECU software satisfies the requirement behavior related to {primary_clue.lower()}.",
        "precondition": "Target ECU variant is configured with the required software baseline, diagnostic session, and applicable safety configuration.",
        "procedure": [
            "Load the target ECU software configuration and confirm diagnostic communication availability.",
            f"Stimulate the condition described by requirement {requirement_id}.",
            "Observe ECU response, timing behavior, diagnostic status, warning output, and fallback behavior as applicable.",
            "Compare observed behavior against the expected response and record pass/fail evidence.",
        ],
        "expectedResponse": f"The ECU behavior satisfies the requirement intent for ASIL {normalized_asil} and produces traceable verification evidence.",
        "reviewStatus": "Pending Engineer Approval",
    }


def build_alternative_candidate_test_case(
    requirement_id: str,
    requirement_text: str,
    asil_level: str,
    match_row: pd.Series,
    alternative_rank: int,
) -> dict[str, Any]:
    test_case_id = str(match_row.get("matched_test_case_id", match_row.get("test_case_id", "TC-N/A")))
    test_case_name = str(match_row.get("matched_test_case_name", match_row.get("test_case_name", "Alternative Test Case")))
    test_type = str(match_row.get("test_type", "Verification"))
    confidence = float(match_row.get("match_score", 0))
    duration_minutes = int(match_row.get("test_duration_minutes", match_row.get("duration_minutes", 0)))
    rationale = str(match_row.get("ai_rationale", "Alternative selected from available historical verification evidence."))
    boundary_clues = detect_boundary_clues(requirement_text)
    primary_clue = boundary_clues[0] if boundary_clues else "requirement behavior"

    return {
        "alternativeId": f"ALT-{requirement_id}-{alternative_rank:02d}",
        "sourceTestCaseId": test_case_id,
        "sourceTestCaseName": test_case_name,
        "alternativeTestCaseName": f"Alternative {alternative_rank}: {test_case_name}",
        "testType": test_type,
        "confidence": round(confidence, 2),
        "durationMinutes": duration_minutes,
        "replacementObjective": f"Use {test_case_id} as a replacement candidate to verify {primary_clue.lower()} for requirement {requirement_id}.",
        "replacementReason": (
            f"This alternative is recommended because it preserves traceability to requirement {requirement_id}, "
            f"has a {round(confidence * 100, 1)}% AI match score, and provides reusable {test_type.lower()} evidence. "
            f"Original AI rationale: {rationale}"
        ),
        "expectedResponse": f"The replacement candidate should satisfy the ASIL {str(asil_level).upper()} requirement intent and produce traceable verification evidence after engineer approval.",
        "recoveryStatus": "Available Alternative",
    }


def build_ranked_alternative_candidates(
    requirement_id: str,
    requirement_text: str,
    asil_level: str,
    excluded_test_case_ids: set[str],
    max_alternatives: int = 5,
) -> list[dict[str, Any]]:
    scored_alternatives: list[dict[str, Any]] = []

    for _, test_case in TEST_CASES.iterrows():
        test_case_id = str(test_case["test_case_id"])
        if test_case_id in excluded_test_case_ids:
            continue

        match_score = float(calculate_hybrid_match_score(requirement_text, asil_level, test_case))
        duration_minutes = int(test_case["duration_minutes"])
        regression_risk_score = calculate_regression_risk_score(asil_level, match_score, duration_minutes, requirement_text)
        scored_alternatives.append(
            {
                "matched_test_case_id": test_case_id,
                "matched_test_case_name": str(test_case["test_case_name"]),
                "test_type": str(test_case["test_type"]),
                "test_duration_minutes": duration_minutes,
                "match_score": match_score,
                "regression_risk_score": regression_risk_score,
                "ai_rationale": build_ai_rationale(
                    requirement_text,
                    str(test_case["test_case_name"]),
                    str(test_case["description"]),
                    match_score,
                ),
            }
        )

    scored_alternatives.sort(
        key=lambda item: (
            item["match_score"],
            item["regression_risk_score"],
            -item["test_duration_minutes"],
        ),
        reverse=True,
    )

    return [
        build_alternative_candidate_test_case(
            requirement_id=requirement_id,
            requirement_text=requirement_text,
            asil_level=asil_level,
            match_row=pd.Series(row),
            alternative_rank=rank,
        )
        for rank, row in enumerate(scored_alternatives[:max_alternatives], start=1)
    ]


def build_manual_test_design_candidate(requirement_id: str, requirement_text: str, asil_level: str) -> dict[str, Any]:
    boundary_clues = detect_boundary_clues(requirement_text)
    primary_clue = boundary_clues[0] if boundary_clues else "requirement behavior"
    normalized_asil = str(asil_level).upper()

    return {
        "manualDesignId": f"MANUAL-{requirement_id}",
        "manualTestCaseName": f"Manual Test Design Required for {requirement_id}",
        "objective": f"Create a human-authored test case to verify {primary_clue.lower()} for requirement {requirement_id}.",
        "recommendedSteps": [
            "Review the rejected AI-generated candidate test and document the rejection rationale.",
            f"Define a test stimulus that directly targets the requirement behavior: {requirement_text}",
            "Specify measurable pass/fail criteria, expected ECU response, diagnostic state, timing limits, and evidence artifacts.",
            "Assign the draft test case to a responsible ECU software engineer and safety engineer for review.",
            "Link the final manual test case back to the traceability matrix before report approval.",
        ],
        "expectedResponse": f"A human-authored test case should provide traceable ASIL {normalized_asil} verification evidence after engineer approval.",
        "recoveryStatus": "Manual Test Design Requested",
    }


def build_traceability_matrix(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for match in matches:
        match_score = float(match.get("match_score", 0))
        asil_level = str(match.get("asil_level", "QM")).upper()
        requirement_text = str(match.get("requirement_description", ""))
        decomposed_clauses = decompose_requirement_clauses(str(match.get("requirement_id", "REQ")), requirement_text)
        mapping_review = mapping_review_fields_from_match(match)
        rows.append(
            {
                "requirementId": match.get("requirement_id"),
                "asilLevel": asil_level,
                "requirementText": match.get("requirement_description"),
                "decomposedRequirementClauses": decomposed_clauses,
                "decompositionStatus": "DECOMPOSED" if len(decomposed_clauses) > 1 else "SINGLE_CLAUSE",
                "testCaseId": match.get("matched_test_case_id"),
                "testCaseName": match.get("matched_test_case_name"),
                "testType": match.get("test_type"),
                "coverageType": match.get("coverageType", match.get("coverage_type", infer_coverage_type(match_score))),
                "confidence": match_score,
                "aiRationale": match.get("ai_rationale"),
                "mappingReviewStatus": mapping_review["mappingReviewStatus"],
                "mappingReviewReason": mapping_review["mappingReviewReason"],
                "mappingReviewReasonCodes": mapping_review["mappingReviewReasonCodes"],
                "reviewStatus": mapping_review["reviewStatus"],
            }
        )

    return rows


def build_candidate1_review_workspace(requirements: pd.DataFrame, matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    match_df = pd.DataFrame(matches)
    review_items: list[dict[str, Any]] = []

    for _, requirement in requirements.iterrows():
        requirement_id = str(requirement["requirement_id"])
        requirement_text = str(requirement["description"])
        asil_level = str(requirement["asil_level"]).upper()
        decomposed_clauses = decompose_requirement_clauses(requirement_id, requirement_text)
        boundary_clues = detect_boundary_clues(requirement_text)

        requirement_matches = match_df[match_df["requirement_id"] == requirement_id].copy()
        requirement_matches = requirement_matches.sort_values(
            by=["match_score", "regression_risk_score", "test_duration_minutes"],
            ascending=[False, False, True],
        )

        primary_matches = requirement_matches.head(3)
        alternative_matches = requirement_matches.iloc[3:8]

        historical_tests = [
            {
                "testCaseId": str(row["matched_test_case_id"]),
                "testCaseName": str(row["matched_test_case_name"]),
                "testType": str(row["test_type"]),
                "confidence": float(row["match_score"]),
                "rationale": str(row.get("ai_rationale", "")),
                "reasonCodes": list(row.get("reason_codes", [])),
                "aiMetadata": dict(row.get("ai_metadata", {})),
            }
            for _, row in primary_matches.iterrows()
        ]

        excluded_test_case_ids = {
            str(row["matched_test_case_id"])
            for _, row in primary_matches.iterrows()
        }
        excluded_test_case_ids.update(
            str(row["matched_test_case_id"])
            for _, row in alternative_matches.iterrows()
        )

        alternative_candidate_tests = [
            build_alternative_candidate_test_case(
                requirement_id=requirement_id,
                requirement_text=requirement_text,
                asil_level=asil_level,
                match_row=row,
                alternative_rank=rank,
            )
            for rank, (_, row) in enumerate(alternative_matches.iterrows(), start=1)
        ]

        if len(alternative_candidate_tests) < 5:
            fallback_alternatives = build_ranked_alternative_candidates(
                requirement_id=requirement_id,
                requirement_text=requirement_text,
                asil_level=asil_level,
                excluded_test_case_ids=excluded_test_case_ids,
                max_alternatives=5 - len(alternative_candidate_tests),
            )
            alternative_candidate_tests.extend(fallback_alternatives)

        best_match_score = float(primary_matches.iloc[0]["match_score"]) if not primary_matches.empty else 0.0
        if best_match_score < GENERATE_TC_THRESHOLD:
            candidate_test_case = generate_test_case_ai(requirement_id, requirement_text, asil_level)
        else:
            candidate_test_case = generate_candidate_test_case(requirement_id, requirement_text, asil_level, boundary_clues)
        manual_test_design_candidate = build_manual_test_design_candidate(requirement_id, requirement_text, asil_level)
        best_match_rationale = str(primary_matches.iloc[0].get("ai_rationale", "")) if not primary_matches.empty else ""
        mapping_review = (
            mapping_review_fields_from_match(primary_matches.iloc[0].to_dict())
            if not primary_matches.empty
            else infer_mapping_review_status(best_match_score, requirement_text, best_match_rationale)
        )

        review_items.append(
            {
                "requirementId": requirement_id,
                "asilLevel": asil_level,
                "extractedRequirementText": requirement_text,
                "decomposedRequirementClauses": decomposed_clauses,
                "decompositionStatus": "DECOMPOSED" if len(decomposed_clauses) > 1 else "SINGLE_CLAUSE",
                "boundaryClues": boundary_clues,
                "recommendedHistoricalTests": historical_tests,
                "generatedCandidateTestCase": candidate_test_case,
                "alternativeCandidateTests": alternative_candidate_tests,
                "manualTestDesignCandidate": manual_test_design_candidate,
                "rejectionRecoveryStatus": "No Rejection",
                "selectedAlternativeId": None,
                "mappingReviewStatus": mapping_review["mappingReviewStatus"],
                "mappingReviewReason": mapping_review["mappingReviewReason"],
                "mappingReviewReasonCodes": mapping_review["mappingReviewReasonCodes"],
                "reviewStatus": mapping_review["reviewStatus"],
                "engineerDecision": mapping_review["reviewStatus"],
                "engineerReviewNote": "",
                "aiMetadata": dict(primary_matches.iloc[0].get("ai_metadata", {})) if not primary_matches.empty else {},
            }
        )

    return review_items
