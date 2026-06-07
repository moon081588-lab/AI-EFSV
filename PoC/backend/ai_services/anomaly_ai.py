"""C3 anomaly adapter for the isolated Chronos-Bolt service."""

from __future__ import annotations

import json
import math
import socket
import statistics
import urllib.error
import urllib.request
from typing import Any

from .config import AI_TIMEOUT_SECONDS, CHRONOS_BASE_URL, CHRONOS_ENABLED, CHRONOS_MODEL_NAME
from .schemas import AIMetadata, C3AnomalyResponse

VALID_ANOMALY_TYPES = {
    "Timing Boundary",
    "Diagnostic Response",
    "Communication Timeout",
    "Safety Fallback Behavior",
    "Sensor Plausibility",
    "Electrical Recovery",
    "Thermal Boundary",
    "HMI Priority",
    "Calibration Configuration",
    "Data Integrity Anomaly",
    "None",
}
VALID_ENGINEER_ACTIONS = {"Accept", "Deny", "Escalate", "Re-test"}


def _classify_anomaly(text: str) -> str:
    lowered = text.lower()
    rules = [
        ("Communication Timeout", ("timeout", "communication", "message loss")),
        ("Safety Fallback Behavior", ("fallback", "safe state", "degraded")),
        ("Sensor Plausibility", ("sensor", "plausibility", "redundant", "mismatch")),
        ("Electrical Recovery", ("voltage", "electrical", "recovery")),
        ("Thermal Boundary", ("thermal", "temperature", "derating")),
        ("HMI Priority", ("warning", "display", "cluster", "hmi", "audible")),
        ("Calibration Configuration", ("calibration", "configuration", "variant")),
        ("Data Integrity Anomaly", ("storage", "memory", "checksum", "freeze-frame", "reset")),
        ("Diagnostic Response", ("diagnostic", "dtc", "response code")),
        ("Timing Boundary", ("timing", "latency", "delay", "within", "ms")),
    ]
    return next((name for name, terms in rules if any(term in lowered for term in terms)), "Timing Boundary")


def _statistical_fallback(observation_payload: dict[str, Any], reason: str) -> C3AnomalyResponse:
    series = [float(value) for value in observation_payload.get("observed_series", [])]
    expected_range = observation_payload.get("expected_range", [0, 0])
    minimum = float(expected_range[0]) if len(expected_range) >= 2 else 0.0
    maximum = float(expected_range[1]) if len(expected_range) >= 2 else 0.0
    protocol_text = " ".join(str(item) for item in observation_payload.get("protocol_logs", []))
    context_text = " ".join(
        [
            str(observation_payload.get("test_case_name", "")),
            str(observation_payload.get("expected_behavior", "")),
            protocol_text,
        ]
    )
    range_violations = [value for value in series if value < minimum or value > maximum]
    protocol_failure = any(
        term in protocol_text.lower()
        for term in ("timeout", "failure", "failed", "fallback delayed", "anomaly", "invalid", "mismatch")
    )
    deviation = 0.0
    if len(series) >= 6:
        split = max(3, int(len(series) * 0.7))
        context = series[:split]
        target = series[split:]
        center = statistics.mean(context)
        spread = max(statistics.pstdev(context), max(abs(maximum - minimum) * 0.03, 0.01))
        deviation = max((abs(value - center) / spread for value in target), default=0.0)

    review_required = bool(range_violations or protocol_failure or deviation > 4.0 or not series)
    confidence = min(0.99, 0.55 + min(len(range_violations) * 0.08, 0.24) + (0.12 if protocol_failure else 0) + min(deviation / 20, 0.08))
    if not review_required:
        confidence = min(0.95, 0.65 + min(len(series), 30) / 100)

    observed_behavior = (
        f"{len(range_violations)} value(s) outside expected range [{minimum:g}, {maximum:g}]."
        if range_violations
        else "Observed series remained within the configured expected range."
    )
    if protocol_failure:
        observed_behavior += " Protocol evidence contains failure-related indicators."

    return C3AnomalyResponse(
        verdict="REVIEW" if review_required else "PASS",
        anomaly_type=_classify_anomaly(context_text) if review_required else "None",
        confidence=round(confidence, 3),
        observed_behavior=observed_behavior,
        explanation=(
            "Deterministic statistical fallback detected range, trend, or protocol indicators requiring engineer review."
            if review_required
            else "Deterministic statistical fallback found no range, trend, or protocol anomaly indicators."
        ),
        recommended_engineer_action="Re-test" if review_required else "Accept",
        metadata=AIMetadata(
            ai_used=False,
            model_name=CHRONOS_MODEL_NAME or None,
            fallback_used=True,
            fallback_reason=reason,
        ),
    )


def _validate_chronos_response(data: dict[str, Any]) -> C3AnomalyResponse:
    verdict = str(data.get("verdict", "")).upper()
    anomaly_type = str(data.get("anomaly_type", ""))
    action = str(data.get("recommended_engineer_action", ""))
    confidence = float(data.get("confidence"))
    metadata = data.get("metadata")
    if verdict not in {"PASS", "REVIEW"}:
        raise ValueError("Chronos verdict must be PASS or REVIEW.")
    if anomaly_type not in VALID_ANOMALY_TYPES:
        raise ValueError("Chronos anomaly_type is invalid.")
    if action not in VALID_ENGINEER_ACTIONS:
        raise ValueError("Chronos recommended_engineer_action is invalid.")
    if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
        raise ValueError("Chronos confidence must be between 0 and 1.")
    if not isinstance(metadata, dict):
        raise ValueError("Chronos metadata is missing.")
    ai_used = bool(metadata.get("ai_used", False))
    fallback_used = bool(metadata.get("fallback_used", False))
    if ai_used == fallback_used:
        raise ValueError("Chronos metadata must identify either AI use or fallback use.")
    if fallback_used and not metadata.get("fallback_reason"):
        raise ValueError("Chronos fallback metadata requires a fallback_reason.")
    return C3AnomalyResponse(
        verdict=verdict,
        anomaly_type=anomaly_type,
        confidence=confidence,
        observed_behavior=str(data.get("observed_behavior", "")),
        explanation=str(data.get("explanation", "")),
        recommended_engineer_action=action,
        metadata=AIMetadata(**metadata),
    )


def run_c3_anomaly_ai(observation_payload: dict[str, Any]) -> C3AnomalyResponse:
    if not CHRONOS_ENABLED:
        return _statistical_fallback(observation_payload, "CHRONOS_ENABLED is false.")
    if not CHRONOS_BASE_URL:
        return _statistical_fallback(observation_payload, "CHRONOS_BASE_URL is not configured.")

    request = urllib.request.Request(
        CHRONOS_BASE_URL,
        data=json.dumps(observation_payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=AI_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Chronos response must be a JSON object.")
        return _validate_chronos_response(data)
    except (TimeoutError, socket.timeout):
        reason = f"Chronos request timed out after {AI_TIMEOUT_SECONDS} seconds."
    except urllib.error.HTTPError as exc:
        reason = f"Chronos endpoint returned HTTP {exc.code}."
    except urllib.error.URLError as exc:
        reason = f"Chronos endpoint request failed: {exc.reason}."
    except json.JSONDecodeError:
        reason = "Chronos endpoint returned invalid JSON."
    except (ValueError, TypeError, KeyError) as exc:
        reason = f"Chronos response validation failed: {exc}"
    except Exception as exc:
        reason = f"Unexpected Chronos request failure: {exc}"
    return _statistical_fallback(observation_payload, reason)
