from __future__ import annotations

import math
from typing import Any

import pandas as pd

from config import MAPPING_REVIEW_THRESHOLD
from matching import mapping_review_fields_from_match


ANOMALY_SCENARIOS: list[dict[str, str]] = [
    {
        "observed_value": "Borderline timing observed",
        "anomaly_type": "Timing Boundary Anomaly",
        "engineer_action": "Review response timing and rerun with timing trace evidence",
    },
    {
        "observed_value": "Unexpected diagnostic response code returned",
        "anomaly_type": "Diagnostic Response Anomaly",
        "engineer_action": "Review diagnostic response and confirm DTC behavior",
    },
    {
        "observed_value": "CAN message timeout during safety-relevant signal monitoring",
        "anomaly_type": "Communication Timeout Anomaly",
        "engineer_action": "Review CAN trace and confirm timeout handling",
    },
    {
        "observed_value": "Fallback state was delayed after fault injection",
        "anomaly_type": "Safety Fallback Behavior Anomaly",
        "engineer_action": "Review fallback transition evidence and safe-state timing",
    },
    {
        "observed_value": "Redundant sensor plausibility mismatch remained unresolved",
        "anomaly_type": "Sensor Plausibility Anomaly",
        "engineer_action": "Review redundant sensor traces and plausibility logic",
    },
    {
        "observed_value": "Voltage disturbance caused incomplete recovery behavior",
        "anomaly_type": "Electrical Recovery Anomaly",
        "engineer_action": "Review voltage profile and recovery evidence",
    },
    {
        "observed_value": "Thermal derating response exceeded expected operating boundary",
        "anomaly_type": "Thermal Boundary Anomaly",
        "engineer_action": "Review thermal model, derating threshold, and cooling recovery evidence",
    },
    {
        "observed_value": "Warning display priority was inconsistent under multiple active alerts",
        "anomaly_type": "HMI Priority Anomaly",
        "engineer_action": "Review HMI warning priority and display arbitration evidence",
    },
    {
        "observed_value": "Invalid calibration parameter was accepted by the control logic",
        "anomaly_type": "Calibration Configuration Anomaly",
        "engineer_action": "Review calibration validation and variant-coding constraints",
    },
    {
        "observed_value": "Stored fault evidence was incomplete after ignition cycle reset",
        "anomaly_type": "Data Integrity Anomaly",
        "engineer_action": "Review persistent storage, freeze-frame data, and reset recovery evidence",
    },
]

PROTOCOL_FRAME_TEMPLATES: list[dict[str, str]] = [
    {
        "protocol": "CAN",
        "direction": "TX",
        "id": "0x180",
        "data": "A9 01 00 00 00 00 00 00",
        "signal": "brake_pressure = 42.5 bar",
    },
    {
        "protocol": "CAN",
        "direction": "RX",
        "id": "0x280",
        "data": "01 00 00 00 00 00 00 00",
        "signal": "brake_status = valid",
    },
    {
        "protocol": "UDS",
        "direction": "TX",
        "id": "0x7E0",
        "data": "22 F1 90",
        "signal": "ReadDataByIdentifier: ECU identifier",
    },
    {
        "protocol": "UDS",
        "direction": "RX",
        "id": "0x7E8",
        "data": "62 F1 90 12 34 56",
        "signal": "positive DID response received",
    },
    {
        "protocol": "LIN",
        "direction": "TX",
        "id": "0x12",
        "data": "01 00 00 00",
        "signal": "door_lock_command = LOCK",
    },
    {
        "protocol": "LIN",
        "direction": "RX",
        "id": "0x22",
        "data": "01 7F 00 00",
        "signal": "body actuator status = acknowledged",
    },
    {
        "protocol": "ETH",
        "direction": "RX",
        "id": "SOME/IP 0x1234",
        "data": "EVENT 0x0421",
        "signal": "camera_status = active",
    },
    {
        "protocol": "CAN-FD",
        "direction": "TX",
        "id": "0x401",
        "data": "10 2A 00 7D 55 AA 00 01 02 03 04 05",
        "signal": "battery_voltage = 392.5 V",
    },
]


def build_protocol_execution_logs(unique_tests: pd.DataFrame, mapping_count: int) -> list[dict[str, str]]:
    logs: list[dict[str, str]] = [
        {
            "time": "00:00",
            "protocol": "SYS",
            "direction": "INIT",
            "id": "ENV",
            "data": "BOOT",
            "detail": "Initializing ECU verification environment",
        },
        {
            "time": "00:01",
            "protocol": "SYS",
            "direction": "LOAD",
            "id": "QUEUE",
            "data": f"{mapping_count} mappings",
            "detail": "Loading matched requirement-to-test queue",
        },
    ]

    max_protocol_events = min(60, len(unique_tests))
    for index, (_, row) in enumerate(unique_tests.head(max_protocol_events).iterrows(), start=2):
        frame = PROTOCOL_FRAME_TEMPLATES[(index - 2) % len(PROTOCOL_FRAME_TEMPLATES)]
        minute = index // 60
        second = index % 60
        logs.append(
            {
                "time": f"{minute:02d}:{second:02d}",
                "protocol": frame["protocol"],
                "direction": frame["direction"],
                "id": frame["id"],
                "data": frame["data"],
                "detail": (
                    f"{frame['signal']} | "
                    f"{row.get('matched_test_case_id', 'TC-N/A')} "
                    f"{row.get('matched_test_case_name', '')}"
                ),
            }
        )

    final_event_index = max_protocol_events + 2
    final_minute = final_event_index // 60
    final_second = final_event_index % 60
    logs.extend(
        [
            {
                "time": f"{final_minute:02d}:{final_second:02d}",
                "protocol": "SYS",
                "direction": "ANALYZE",
                "id": "TRACE",
                "data": "RX/TX BUFFER",
                "detail": f"Captured representative protocol traces for {max_protocol_events} of {len(unique_tests)} unique test cases",
            },
            {
                "time": f"{final_minute:02d}:{final_second + 1:02d}",
                "protocol": "SYS",
                "direction": "DONE",
                "id": "RESULT",
                "data": "COMPLETE",
                "detail": "Verification simulation complete; anomaly candidates forwarded for engineer review",
            },
        ]
    )

    return logs


def infer_anomaly_type(test_type: str, test_case_name: str, observed_value: str, verdict: str) -> str:
    if verdict == "PASS":
        return "No anomaly detected"

    text = f"{test_type} {test_case_name} {observed_value}".lower()

    if "diagnostic" in text or "dtc" in text or "response code" in text:
        return "Diagnostic Response Anomaly"
    if "communication" in text or "timeout" in text or "can message" in text:
        return "Communication Timeout Anomaly"
    if "fallback" in text or "safe state" in text or "fault injection" in text:
        return "Safety Fallback Behavior Anomaly"
    if "sensor" in text or "plausibility" in text or "redundant" in text:
        return "Sensor Plausibility Anomaly"
    if "voltage" in text or "electrical" in text or "recovery" in text:
        return "Electrical Recovery Anomaly"
    if "thermal" in text or "temperature" in text or "derating" in text:
        return "Thermal Boundary Anomaly"
    if "warning" in text or "display" in text or "hmi" in text or "alert" in text:
        return "HMI Priority Anomaly"
    if "calibration" in text or "configuration" in text or "variant" in text:
        return "Calibration Configuration Anomaly"
    if "storage" in text or "freeze-frame" in text or "reset" in text or "stored" in text:
        return "Data Integrity Anomaly"
    if "timing" in text or "delay" in text or "latency" in text or "borderline" in text:
        return "Timing Boundary Anomaly"
    return "Execution Behavior Anomaly"


def build_anomaly_explanation(test_case_name: str, anomaly_type: str, observed_value: str, verdict: str) -> str:
    if verdict == "PASS":
        return "The observed result stayed within the expected verification range, so no anomaly review is required."

    return (
        f"The AI anomaly detector flagged '{test_case_name}' because the observed behavior was reported as "
        f"'{observed_value}'. This pattern is classified as {anomaly_type.lower()} and should be reviewed by an engineer "
        "before the result is treated as final verification evidence."
    )


def build_anomaly_review_rows(test_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    anomaly_rows: list[dict[str, Any]] = []

    for row in test_rows:
        verdict = str(row.get("result", "PASS")).upper()
        observed_value = str(row.get("measured_value", ""))
        test_case_name = str(row.get("test_case_name", ""))
        test_type = str(row.get("test_type", ""))
        anomaly_type = str(row.get("anomaly_type") or infer_anomaly_type(test_type, test_case_name, observed_value, verdict))
        confidence = float(row.get("anomaly_confidence", 0.0 if verdict == "PASS" else 0.78))

        anomaly_rows.append(
            {
                "testCaseId": row.get("test_case_id"),
                "testCaseName": test_case_name,
                "testType": test_type,
                "expectedBehavior": row.get("expected_behavior", "Observed ECU response should remain within expected timing, diagnostic, and functional safety limits."),
                "observedBehavior": row.get("observed_behavior", observed_value),
                "anomalyType": anomaly_type,
                "confidence": round(confidence, 2),
                "aiExplanation": row.get("anomaly_explanation") or build_anomaly_explanation(test_case_name, anomaly_type, observed_value, verdict),
                "engineerDecision": row.get("engineer_action", "Accept" if verdict == "PASS" else "Escalate"),
                "reviewRequired": verdict != "PASS",
                "metadata": dict(row.get("anomaly_metadata", {})),
            }
        )

    return anomaly_rows


def build_simulated_observation(test_row: pd.Series, linked_matches: list[dict[str, Any]]) -> dict[str, Any]:
    test_case_id = str(test_row.get("matched_test_case_id", "TC-N/A"))
    test_case_name = str(test_row.get("matched_test_case_name", "Verification Test"))
    test_type = str(test_row.get("test_type", "Verification"))
    requirement_text = " ".join(str(match.get("requirement_description", "")) for match in linked_matches)
    searchable = f"{test_case_name} {test_type} {requirement_text}".lower()
    risk_score = max((float(match.get("regression_risk_score", 0)) for match in linked_matches), default=0.0)
    match_score = min((float(match.get("match_score", 1)) for match in linked_matches), default=1.0)
    review_statuses = {str(match.get("review_status", "")).lower() for match in linked_matches}

    signal_rules = [
        (("thermal", "temperature", "derating"), "temperature_c", [20.0, 95.0]),
        (("voltage", "electrical", "battery"), "supply_voltage_v", [9.0, 16.0]),
        (("timing", "latency", "timeout", "within", " ms"), "response_time_ms", [0.0, 100.0]),
        (("sensor", "plausibility", "redundant"), "sensor_plausibility_pct", [95.0, 100.0]),
        (("communication", "can", "message"), "message_health_pct", [98.0, 100.0]),
        (("warning", "display", "cluster", "hmi", "audible"), "hmi_response_score", [90.0, 100.0]),
        (("torque", "brake", "actuator"), "command_tracking_pct", [90.0, 110.0]),
    ]
    signal_name, expected_range = next(
        ((name, bounds) for terms, name, bounds in signal_rules if any(term in searchable for term in terms)),
        ("verification_response_pct", [90.0, 110.0]),
    )
    minimum, maximum = expected_range
    center = (minimum + maximum) / 2
    width = maximum - minimum
    seed = sum(ord(character) for character in test_case_id)
    observed_series = [
        round(center + math.sin((seed + index) * 0.47) * width * 0.08, 3)
        for index in range(24)
    ]
    anomaly_candidate = (
        risk_score >= 80
        or match_score < MAPPING_REVIEW_THRESHOLD
        or bool(review_statuses & {"review_required", "weak_fallback", "external_validation_required"})
    )
    protocol_logs = [
        f"SIM signal={signal_name} test_case={test_case_id}",
        f"SIM risk_score={risk_score:g} match_score={match_score:.3f}",
        "SIM protocol response remained valid",
    ]
    if anomaly_candidate:
        excursion = maximum + max(width * 0.18, 1.0)
        observed_series[-3:] = [round(excursion + index * width * 0.03, 3) for index in range(3)]
        protocol_logs[-1] = "SIM anomaly indicator: response outside configured expected range; engineer review required"

    return {
        "test_case_id": test_case_id,
        "test_case_name": test_case_name,
        "signal_name": signal_name,
        "expected_range": expected_range,
        "observed_series": observed_series,
        "expected_behavior": f"{signal_name} should remain within [{minimum:g}, {maximum:g}] during the simulated verification observation.",
        "protocol_logs": protocol_logs,
        "linked_requirements": [
            {
                "requirement_id": match.get("requirement_id"),
                "description": match.get("requirement_description"),
                "asil_level": match.get("asil_level"),
                "match_score": match.get("match_score"),
                "regression_risk_score": match.get("regression_risk_score"),
            }
            for match in linked_matches
        ],
    }


def build_c3_audit_events(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        metadata = dict(row.get("anomaly_metadata", {}))
        events.append(
            {
                "eventId": f"AUD-C3-{index:03d}",
                "eventType": "AI_ANOMALY_DETECTION",
                "actor": "C3 Chronos Anomaly Detector",
                "relatedItem": row.get("test_case_id"),
                "details": (
                    f"Verdict {row.get('result')} for {row.get('test_case_id')}; "
                    f"anomaly type: {row.get('anomaly_type')}; confidence: {row.get('anomaly_confidence')}."
                ),
                "test_case_id": row.get("test_case_id"),
                "model_name": metadata.get("model_name"),
                "ai_used": bool(metadata.get("ai_used", False)),
                "fallback_used": bool(metadata.get("fallback_used", False)),
                "fallback_reason": metadata.get("fallback_reason"),
                "verdict": row.get("result"),
                "anomaly_type": row.get("anomaly_type"),
                "confidence": row.get("anomaly_confidence"),
            }
        )
    return events


def build_audit_log(
    filename: str | None,
    parser_info: dict[str, Any],
    requirements: pd.DataFrame,
    matches: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    requirement_count = int(len(requirements))
    unique_test_count = int(pd.DataFrame(matches)["matched_test_case_id"].nunique()) if matches else 0
    review_required_count = sum(
        1
        for match in matches
        if mapping_review_fields_from_match(match)["mappingReviewStatus"] == "MAPPING_REVIEW_REQUIRED"
    )

    audit_events = [
        {
            "eventId": "AUD-001",
            "eventType": "File Upload",
            "actor": "System",
            "relatedItem": filename or "uploaded file",
            "details": "Requirement file was received by the verification workflow.",
        },
        {
            "eventId": "AUD-002",
            "eventType": "Parser Auto-Detection",
            "actor": "System",
            "relatedItem": parser_info.get("sheetName") or parser_info.get("fileType") or "uploaded file",
            "details": (
                f"Detected header row {parser_info.get('headerRow', 'N/A')}; "
                f"requirement text column: {parser_info.get('requirementTextColumn', 'N/A')}; "
                f"ASIL column: {parser_info.get('asilColumn', 'N/A')}."
            ),
        },
        {
            "eventId": "AUD-003",
            "eventType": "Requirement Normalization",
            "actor": "System",
            "relatedItem": "Normalized requirement set",
            "details": f"Normalized {requirement_count} requirement record(s) for matching.",
        },
        {
            "eventId": "AUD-004",
            "eventType": "AI Candidate Matching",
            "actor": "AI Matching Module",
            "relatedItem": "Requirement-to-test mappings",
            "details": f"Generated {len(matches)} candidate mapping(s) across {unique_test_count} unique test case(s).",
        },
        {
            "eventId": "AUD-005",
            "eventType": "Review Gate Assignment",
            "actor": "System",
            "relatedItem": "Traceability Matrix",
            "details": f"Flagged {review_required_count} candidate mapping(s) for manual or safety engineer review.",
        },
    ]
    matches_by_requirement: dict[str, list[dict[str, Any]]] = {}
    for match in matches:
        matches_by_requirement.setdefault(str(match.get("requirement_id", "REQ-N/A")), []).append(match)

    for index, (requirement_id, requirement_matches) in enumerate(matches_by_requirement.items(), start=1):
        first_match = requirement_matches[0]
        metadata = dict(first_match.get("ai_metadata", {}))
        reason_codes = sorted(
            {
                str(code)
                for match in requirement_matches
                for code in match.get("reason_codes", [])
            }
        )
        selected_test_case_ids = [str(match.get("matched_test_case_id", "")) for match in requirement_matches]
        review_status = str(first_match.get("review_status", "review_required"))
        audit_events.append(
            {
                "eventId": f"AUD-AI-{index:03d}",
                "eventType": "AI_MATCHING",
                "actor": "C1 AI Matching Engine",
                "relatedItem": requirement_id,
                "details": (
                    f"Selected test case(s): {', '.join(selected_test_case_ids)}; "
                    f"AI used: {metadata.get('ai_used', False)}; "
                    f"fallback used: {metadata.get('fallback_used', False)}; "
                    f"review status: {review_status}."
                ),
                "requirement_id": requirement_id,
                "selected_test_case_ids": selected_test_case_ids,
                "ai_used": bool(metadata.get("ai_used", False)),
                "model_name": metadata.get("model_name"),
                "fallback_used": bool(metadata.get("fallback_used", False)),
                "fallback_reason": metadata.get("fallback_reason"),
                "review_status": review_status,
                "reason_codes": reason_codes,
            }
        )

    for index, match in enumerate(matches, start=1):
        metadata = dict(match.get("c2_ai_metadata", {}))
        test_case_id = str(match.get("matched_test_case_id", "TC-N/A"))
        requirement_id = str(match.get("requirement_id", "REQ-N/A"))
        deterministic_score = float(match.get("deterministic_regression_risk_score", match.get("regression_risk_score", 0)))
        ai_priority_score = float(match.get("ai_priority_score", deterministic_score))
        final_priority_score = float(match.get("final_priority_score", match.get("regression_risk_score", deterministic_score)))
        rationale = str(match.get("priority_rationale", match.get("regression_ranking_reason", "")))
        audit_events.append(
            {
                "eventId": f"AUD-C2-{index:03d}",
                "eventType": "AI_REGRESSION_PRIORITIZATION",
                "actor": "C2 AI Regression Prioritizer",
                "relatedItem": test_case_id,
                "details": (
                    f"Prioritized {test_case_id} for {requirement_id}; deterministic score: {deterministic_score}; "
                    f"AI priority score: {ai_priority_score}; final priority score: {final_priority_score}."
                ),
                "test_case_id": test_case_id,
                "requirement_id": requirement_id,
                "model_name": metadata.get("model_name"),
                "ai_used": bool(metadata.get("ai_used", False)),
                "fallback_used": bool(metadata.get("fallback_used", False)),
                "fallback_reason": metadata.get("fallback_reason"),
                "deterministic_risk_score": deterministic_score,
                "ai_priority_score": ai_priority_score,
                "final_priority_score": final_priority_score,
                "rationale": rationale,
            }
        )

    return audit_events
