"""AI service for generating a test case from a low-confidence requirement."""

from __future__ import annotations

from typing import Any

from .config import AI_ENABLED, MODEL_C1_MATCHING
from .llm_client import request_json
from .schemas import AIMetadata


SYSTEM_PROMPT = """You are a software verification test case writer for ISO 26262 automotive ECU software.
A requirement has been flagged because no existing test case matched it with sufficient confidence.
Your task: write ONE specific, actionable test case that directly verifies the given requirement.
Return only strict JSON. No markdown, no prose outside the JSON object.
Required JSON shape:
{
  "test_case_name": "short descriptive name (max 10 words)",
  "test_type": "one of: Functional, Timing, Boundary, Fault Injection, Integration, Regression",
  "objective": "what this test verifies, 1-2 sentences referencing the requirement",
  "precondition": "ECU state required before the test begins",
  "procedure": ["step 1", "step 2", "step 3", "step 4"],
  "expected_response": "exact ECU behaviour that constitutes a pass",
  "acceptance_criteria": "measurable pass/fail criterion",
  "estimated_duration_minutes": integer between 30 and 480
}"""

GENERATE_TC_SCHEMA = {
    "type": "object",
    "properties": {
        "test_case_name":           {"type": "string"},
        "test_type":                {"type": "string", "enum": ["Functional", "Timing", "Boundary", "Fault Injection", "Integration", "Regression"]},
        "objective":                {"type": "string"},
        "precondition":             {"type": "string"},
        "procedure":                {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 6},
        "expected_response":        {"type": "string"},
        "acceptance_criteria":      {"type": "string"},
        "estimated_duration_minutes": {"type": "integer", "minimum": 30, "maximum": 480},
    },
    "required": [
        "test_case_name", "test_type", "objective", "precondition",
        "procedure", "expected_response", "acceptance_criteria", "estimated_duration_minutes",
    ],
}

VALID_TEST_TYPES = {"Functional", "Timing", "Boundary", "Fault Injection", "Integration", "Regression"}


def generate_test_case_ai(
    requirement_id: str,
    requirement_text: str,
    asil_level: str,
) -> dict[str, Any]:
    """Generate a test case for a requirement that had no strong existing match.

    Returns a dict with the test case fields plus an ``ai_generated`` flag and
    ``ai_metadata`` so the frontend can render it distinctly.
    """
    if not AI_ENABLED:
        return _fallback(requirement_id, requirement_text, asil_level, "AI_DISABLED")

    user_payload = {
        "requirement_id": requirement_id,
        "requirement_text": requirement_text,
        "asil_level": asil_level,
        "context": (
            "This requirement had no existing test case with confidence ≥ 60%. "
            "Generate a purpose-built test case that directly verifies it."
        ),
    }

    result = request_json(
        model_name=MODEL_C1_MATCHING,
        system_prompt=SYSTEM_PROMPT,
        user_payload=user_payload,
        response_schema=GENERATE_TC_SCHEMA,
    )

    if result.metadata.fallback_used or result.data is None:
        return _fallback(requirement_id, requirement_text, asil_level,
                         result.metadata.fallback_reason or "AI_UNAVAILABLE")

    data = result.data
    test_type = str(data.get("test_type", "Functional"))
    if test_type not in VALID_TEST_TYPES:
        test_type = "Functional"

    procedure = data.get("procedure", [])
    if not isinstance(procedure, list):
        procedure = [str(procedure)]

    return {
        "candidateTestCaseId": f"GEN-{requirement_id}",
        "candidateTestCaseName": str(data.get("test_case_name", f"AI-Generated TC for {requirement_id}")),
        "testType": test_type,
        "objective": str(data.get("objective", "")),
        "precondition": str(data.get("precondition", "")),
        "procedure": [str(s) for s in procedure],
        "expectedResponse": str(data.get("expected_response", "")),
        "acceptanceCriteria": str(data.get("acceptance_criteria", "")),
        "estimatedDurationMinutes": int(data.get("estimated_duration_minutes", 60)),
        "reviewStatus": "Pending Engineer Approval",
        "aiGenerated": True,
        "aiMetadata": result.metadata.model_dump(),
    }


def _fallback(
    requirement_id: str,
    requirement_text: str,
    asil_level: str,
    reason: str,
) -> dict[str, Any]:
    """Deterministic fallback when AI is unavailable."""
    short_text = requirement_text[:80].rstrip() + ("…" if len(requirement_text) > 80 else "")
    return {
        "candidateTestCaseId": f"GEN-{requirement_id}",
        "candidateTestCaseName": f"Proposed Verification for {requirement_id}",
        "testType": "Functional",
        "objective": f"Verify that the ECU satisfies: {short_text}",
        "precondition": "ECU is configured with the required software baseline and diagnostic session is active.",
        "procedure": [
            f"Configure test environment for requirement {requirement_id}.",
            "Stimulate the condition described by the requirement.",
            "Observe and record ECU response, timing, and diagnostic output.",
            "Compare observed behaviour against the requirement specification.",
        ],
        "expectedResponse": f"ECU behaviour satisfies ASIL {asil_level} requirement intent with traceable evidence.",
        "acceptanceCriteria": "All observed outputs match the requirement specification within defined tolerances.",
        "estimatedDurationMinutes": 60,
        "reviewStatus": "Pending Engineer Approval",
        "aiGenerated": False,
        "aiMetadata": AIMetadata(
            ai_used=False,
            fallback_used=True,
            fallback_reason=reason,
        ).model_dump(),
    }
