from __future__ import annotations

import re
from pathlib import Path
from typing import Any

MIN_MAPPING_SELECTION_SCORE = 0.55
MAPPING_REVIEW_THRESHOLD = 0.65
READY_APPROVAL_THRESHOLD = 0.70
MAX_PENDING_ANOMALY_REVIEWS = 4
REFERENCE_MAPPINGS_PATH = Path(__file__).resolve().parent / "data" / "reference_mappings.json"

EXTERNAL_HMI_VALIDATION_TERMS: set[str] = {
    "warning lamp",
    "dashboard",
    "instrument cluster",
    "cluster display",
    "hud",
    "display message",
    "visual alert",
    "buzzer",
    "chime",
    "speaker",
    "audible alert",
    "warning sound",
}

REQUIREMENT_COLUMN_CANDIDATES: set[str] = {
    "description",
    "requirement",
    "requirements",
    "requirement_text",
    "requirement_description",
    "software_requirement",
    "software_requirements",
    "software_safety_requirement",
    "software_safety_requirements",
    "safety_requirement",
    "safety_requirements",
    "req_description",
    "req_text",
    "functional_requirement",
    "functional_requirements",
}

ID_COLUMN_CANDIDATES: set[str] = {
    "id",
    "requirement_id",
    "req_id",
    "requirement_number",
    "requirement_no",
    "req_no",
    "req_number",
    "identifier",
    "requirement_identifier",
}

ASIL_COLUMN_CANDIDATES: set[str] = {
    "asil",
    "asil_level",
    "asil_rating",
    "safety_level",
    "integrity_level",
    "automotive_safety_integrity_level",
}

REQUIREMENT_KEYWORD_PATTERN = re.compile(
    r"\b(shall|must|required|requirement|system|software|ecu|fault|safe state|diagnostic|detect|monitor|verify)\b",
    re.IGNORECASE,
)

TECHNICAL_KEYWORD_GROUPS: dict[str, set[str]] = {
    "timing": {"within", "ms", "second", "delay", "latency", "timing", "timeout", "debounce", "interval"},
    "fault": {"fault", "failure", "invalid", "inconsistent", "implausible", "corruption", "degraded", "diagnostic", "dtc"},
    "fallback": {"fallback", "safe", "safe state", "limp", "disable", "suppression", "recovery", "default"},
    "threshold": {"threshold", "exceeds", "below", "above", "minimum", "maximum", "limit", "tolerance", "range"},
    "sensor": {"sensor", "plausibility", "redundant", "mismatch", "signal", "stuck", "noisy", "cross-check"},
    "communication": {"communication", "can", "message", "bus", "gateway", "payload", "stale", "unavailable", "routing"},
    "electrical": {"voltage", "undervoltage", "overvoltage", "supply", "short", "open", "load", "transient"},
    "thermal": {"thermal", "temperature", "overheating", "derating", "cooling", "cold", "heat"},
    "hmi": {"warning", "display", "indicator", "telltale", "driver", "alert", "visibility", "screen"},
    "cybersecurity": {"unauthorized", "authentication", "replay", "session", "secure", "access", "request"},
    "memory": {"memory", "checksum", "freeze-frame", "storage", "persistent", "reset", "recording"},
    "actuator": {"actuator", "movement", "torque", "brake", "steering", "lamp", "contactor", "deployment"},
}

STOPWORDS: set[str] = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it", "of", "on", "or",
    "that", "the", "to", "under", "when", "with", "after", "before", "during", "shall", "must", "verify",
    "system", "software", "ecu", "required", "requirement", "control", "behavior", "case", "test",
}

DOMAIN_TO_TEST_CODES: dict[str, set[str]] = {
    "brake": {"BRK", "CC", "TRQ"},
    "braking": {"BRK", "CC", "TRQ"},
    "steering": {"STR", "RVC", "LGT"},
    "lighting": {"LGT", "CLU"},
    "lamp": {"LGT", "CLU"},
    "headlamp": {"LGT", "CLU"},
    "torque": {"TRQ", "CC", "STR"},
    "powertrain": {"TRQ", "CC"},
    "airbag": {"SRS", "CLU"},
    "restraint": {"SRS", "CLU"},
    "cluster": {"CLU", "LGT", "SRS", "BMS"},
    "display": {"CLU", "RVC"},
    "door": {"LOCK"},
    "lock": {"LOCK"},
    "battery": {"BMS", "CLU", "TRQ"},
    "charging": {"BMS"},
    "cruise": {"CC", "TRQ", "BRK"},
    "camera": {"RVC", "CLU"},
    "rearview": {"RVC", "CLU"},
}
