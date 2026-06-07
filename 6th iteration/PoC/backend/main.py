from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from ai_services.anomaly_ai import run_c3_anomaly_ai
from ai_services.report_ai import run_c3_report_drafter_ai
from candidate_workspace import build_candidate1_review_workspace, build_traceability_matrix
from matching import make_summary, match_requirements
from models import ReportRequest, ReviewDecision
from requirements_parser import (
    build_parser_info_details,
    normalize_requirements,
    parse_requirements_file,
)
from simulation import (
    build_anomaly_review_rows,
    build_audit_log,
    build_c3_audit_events,
    build_protocol_execution_logs,
    build_simulated_observation,
)
from test_cases import TEST_CASES


app = FastAPI(title="AI Assisted Software Verification Tool API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/test-cases")
def get_test_cases() -> list[dict[str, Any]]:
    return TEST_CASES.to_dict(orient="records")


@app.post("/analyze")
async def analyze_requirements(file: UploadFile = File(...)) -> dict[str, Any]:
    file_bytes = await file.read()

    try:
        raw_requirements, parser_info = parse_requirements_file(file_bytes, file.filename or "")
        requirements = normalize_requirements(raw_requirements)
        parser_info = build_parser_info_details(raw_requirements, requirements, parser_info)
        matches = match_requirements(requirements)
        traceability_matrix = build_traceability_matrix(matches)
        candidate1_review_items = build_candidate1_review_workspace(requirements, matches)
        audit_log = build_audit_log(file.filename, parser_info, requirements, matches)
        summary = make_summary(matches, requirement_count=len(requirements))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "filename": file.filename,
        "requirements": requirements.to_dict(orient="records"),
        "matches": matches,
        "summary": summary,
        "parserInfo": parser_info,
        "traceabilityMatrix": traceability_matrix,
        "candidate1ReviewItems": candidate1_review_items,
        "auditLog": audit_log,
    }


@app.post("/simulate-tests")
def simulate_tests(payload: dict[str, Any]) -> dict[str, Any]:
    matches = payload.get("matches", [])
    if not matches:
        raise HTTPException(status_code=400, detail="No matches were provided.")

    match_df = pd.DataFrame(matches)
    unique_tests = match_df.drop_duplicates(subset=["matched_test_case_id"]).copy()

    rows: list[dict[str, Any]] = []
    for _, row in unique_tests.reset_index(drop=True).iterrows():
        test_case_id = str(row["matched_test_case_id"])
        linked_matches = match_df[match_df["matched_test_case_id"].astype(str) == test_case_id].to_dict(orient="records")
        observation = build_simulated_observation(row, linked_matches)
        anomaly_result = run_c3_anomaly_ai(observation)
        anomaly_metadata = anomaly_result.metadata.model_dump()
        rows.append(
            {
                "test_case_id": test_case_id,
                "test_case_name": row["matched_test_case_name"],
                "test_type": row["test_type"],
                "duration_minutes": int(row["test_duration_minutes"]),
                "result": anomaly_result.verdict,
                "measured_value": anomaly_result.observed_behavior,
                "engineer_action": anomaly_result.recommended_engineer_action,
                "expected_behavior": observation["expected_behavior"],
                "signal_name": observation["signal_name"],
                "expected_range": observation["expected_range"],
                "observed_series": observation["observed_series"],
                "protocol_logs": observation["protocol_logs"],
                "anomaly_metadata": anomaly_metadata,
                "anomaly_type": anomaly_result.anomaly_type,
                "anomaly_confidence": anomaly_result.confidence,
                "observed_behavior": anomaly_result.observed_behavior,
                "anomaly_explanation": anomaly_result.explanation,
            }
        )

    anomaly_review = build_anomaly_review_rows(rows)
    protocol_logs = build_protocol_execution_logs(unique_tests, mapping_count=len(matches))
    anomaly_audit_log = build_c3_audit_events(rows)

    return {
        "results": rows,
        "anomalyReview": anomaly_review,
        "protocolLogs": protocol_logs,
        "auditLog": anomaly_audit_log,
        "anomalyAuditLog": anomaly_audit_log,
        "summary": {
            "executedTestCases": len(rows),
            "passCount": sum(1 for row in rows if row["result"] == "PASS"),
            "reviewCount": sum(1 for row in rows if row["result"] == "REVIEW"),
            "anomalyCount": sum(1 for row in anomaly_review if row["reviewRequired"]),
            "estimatedTotalTimeMinutes": sum(int(row["duration_minutes"]) for row in rows),
        },
    }


@app.post("/draft-report")
def draft_report(payload: ReportRequest) -> dict[str, Any]:
    matches = payload.matches
    decisions = payload.decisions
    candidate1_decisions = payload.candidate1Decisions or {}

    if not matches:
        raise HTTPException(status_code=400, detail="No matches were provided.")

    match_df = pd.DataFrame(matches)
    unique_tests = match_df.drop_duplicates(subset=["matched_test_case_id"]).copy()

    requirement_count = int(match_df["requirement_id"].nunique()) if "requirement_id" in match_df.columns else 0
    unique_test_count = int(match_df["matched_test_case_id"].nunique()) if "matched_test_case_id" in match_df.columns else 0
    total_mappings = int(len(match_df))
    average_confidence = round(float(match_df["match_score"].mean()), 3) if "match_score" in match_df.columns and total_mappings else 0
    total_test_time_minutes = int(unique_tests["test_duration_minutes"].sum()) if "test_duration_minutes" in unique_tests.columns else 0

    accepted_decisions = [decision for decision in decisions if any(term in decision.decision.upper() for term in ("ACCEPT", "APPROVE"))]
    rejected_decisions = [decision for decision in decisions if any(term in decision.decision.upper() for term in ("REJECT", "DENIED", "DENY"))]
    unresolved_decisions = [
        decision for decision in decisions
        if decision not in accepted_decisions and decision not in rejected_decisions
    ]

    candidate1_approved = [key for key, value in candidate1_decisions.items() if str(value).upper() == "APPROVED_BY_ENGINEER"]
    candidate1_alternative_selected = [key for key, value in candidate1_decisions.items() if str(value).upper() == "REJECTED_WITH_ALTERNATIVE"]
    candidate1_manual_requested = [key for key, value in candidate1_decisions.items() if str(value).upper() == "MANUAL_TEST_REQUESTED"]
    candidate1_rejected = [key for key, value in candidate1_decisions.items() if str(value).upper() == "REJECTED_BY_ENGINEER"]
    resolved_mapping_requirements = set(candidate1_approved + candidate1_alternative_selected)

    unresolved_mapping_requirements: set[str] = set()
    external_validation_requirements: set[str] = set()
    untestable_requirements: set[str] = set()
    for match in matches:
        requirement_id = str(match.get("requirement_id", match.get("requirementId", "UNKNOWN")))
        review_status = str(match.get("review_status", match.get("reviewStatus", ""))).lower()
        mapping_review_status = str(match.get("mappingReviewStatus", "")).upper()
        coverage_type = str(match.get("coverage_type", match.get("coverageType", ""))).lower()
        if coverage_type == "external_validation_required" or review_status == "external_validation_required":
            external_validation_requirements.add(requirement_id)
        if bool(match.get("untestable")) or review_status == "untestable":
            untestable_requirements.add(requirement_id)
        if (
            review_status in {"review_required", "weak_fallback", "external_validation_required", "untestable"}
            or mapping_review_status == "MAPPING_REVIEW_REQUIRED"
        ) and requirement_id not in resolved_mapping_requirements:
            unresolved_mapping_requirements.add(requirement_id)

    review_simulation_ids = {
        str(item.get("test_case_id", item.get("testCaseId", "")))
        for item in payload.simulationResults
        if str(item.get("result", "")).upper() == "REVIEW"
    }
    decided_test_ids = {decision.testCaseId for decision in decisions}
    unresolved_anomaly_ids = sorted(
        (review_simulation_ids - decided_test_ids)
        | {decision.testCaseId for decision in unresolved_decisions}
        | {decision.testCaseId for decision in rejected_decisions}
    )

    unresolved_issues = [
        *[f"Mapping requires engineer resolution: {item}" for item in sorted(unresolved_mapping_requirements)],
        *[f"Anomaly decision remains open or rejected: {item}" for item in unresolved_anomaly_ids],
        *[f"External physical validation remains required: {item}" for item in sorted(external_validation_requirements)],
        *[f"Requirement is currently untestable: {item}" for item in sorted(untestable_requirements)],
        *[f"Manual test design remains required: {item}" for item in sorted(candidate1_manual_requested)],
        *[f"Candidate mapping remains rejected: {item}" for item in sorted(candidate1_rejected)],
    ]
    unresolved_issues = list(dict.fromkeys(unresolved_issues))
    blocking_issues = unresolved_issues[:50]
    can_approve = not blocking_issues
    report_status = "READY_FOR_APPROVAL" if can_approve else ("BLOCKED" if untestable_requirements else "REQUIRES_REVIEW")
    approval_gate = {
        "status": report_status,
        "canApprove": can_approve,
        "blockingIssues": blocking_issues,
        "requiredApprover": "Functional Safety Engineer",
        "message": (
            "Draft evidence is ready for Functional Safety Engineer approval; approval has not been granted."
            if can_approve
            else f"Functional Safety Engineer approval is blocked by {len(blocking_issues)} unresolved issue(s)."
        ),
        "approvalStatus": "Pending Safety Engineer Review",
        "reviewerRole": "Functional Safety Engineer",
        "approvalRequired": True,
        "controlRationale": "The backend determines readiness from unresolved mappings, anomaly decisions, and external validation obligations. The NLG drafter cannot approve this report.",
    }

    summary_metrics = {
        "requirementCount": requirement_count,
        "uniqueTestCaseCount": unique_test_count,
        "mappingCount": total_mappings,
        "averageConfidence": average_confidence,
        "estimatedTestTimeMinutes": total_test_time_minutes,
        "acceptedResultCount": len(accepted_decisions),
        "rejectedResultCount": len(rejected_decisions),
        "unresolvedAnomalyDecisionCount": len(unresolved_anomaly_ids),
        "approvedMappingCount": len(candidate1_approved) + len(candidate1_alternative_selected),
        "rejectedMappingCount": len(candidate1_rejected),
        "untestableRequirementCount": len(untestable_requirements),
        "externalValidationRequiredCount": len(external_validation_requirements),
        "unresolvedIssueCount": len(unresolved_issues),
        "candidate1ApprovedCount": len(candidate1_approved),
        "candidate1AlternativeRecoveryCount": len(candidate1_alternative_selected),
        "candidate1ManualDesignCount": len(candidate1_manual_requested),
        "candidate1KeptRejectedCount": len(candidate1_rejected),
    }
    deterministic_text = {
        "scope_summary": f"The draft covers {requirement_count} requirements, {total_mappings} mappings, and {unique_test_count} unique candidate test cases.",
        "safety_context": "This report supports Functional Safety Engineer review and does not establish ISO 26262 certification or final safety approval.",
        "traceability_evidence": f"Average mapping confidence is {round(average_confidence * 100, 1)}%; {len(unresolved_mapping_requirements)} mapping requirement(s) remain unresolved.",
        "test_portfolio_summary": f"Estimated unique simulated test effort is {total_test_time_minutes} minutes across {unique_test_count} test cases.",
        "anomaly_review_summary": f"Engineer decisions include {len(accepted_decisions)} accepted, {len(rejected_decisions)} rejected, and {len(unresolved_anomaly_ids)} unresolved anomaly result(s).",
        "engineer_decision_summary": f"{len(candidate1_approved)} mappings were approved and {len(candidate1_alternative_selected)} were resolved using alternatives; unresolved items remain subject to engineer action.",
        "limitations": "Execution evidence is simulated. Real ECU/HIL execution, physical HMI validation, and formal safety confirmation are outside this draft.",
        "approval_gate_statement": approval_gate["message"],
    }
    compact_mappings = [
        {
            "requirement_id": item.get("requirement_id"),
            "test_case_id": item.get("matched_test_case_id"),
            "asil_level": item.get("asil_level"),
            "match_score": item.get("match_score"),
            "coverage_type": item.get("coverage_type", item.get("coverageType")),
            "review_status": item.get("review_status", item.get("reviewStatus")),
        }
        for item in matches[:25]
    ]
    traceability_matrix = payload.traceabilityMatrix or build_traceability_matrix(matches)
    report_payload = {
        **deterministic_text,
        "summary_metrics": summary_metrics,
        "mappings": compact_mappings,
        "traceability_matrix": traceability_matrix[:20],
        "simulation_results": payload.simulationResults[:20],
        "anomaly_decisions": [decision.model_dump() for decision in decisions[:20]],
        "candidate1_decisions": list(candidate1_decisions.items())[:25],
        "candidate1_review_notes": dict(list((payload.candidate1ReviewNotes or {}).items())[:10]),
        "candidate1_recovery_records": dict(list((payload.candidate1RecoveryRecords or {}).items())[:10]),
        "unresolved_issues": unresolved_issues[:25],
        "external_validation_required": sorted(external_validation_requirements)[:25],
        "report_status": report_status,
        "approval_gate": approval_gate,
    }
    report_draft = run_c3_report_drafter_ai(report_payload)
    ai_metadata = report_draft.metadata.model_dump()
    sections = [
        {"title": "Scope Summary", "body": report_draft.scope_summary},
        {"title": "Safety Context", "body": report_draft.safety_context},
        {"title": "Traceability Evidence", "body": report_draft.traceability_evidence},
        {"title": "Test Portfolio Summary", "body": report_draft.test_portfolio_summary},
        {"title": "Anomaly Review Summary", "body": report_draft.anomaly_review_summary},
        {"title": "Engineer Decision Summary", "body": report_draft.engineer_decision_summary},
        {"title": "Limitations", "body": report_draft.limitations},
        {"title": "Approval Gate", "body": report_draft.approval_gate_statement},
    ]
    audit_event = {
        "eventType": "AI_REPORT_DRAFTING",
        "model_name": ai_metadata.get("model_name"),
        "ai_used": ai_metadata.get("ai_used", False),
        "fallback_used": ai_metadata.get("fallback_used", True),
        "fallback_reason": ai_metadata.get("fallback_reason"),
        "report_status": report_status,
        "unresolved_issue_count": len(unresolved_issues),
    }

    return {
        "title": "Draft ISO 26262 Verification Support Report",
        "summary": summary_metrics,
        "sections": sections,
        "approvalGate": approval_gate,
        "reportStatus": report_status,
        "unresolvedIssues": unresolved_issues,
        "aiMetadata": ai_metadata,
        "auditLog": [audit_event],
    }
