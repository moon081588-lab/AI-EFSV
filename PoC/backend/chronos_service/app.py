"""Isolated Chronos-Bolt anomaly detection service."""

from __future__ import annotations

import math
import os
import statistics
import threading
from typing import Any, Literal, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

CHRONOS_MODEL_NAME = os.getenv("CHRONOS_MODEL_NAME", "amazon/chronos-bolt-small").strip()

app = FastAPI(title="AI-EFSV Chronos-Bolt Anomaly Service")
_pipeline: Any = None
_device = "cpu"
_load_error: Optional[str] = None
_load_lock = threading.Lock()


@app.on_event("startup")
def _auto_load() -> None:
    """Start loading the Chronos model in the background at service startup."""
    threading.Thread(target=_load_pipeline, daemon=True).start()
MIN_CHRONOS_SERIES_LENGTH = 12


class AnomalyRequest(BaseModel):
    test_case_id: str
    test_case_name: str
    signal_name: str
    expected_range: list[float] = Field(min_length=2, max_length=2)
    observed_series: list[float] = Field(min_length=1)
    expected_behavior: str
    protocol_logs: list[str] = Field(default_factory=list)
    linked_requirements: list[dict[str, Any]] = Field(default_factory=list)


class Metadata(BaseModel):
    ai_used: bool
    model_name: Optional[str]
    fallback_used: bool
    fallback_reason: Optional[str]


class AnomalyResponse(BaseModel):
    verdict: Literal["PASS", "REVIEW"]
    anomaly_type: str
    confidence: float
    observed_behavior: str
    explanation: str
    recommended_engineer_action: Literal["Accept", "Deny", "Escalate", "Re-test"]
    metadata: Metadata


def _load_pipeline() -> Any:
    global _pipeline, _device, _load_error
    if _pipeline is not None or _load_error is not None:
        return _pipeline
    with _load_lock:
        if _pipeline is not None or _load_error is not None:
            return _pipeline
        try:
            import torch
            from chronos import ChronosBoltPipeline

            _device = "cuda" if torch.cuda.is_available() else "cpu"
            dtype = torch.bfloat16 if _device == "cuda" and torch.cuda.is_bf16_supported() else torch.float32
            _pipeline = ChronosBoltPipeline.from_pretrained(
                CHRONOS_MODEL_NAME,
                device_map=_device,
                dtype=dtype,
            )
        except Exception as exc:
            _load_error = f"{type(exc).__name__}: {exc}"
    return _pipeline


def _clean_series(values: list[float]) -> list[float]:
    series: list[float] = []
    for value in values:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("observed_series contains a non-finite value.")
        series.append(number)
    return series


def _classify(text: str) -> str:
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


def _protocol_failure(logs: list[str]) -> bool:
    text = " ".join(logs).lower()
    return any(
        term in text
        for term in (
            "timeout",
            "failure",
            "failed",
            "delayed",
            "fallback",
            "dtc",
            "anomaly",
            "invalid",
            "mismatch",
            "out of range",
        )
    )


def _statistical_response(payload: AnomalyRequest, reason: str) -> AnomalyResponse:
    try:
        series = _clean_series(payload.observed_series)
    except (TypeError, ValueError) as exc:
        series = []
        reason = f"{reason}; invalid observed_series: {exc}"
    minimum, maximum = map(float, payload.expected_range)
    violations = [value for value in series if value < minimum or value > maximum]
    protocol_failure = _protocol_failure(payload.protocol_logs)
    split = max(3, int(len(series) * 0.7))
    context, target = series[:split], series[split:]
    center = statistics.mean(context) if context else 0.0
    spread = max(statistics.pstdev(context), max(abs(maximum - minimum) * 0.03, 0.01)) if len(context) > 1 else 0.01
    deviation = max((abs(value - center) / spread for value in target), default=0.0)
    review = bool(violations or protocol_failure or deviation > 4.0)
    confidence = min(0.99, 0.55 + min(len(violations) * 0.08, 0.24) + (0.12 if protocol_failure else 0) + min(deviation / 20, 0.08))
    if not review:
        confidence = min(0.95, 0.65 + min(len(series), 30) / 100)
    context_text = f"{payload.test_case_name} {payload.expected_behavior} {' '.join(payload.protocol_logs)}"
    return AnomalyResponse(
        verdict="REVIEW" if review else "PASS",
        anomaly_type=_classify(context_text) if review else "None",
        confidence=round(confidence, 3),
        observed_behavior=(
            f"{len(violations)} value(s) exceeded expected range [{minimum:g}, {maximum:g}]."
            if violations
            else "Observed series remained within the configured expected range."
        ),
        explanation=(
            "Statistical fallback detected range, trend, or protocol indicators requiring engineer review."
            if review
            else "Statistical fallback found no range, trend, or protocol anomaly indicators."
        ),
        recommended_engineer_action="Re-test" if review else "Accept",
        metadata=Metadata(
            ai_used=False,
            model_name=CHRONOS_MODEL_NAME or None,
            fallback_used=True,
            fallback_reason=f"Chronos model unavailable: {reason}",
        ),
    )


def _chronos_response(payload: AnomalyRequest, pipeline: Any) -> AnomalyResponse:
    import torch

    series = _clean_series(payload.observed_series)
    if len(series) < MIN_CHRONOS_SERIES_LENGTH:
        raise ValueError(f"Observed series is too short for Chronos inference; minimum length is {MIN_CHRONOS_SERIES_LENGTH}.")
    minimum, maximum = map(float, payload.expected_range)
    target_length = max(1, min(8, len(series) // 3))
    context = series[:-target_length]
    target = series[-target_length:]
    if len(context) < 4:
        raise ValueError("Observed series is too short for Chronos forecast comparison.")

    quantiles, _ = pipeline.predict_quantiles(
        context=torch.tensor(context, dtype=torch.float32),
        prediction_length=target_length,
        quantile_levels=[0.1, 0.5, 0.9],
    )
    values = quantiles.detach().cpu().float().numpy()
    while values.ndim > 2:
        values = values[0]
    lower = values[:, 0].tolist()
    median = values[:, 1].tolist()
    upper = values[:, 2].tolist()
    forecast_violations = sum(1 for value, low, high in zip(target, lower, upper) if value < low or value > high)
    range_violations = sum(1 for value in series if value < minimum or value > maximum)
    protocol_failure = _protocol_failure(payload.protocol_logs)
    review = bool(range_violations or forecast_violations or protocol_failure)
    confidence = min(0.99, 0.58 + min(range_violations * 0.08, 0.2) + min(forecast_violations * 0.07, 0.2) + (0.1 if protocol_failure else 0))
    if not review:
        confidence = 0.86
    context_text = f"{payload.test_case_name} {payload.expected_behavior} {' '.join(payload.protocol_logs)}"
    median_error = statistics.mean(abs(actual - expected) for actual, expected in zip(target, median))
    return AnomalyResponse(
        verdict="REVIEW" if review else "PASS",
        anomaly_type=_classify(context_text) if review else "None",
        confidence=round(confidence, 3),
        observed_behavior=(
            f"Chronos comparison found {forecast_violations} forecast-interval deviation(s) and "
            f"{range_violations} expected-range violation(s)."
        ),
        explanation=(
            f"Recent observations were compared with Chronos-Bolt forecast quantiles; mean median-forecast error was {median_error:.3f}. "
            "This is simulated decision support and does not represent real ECU or ISO 26262 validation."
        ),
        recommended_engineer_action="Re-test" if review else "Accept",
        metadata=Metadata(
            ai_used=True,
            model_name=CHRONOS_MODEL_NAME,
            fallback_used=False,
            fallback_reason=None,
        ),
    )


@app.get("/health")
def health(load_model: bool = False) -> dict[str, Any]:
    global _device
    try:
        import torch

        _device = "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        _device = "cpu"
    if load_model:
        _load_pipeline()
    response = {
        "status": "ok",
        "model_name": CHRONOS_MODEL_NAME,
        "model_loaded": _pipeline is not None,
        "device": _device,
        "fallback_available": True,
    }
    if _load_error:
        response["load_error"] = _load_error
    return response


@app.post("/anomaly", response_model=AnomalyResponse)
def anomaly(payload: AnomalyRequest) -> AnomalyResponse:
    pipeline = _load_pipeline()
    if pipeline is None:
        return _statistical_response(payload, _load_error or "unknown model load failure")
    try:
        return _chronos_response(payload, pipeline)
    except Exception as exc:
        return _statistical_response(payload, str(exc))
