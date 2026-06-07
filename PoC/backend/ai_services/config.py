"""Environment-based configuration for optional AI services."""

from __future__ import annotations

import os
from pathlib import Path

# Load backend/.env into os.environ before any os.getenv() calls.
# Uses a plain reader so there is no dependency on python-dotenv being installed.
def _load_env_file() -> None:
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

_load_env_file()


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
