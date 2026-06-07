"""Environment-based configuration for optional AI services."""

from __future__ import annotations

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_positive_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
        return value if value > 0 else default
    except (TypeError, ValueError):
        return default


AI_ENABLED = _get_bool("AI_ENABLED", False)
AI_PROVIDER = os.getenv("AI_PROVIDER", "disabled").strip() or "disabled"
AI_BASE_URL = os.getenv("AI_BASE_URL", "").strip()
AI_API_KEY = os.getenv("AI_API_KEY", "").strip()

MODEL_C1_MATCHING = os.getenv("MODEL_C1_MATCHING", "llama-family-matching-model").strip()
MODEL_C2_PRIORITIZER = os.getenv("MODEL_C2_PRIORITIZER", "gemma-family-prioritizer-model").strip()
MODEL_C3_ANOMALY = os.getenv("MODEL_C3_ANOMALY", "chronos-family-anomaly-model").strip()
MODEL_C3_REPORT = os.getenv("MODEL_C3_REPORT", "lightweight-report-drafter-model").strip()

AI_TIMEOUT_SECONDS = _get_positive_int("AI_TIMEOUT_SECONDS", 120)

CHRONOS_ENABLED = _get_bool("CHRONOS_ENABLED", False)
CHRONOS_BASE_URL = os.getenv("CHRONOS_BASE_URL", "http://127.0.0.1:9001/anomaly").strip()
CHRONOS_MODEL_NAME = os.getenv("CHRONOS_MODEL_NAME", "amazon/chronos-bolt-small").strip()
