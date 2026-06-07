"""Optional C2 regression prioritization AI adapter."""

from __future__ import annotations

from typing import Any

from .config import AI_ENABLED, MODEL_C2_PRIORITIZER
from .fallback import prioritization_fallback_response
from .llm_client import request_json
from .schemas import C2PrioritizationResponse


SYSTEM_PROMPT = """You are a regression-test prioritization assistant.
Return only a strict JSON object with ai_priority_score, factor_scores, and
rationale. Do not include markdown, prose outside the JSON object, or extra
top-level keys.
factor_scores must contain asil, safety_behavior, mapping_uncertainty, duration,
and review_dependency. Keep the rationale concise and based only on supplied
ASIL, safety behavior indicators, mapping uncertainty, duration, and review
dependency. Do not claim real ECU execution, HIL results, or ISO 26262
compliance. Do not return chain-of-thought.
All five factor score keys are mandatory. Required JSON shape:
{"ai_priority_score":0,"factor_scores":{"asil":0,"safety_behavior":0,
"mapping_uncertainty":0,"duration":0,"review_dependency":0},
"rationale":"concise engineer-reviewable explanation"}"""

FACTOR_SCORE_LIMITS = {
    "asil": (0.0, 45.0),
    "safety_behavior": (0.0, 20.0),
    "mapping_uncertainty": (0.0, 15.0),
    "duration": (0.0, 10.0),
    "review_dependency": (0.0, 10.0),
}
PROHIBITED_RATIONALE_CLAIMS = {
    "real ecu execution",
    "actual ecu execution",
    "real hil",
    "actual hil",
    "hil results confirm",
    "iso 26262 compliant",
    "iso 26262 compliance achieved",
    "certified compliant",
}
C2_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "ai_priority_score": {"type": "number", "minimum": 0, "maximum": 100},
        "factor_scores": {
            "type": "object",
            "properties": {
                factor_name: {"type": "number", "minimum": minimum, "maximum": maximum}
                for factor_name, (minimum, maximum) in FACTOR_SCORE_LIMITS.items()
            },
            "required": list(FACTOR_SCORE_LIMITS),
        },
        "rationale": {"type": "string"},
    },
    "required": ["ai_priority_score", "factor_scores", "rationale"],
}


def _validate_prioritizer_response(data: dict[str, Any]) -> tuple[float, dict[str, float], str]:
    ai_priority_score = float(data.get("ai_priority_score"))
    if not 0.0 <= ai_priority_score <= 100.0:
        raise ValueError("ai_priority_score must be between 0 and 100.")

    raw_factor_scores = data.get("factor_scores")
    if not isinstance(raw_factor_scores, dict):
        raise ValueError("factor_scores must be an object.")

    factor_scores: dict[str, float] = {}
    for factor_name, (minimum, maximum) in FACTOR_SCORE_LIMITS.items():
        if factor_name not in raw_factor_scores:
            raise ValueError(f"factor_scores is missing {factor_name}.")
        score = float(raw_factor_scores[factor_name])
        if not minimum <= score <= maximum:
            raise ValueError(f"factor score {factor_name} must be between {minimum:g} and {maximum:g}.")
        factor_scores[factor_name] = score

    rationale = str(data.get("rationale", "")).strip()
    if not rationale:
        raise ValueError("rationale is required.")
    if len(rationale) > 800:
        raise ValueError("rationale must be concise.")
    lowered_rationale = rationale.lower()
    if any(claim in lowered_rationale for claim in PROHIBITED_RATIONALE_CLAIMS):
        raise ValueError("rationale contains an unsupported execution or compliance claim.")
    return round(ai_priority_score, 3), factor_scores, rationale


def run_c2_prioritizer_ai(priority_payload: dict[str, Any]) -> C2PrioritizationResponse:
    if not AI_ENABLED:
        return prioritization_fallback_response(
            "AI_ENABLED is false.",
            priority_payload,
            MODEL_C2_PRIORITIZER,
        )

    result = request_json(
        MODEL_C2_PRIORITIZER,
        SYSTEM_PROMPT,
        priority_payload,
        response_schema=C2_RESPONSE_SCHEMA,
    )
    if not result.data:
        return prioritization_fallback_response(
            result.metadata.fallback_reason or "C2 prioritizer AI returned no usable response.",
            priority_payload,
            MODEL_C2_PRIORITIZER,
        )

    try:
        ai_priority_score, factor_scores, rationale = _validate_prioritizer_response(result.data)
        return C2PrioritizationResponse(
            ai_priority_score=ai_priority_score,
            factor_scores=factor_scores,
            rationale=rationale,
            metadata=result.metadata,
        )
    except Exception as exc:
        return prioritization_fallback_response(
            f"C2 prioritizer AI response validation failed: {exc}",
            priority_payload,
            MODEL_C2_PRIORITIZER,
        )
