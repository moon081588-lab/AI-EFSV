from __future__ import annotations

import difflib
import io
import json
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai_services.matching_ai import run_c1_matching_ai
from ai_services.anomaly_ai import run_c3_anomaly_ai
from ai_services.prioritizer_ai import run_c2_prioritizer_ai
from ai_services.report_ai import run_c3_report_drafter_ai


app = FastAPI(title="AI Assisted Software Verification Tool API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


MIN_MAPPING_SELECTION_SCORE = 0.55
MAPPING_REVIEW_THRESHOLD = 0.65
READY_APPROVAL_THRESHOLD = 0.70
MAX_PENDING_ANOMALY_REVIEWS = 4
REFERENCE_MAPPINGS_PATH = Path(__file__).resolve().parent / "data" / "reference_mappings.json"
EXTERNAL_HMI_VALIDATION_TERMS = {
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


TEST_CASE_TOPICS: dict[str, dict[str, Any]] = {
    "BRK": {
        "base_name": "Brake Control Verification",
        "test_type": "Functional Safety",
        "duration_base": 28,
        "descriptions": [
            "Verify commanded brake force accuracy under normal braking conditions.",
            "Verify brake pressure sensor fault detection within the required diagnostic time.",
            "Verify degraded braking mode entry when hydraulic pressure is below the safe threshold.",
            "Verify driver warning when regenerative braking is unavailable.",
            "Verify friction braking priority when regenerative braking torque is insufficient.",
            "Verify unintended brake release prevention during emergency braking.",
            "Verify stable brake force distribution during split-mu road conditions.",
            "Verify diagnostic trouble code storage when brake actuator response is delayed.",
            "Verify automatic hold release behavior above the configured speed threshold.",
            "Verify brake pedal plausibility using redundant pedal position signals.",
            "Verify brake actuator response timing during repeated braking events.",
            "Verify brake fault safe-state transition after communication timeout.",
            "Verify brake warning indicator request after critical braking fault detection.",
            "Verify brake control recovery behavior after transient voltage disturbance.",
            "Verify brake system traceability from safety requirement to executable test case.",
        ],
    },
    "STR": {
        "base_name": "Steering Assist Verification",
        "test_type": "Fault Injection",
        "duration_base": 32,
        "descriptions": [
            "Verify steering assist manual fallback after steering angle sensor fault detection.",
            "Verify assistance torque limitation when steering torque sensor values are inconsistent.",
            "Verify driver warning when electric power steering enters degraded mode.",
            "Verify unintended steering torque prevention during ignition-on self-test.",
            "Verify diagnostic trouble code storage when steering motor current exceeds the safe limit.",
            "Verify smooth assistance reduction when battery voltage is below the operating threshold.",
            "Verify steering angle sensor plausibility before lane keeping support activation.",
            "Verify manual steering availability after power assist failure.",
            "Verify assistance output suppression when calibration data is invalid.",
            "Verify steering motor overheating detection and torque derating request.",
            "Verify steering fallback timing under intermittent sensor communication loss.",
            "Verify steering control safe state after watchdog timeout.",
            "Verify steering diagnostic response after redundant signal mismatch.",
            "Verify steering assist availability after ignition cycle reset.",
            "Verify steering requirement traceability to fallback and diagnostic test cases.",
        ],
    },
    "LGT": {
        "base_name": "Lighting System Verification",
        "test_type": "Electrical Validation",
        "duration_base": 18,
        "descriptions": [
            "Verify headlamp beam intensity compliance during supply voltage fluctuation.",
            "Verify low beam fallback when high beam actuator feedback is invalid.",
            "Verify driver alert when adaptive headlamp leveling fails.",
            "Verify beam angle lowering under rear axle load increase to prevent glare.",
            "Verify safe default lighting mode when ambient light sensor input is unavailable.",
            "Verify left and right lamp synchronization during automatic beam adjustment.",
            "Verify diagnostic trouble code storage when LED driver temperature exceeds threshold.",
            "Verify daytime running lamp continuity after non-critical adaptive lighting failure.",
            "Verify open circuit failure detection in the low beam output channel.",
            "Verify adaptive bending function disablement when steering angle input is implausible.",
            "Verify headlamp recovery after transient electrical disturbance.",
            "Verify lighting fault communication to the instrument cluster.",
            "Verify lamp output status consistency during ignition cycle transition.",
            "Verify lighting control behavior under reduced battery voltage.",
            "Verify lighting requirement traceability to electrical validation evidence.",
        ],
    },
    "TRQ": {
        "base_name": "Powertrain Torque Verification",
        "test_type": "Dynamic Control",
        "duration_base": 40,
        "descriptions": [
            "Verify engine torque limitation to prevent wheel spin on low-traction surfaces.",
            "Verify torque reduction when accelerator pedal signals are inconsistent.",
            "Verify limp-home mode entry when throttle actuator feedback is invalid.",
            "Verify unintended acceleration prevention during startup initialization.",
            "Verify throttle response timing and delayed actuator movement detection.",
            "Verify torque request suppression when brake override is active.",
            "Verify torque reduction when coolant temperature exceeds the thermal protection threshold.",
            "Verify freeze-frame storage after safety-relevant torque monitoring fault detection.",
            "Verify torque request plausibility before forwarding output to the powertrain actuator.",
            "Verify torque command reset to safe default after watchdog timeout.",
            "Verify torque command arbitration during conflicting driver inputs.",
            "Verify powertrain diagnostic response after actuator communication timeout.",
            "Verify torque control stability during rapid pedal input change.",
            "Verify torque fallback behavior after invalid calibration detection.",
            "Verify torque requirement traceability to powertrain safety test cases.",
        ],
    },
    "SRS": {
        "base_name": "Airbag and Restraint Verification",
        "test_type": "Safety Critical Timing",
        "duration_base": 38,
        "descriptions": [
            "Verify frontal airbag deployment timing after confirmed crash detection.",
            "Verify passenger airbag suppression when occupant weight is below the threshold.",
            "Verify crash sensor plausibility before deployment decision.",
            "Verify deployment event data recording after crash-triggered activation.",
            "Verify driver alert when restraint control module memory corruption is detected.",
            "Verify deployment output disablement when squib resistance is outside the allowed range.",
            "Verify power-on self-test before enabling deployment readiness.",
            "Verify deployment readiness during transient battery voltage drop.",
            "Verify side-impact sensor failure detection and diagnostic trouble code setting.",
            "Verify unintended deployment prevention during normal driving vibration events.",
            "Verify restraint system safe state after internal watchdog reset.",
            "Verify crash signal confirmation logic using redundant sensor inputs.",
            "Verify airbag warning request to the instrument cluster after restraint degradation.",
            "Verify restraint diagnostic response for squib circuit open load condition.",
            "Verify restraint requirement traceability to deployment and suppression test evidence.",
        ],
    },
    "CLU": {
        "base_name": "Instrument Cluster Verification",
        "test_type": "HMI Verification",
        "duration_base": 16,
        "descriptions": [
            "Verify coolant temperature display accuracy across normal operating conditions.",
            "Verify brake system warning display after receiving critical brake fault signal.",
            "Verify airbag warning display when restraint system status is degraded.",
            "Verify battery thermal warning display after battery management system alert request.",
            "Verify steering assist warning display when electric power steering enters fallback mode.",
            "Verify safety-critical warning priority over infotainment notifications.",
            "Verify warning indicator visibility under day and night brightness settings.",
            "Verify safe warning display mode after display communication timeout.",
            "Verify last active warning state storage after ignition cycle reset.",
            "Verify telltale lamp operation during startup self-check.",
            "Verify cluster warning latency for high-priority safety messages.",
            "Verify cluster fault indication consistency during communication recovery.",
            "Verify cluster message display when multiple ECU warnings are active.",
            "Verify cluster fallback screen after invalid display data reception.",
            "Verify instrument cluster requirement traceability to HMI evidence.",
        ],
    },
    "LOCK": {
        "base_name": "Door Lock Control Verification",
        "test_type": "Body Control",
        "duration_base": 14,
        "descriptions": [
            "Verify door unlock prevention when vehicle speed is above the configured threshold.",
            "Verify automatic door unlock after crash event confirmation.",
            "Verify unlock request rejection when child lock safety mode is active.",
            "Verify door latch sensor inconsistency detection and driver notification.",
            "Verify locked state retention after transient communication loss with body control module.",
            "Verify diagnostic trouble code storage when lock actuator movement is incomplete.",
            "Verify driver door closed status before enabling drive-away locking.",
            "Verify unintended unlocking prevention during remote key authentication failure.",
            "Verify passive unlock disablement when key signal strength is below the security threshold.",
            "Verify audible feedback after successful remote lock command.",
            "Verify lock actuator response timing during repeated lock and unlock cycles.",
            "Verify crash unlock priority over normal lock state control.",
            "Verify door lock state consistency after ignition cycle reset.",
            "Verify body control diagnostic response after actuator short circuit detection.",
            "Verify door lock requirement traceability to body control test evidence.",
        ],
    },
    "BMS": {
        "base_name": "Battery Management Verification",
        "test_type": "Thermal Safety",
        "duration_base": 30,
        "descriptions": [
            "Verify driver alert when battery temperature exceeds safe thermal thresholds.",
            "Verify charging current limitation when cell temperature exceeds warning threshold.",
            "Verify high-voltage contactor opening when isolation resistance is below safe threshold.",
            "Verify cell voltage imbalance detection above the configured diagnostic threshold.",
            "Verify discharge power reduction when battery state of charge is critically low.",
            "Verify fault data storage when thermal runaway risk condition is detected.",
            "Verify current sensor plausibility using redundant measurement paths.",
            "Verify vehicle shutdown request when high-voltage interlock loop is open.",
            "Verify charging limitation status communication to the instrument cluster.",
            "Verify battery management safe state after internal watchdog failure.",
            "Verify battery thermal derating under sustained high-load discharge.",
            "Verify contactor command suppression after high-voltage diagnostic fault detection.",
            "Verify battery fault traceability from sensor input to driver warning request.",
            "Verify BMS communication timeout handling during charging operation.",
            "Verify battery requirement traceability to thermal and electrical safety evidence.",
        ],
    },
    "CC": {
        "base_name": "Cruise Control Verification",
        "test_type": "Driver Assistance",
        "duration_base": 17,
        "descriptions": [
            "Verify cruise control disengagement when the brake pedal is pressed.",
            "Verify cruise control disengagement when accelerator pedal override threshold is exceeded.",
            "Verify cruise control activation rejection below the minimum configured vehicle speed.",
            "Verify driver alert when radar input required for adaptive cruise is unavailable.",
            "Verify target speed maintenance within tolerance on level road.",
            "Verify activation request rejection when brake switch status is invalid.",
            "Verify smooth set-speed reduction when following distance becomes unsafe.",
            "Verify control output cancellation after communication timeout with powertrain controller.",
            "Verify diagnostic data storage when speed control actuator response is delayed.",
            "Verify visual indication when cruise control is active.",
            "Verify cruise control fallback after sensor plausibility failure.",
            "Verify cruise control state reset after ignition cycle transition.",
            "Verify cruise control driver override priority during active control.",
            "Verify adaptive cruise warning display after object detection loss.",
            "Verify cruise control requirement traceability to driver assistance evidence.",
        ],
    },
    "RVC": {
        "base_name": "Rearview Camera Verification",
        "test_type": "HMI Timing",
        "duration_base": 12,
        "descriptions": [
            "Verify rearview camera feed display within the required time after reverse gear selection.",
            "Verify driver warning when camera video signal is unavailable.",
            "Verify guide line overlay alignment within configured tolerance.",
            "Verify rear display switch-off after reverse gear is disengaged.",
            "Verify fallback warning screen after camera communication timeout.",
            "Verify image brightness adjustment during low-light reverse operation.",
            "Verify frozen image prevention during active reverse mode.",
            "Verify video frame freshness before rendering the image to the display.",
            "Verify diagnostic trouble code storage when camera module self-test fails.",
            "Verify dynamic guide line disablement when steering angle input is invalid.",
            "Verify rearview camera recovery after transient video signal interruption.",
            "Verify reverse gear input plausibility before camera activation.",
            "Verify rearview camera message display after camera calibration error.",
            "Verify camera feed timing during repeated gear shift cycles.",
            "Verify rearview camera requirement traceability to HMI timing evidence.",
        ],
    },
}


CONSTRAINT_PROFILES: list[dict[str, Any]] = [
    {
        "label": "Timing and latency constraint",
        "detail": "Constraint focus: response latency, diagnostic detection interval, debounce time, and timeout handling.",
        "duration_hours": 1,
    },
    {
        "label": "Voltage and electrical disturbance constraint",
        "detail": "Constraint focus: undervoltage, overvoltage, transient supply drop, short circuit, open load, and recovery after electrical disturbance.",
        "duration_hours": 3,
    },
    {
        "label": "Thermal operating constraint",
        "detail": "Constraint focus: high-temperature derating, cold-start behavior, thermal runaway prevention, overheating detection, and cooling recovery.",
        "duration_hours": 6,
    },
    {
        "label": "Sensor plausibility and redundancy constraint",
        "detail": "Constraint focus: redundant sensor mismatch, implausible signal range, stuck-at value, noisy signal filtering, and cross-check logic.",
        "duration_hours": 10,
    },
    {
        "label": "Communication and network constraint",
        "detail": "Constraint focus: CAN message loss, delayed message arrival, invalid payload, gateway routing failure, bus-off recovery, and stale signal handling.",
        "duration_hours": 14,
    },
    {
        "label": "Calibration and configuration constraint",
        "detail": "Constraint focus: invalid calibration data, variant coding mismatch, missing configuration parameter, and software baseline incompatibility.",
        "duration_hours": 22,
    },
    {
        "label": "Mechanical and actuator constraint",
        "detail": "Constraint focus: actuator saturation, limited movement range, mechanical backlash, incomplete movement, degraded output authority, and stuck actuator detection.",
        "duration_hours": 30,
    },
    {
        "label": "Environmental and road-load constraint",
        "detail": "Constraint focus: vibration, low-friction surface, slope, load variation, humidity, glare, ambient light shift, and harsh operating condition.",
        "duration_hours": 40,
    },
    {
        "label": "Human-machine interface constraint",
        "detail": "Constraint focus: warning priority, visibility, telltale consistency, driver acknowledgement, display fallback, and competing alert suppression.",
        "duration_hours": 52,
    },
    {
        "label": "Cybersecurity and access-control constraint",
        "detail": "Constraint focus: unauthorized diagnostic request, failed authentication, replayed command, invalid session transition, and secure fallback behavior.",
        "duration_hours": 64,
    },
    {
        "label": "Data integrity and memory constraint",
        "detail": "Constraint focus: corrupted memory, invalid checksum, freeze-frame consistency, event data recording, persistent fault storage, and recovery after reset.",
        "duration_hours": 78,
    },
    {
        "label": "Endurance and regression stability constraint",
        "detail": "Constraint focus: repeated operating cycles, long-duration stress, accumulated state drift, regression stability, and evidence consistency across reruns.",
        "duration_hours": 96,
    },
]


def duration_minutes_for_test_case(global_index: int) -> int:
    # Keep the full generated test portfolio below 720 hours total while still
    # including selected long-running tests up to 4 days for realistic regression planning.
    long_running_hours = {
        1: 96,
        2: 72,
        3: 48,
        4: 36,
        5: 24,
        6: 18,
        7: 12,
        8: 10,
        9: 8,
        10: 6,
    }
    if global_index in long_running_hours:
        return long_running_hours[global_index] * 60

    short_to_medium_hours = [1, 2, 3, 4, 5, 6]
    return short_to_medium_hours[(global_index - 11) % len(short_to_medium_hours)] * 60


def build_test_cases() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    global_index = 0
    for topic_position, (topic_code, topic_data) in enumerate(TEST_CASE_TOPICS.items()):
        for index, description in enumerate(topic_data["descriptions"], start=1):
            global_index += 1
            profile = CONSTRAINT_PROFILES[(topic_position * 3 + index - 1) % len(CONSTRAINT_PROFILES)]
            duration_minutes = duration_minutes_for_test_case(global_index)
            description_with_constraints = f"{description} {profile['detail']}"

            rows.append(
                {
                    "test_case_id": f"TC-{topic_code}-{index:03d}",
                    "test_case_name": f"{topic_data['base_name']} {index:03d}",
                    "description": description_with_constraints,
                    "constraint_category": profile["label"],
                    "duration_minutes": duration_minutes,
                    "test_type": topic_data["test_type"],
                }
            )
    return pd.DataFrame(rows)


TEST_CASES = build_test_cases()


def clean_cell_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value)
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_column_name(name: Any) -> str:
    text = clean_cell_text(name).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


REQUIREMENT_COLUMN_CANDIDATES = {
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

ID_COLUMN_CANDIDATES = {
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

ASIL_COLUMN_CANDIDATES = {
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

def score_requirement_table(df: pd.DataFrame) -> float:
    if df.empty:
        return 0

    normalized_columns = [normalize_column_name(column) for column in df.columns]
    column_score = 0
    if any(column in REQUIREMENT_COLUMN_CANDIDATES for column in normalized_columns):
        column_score += 120
    if any(column in ID_COLUMN_CANDIDATES for column in normalized_columns):
        column_score += 30
    if any(column in ASIL_COLUMN_CANDIDATES for column in normalized_columns):
        column_score += 30

    text_score = 0
    non_empty_rows = 0
    for _, row in df.head(150).iterrows():
        joined = " ".join(clean_cell_text(value) for value in row.tolist())
        if joined:
            non_empty_rows += 1
            if REQUIREMENT_KEYWORD_PATTERN.search(joined):
                text_score += 8
            if re.search(r"\bREQ[-_ ]?\d+\b|\bSWR[-_ ]?\d+\b|\bSSR[-_ ]?\d+\b", joined, re.IGNORECASE):
                text_score += 8
            if re.search(r"\bASIL\s*[ABCD]\b|\bQM\b", joined, re.IGNORECASE):
                text_score += 5

    return column_score + text_score + min(non_empty_rows, 50)


def read_csv_candidates(file_bytes: bytes) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    encodings = ("utf-8-sig", "utf-8", "latin-1")
    separators = (None, ",", ";", "\t", "|")

    for encoding in encodings:
        for separator in separators:
            try:
                df = pd.read_csv(
                    io.BytesIO(file_bytes),
                    encoding=encoding,
                    sep=separator,
                    engine="python",
                    dtype=str,
                    keep_default_na=False,
                )
                if not df.empty:
                    candidates.append(
                        {
                            "df": df,
                            "sheetName": "CSV file",
                            "headerRow": 1,
                            "encoding": encoding,
                            "separator": "auto" if separator is None else separator,
                        }
                    )
            except Exception:
                continue

    return candidates


def read_excel_candidates(file_bytes: bytes) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    excel = pd.ExcelFile(io.BytesIO(file_bytes))

    for sheet_name in excel.sheet_names:
        preview = pd.read_excel(excel, sheet_name=sheet_name, header=None, dtype=str, keep_default_na=False)
        max_header_rows = min(10, len(preview))

        for header_row in range(max_header_rows):
            try:
                df = pd.read_excel(
                    excel,
                    sheet_name=sheet_name,
                    header=header_row,
                    dtype=str,
                    keep_default_na=False,
                )
                df = df.dropna(axis=1, how="all")
                if not df.empty:
                    candidates.append(
                        {
                            "df": df,
                            "sheetName": sheet_name,
                            "headerRow": header_row + 1,
                            "encoding": None,
                            "separator": None,
                        }
                    )
            except Exception:
                continue

    return candidates


def parse_requirements_file(file_bytes: bytes, filename: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    name = filename.lower()

    try:
        if name.endswith(".csv"):
            candidates = read_csv_candidates(file_bytes)
            file_type = "CSV"
        elif name.endswith((".xlsx", ".xls")):
            candidates = read_excel_candidates(file_bytes)
            file_type = "Excel"
        else:
            raise ValueError("Unsupported file type. Upload CSV, XLSX, or XLS.")
    except Exception as exc:
        raise ValueError(f"Could not parse uploaded file: {exc}") from exc

    if not candidates:
        raise ValueError("Could not parse the uploaded file into a usable table.")

    best_candidate = max(candidates, key=lambda candidate: score_requirement_table(candidate["df"]))
    best_df = best_candidate["df"].copy()
    best_df.columns = [clean_cell_text(column) for column in best_df.columns]
    best_df = best_df.dropna(axis=1, how="all")
    best_df = best_df.dropna(axis=0, how="all")

    parser_info = {
        "status": "auto_parsed",
        "fileType": file_type,
        "sheetName": best_candidate.get("sheetName"),
        "headerRow": best_candidate.get("headerRow"),
        "encoding": best_candidate.get("encoding"),
        "separator": best_candidate.get("separator"),
        "candidateTablesScanned": len(candidates),
        "warnings": [],
    }

    if parser_info["headerRow"] and parser_info["headerRow"] != 1:
        parser_info["warnings"].append(f"Header row was detected automatically at row {parser_info['headerRow']}.")
    if len(candidates) > 1:
        parser_info["warnings"].append(f"Scanned {len(candidates)} possible table layouts and selected the highest-scoring requirement table.")

    return best_df, parser_info


def find_column_by_candidates(df: pd.DataFrame, candidates: set[str]) -> str | None:
    normalized_to_original = {normalize_column_name(column): column for column in df.columns}
    for candidate in candidates:
        if candidate in normalized_to_original:
            return normalized_to_original[candidate]
    return None


# Strict validation for required columns and blank cells
def validate_required_upload_columns(df: pd.DataFrame) -> None:
    required_column_groups = {
        "Requirement ID": ID_COLUMN_CANDIDATES,
        "Requirement Text": REQUIREMENT_COLUMN_CANDIDATES,
        "ASIL Level": ASIL_COLUMN_CANDIDATES,
    }

    missing_columns: list[str] = []
    blank_columns: list[str] = []

    for display_name, candidates in required_column_groups.items():
        column_name = find_column_by_candidates(df, candidates)
        if column_name is None:
            missing_columns.append(display_name)
            continue

        non_empty_values = df[column_name].map(clean_cell_text)
        if non_empty_values[non_empty_values != ""].empty:
            blank_columns.append(display_name)

    error_messages: list[str] = []
    if missing_columns:
        error_messages.append(f"missing required column(s): {', '.join(missing_columns)}")
    if blank_columns:
        error_messages.append(f"blank required column(s): {', '.join(blank_columns)}")

    if error_messages:
        raise ValueError(
            "400: Bad Request - uploaded requirement file has invalid structure; "
            + "; ".join(error_messages)
            + ". Required columns are Requirement ID, Requirement Text, and ASIL Level."
        )


def find_requirement_column(df: pd.DataFrame) -> str | None:
    direct_match = find_column_by_candidates(df, REQUIREMENT_COLUMN_CANDIDATES)
    if direct_match:
        return direct_match

    best_column = None
    best_score = 0.0
    for column in df.columns:
        values = df[column].map(clean_cell_text)
        non_empty_values = values[values != ""]
        if non_empty_values.empty:
            continue

        average_length = float(non_empty_values.map(len).mean())
        keyword_hits = int(non_empty_values.map(lambda value: bool(REQUIREMENT_KEYWORD_PATTERN.search(value))).sum())
        score = average_length + keyword_hits * 25

        if score > best_score:
            best_score = score
            best_column = column

    return best_column


def normalize_asil(value: Any) -> str:
    text = clean_cell_text(value).upper().replace("-", " ")
    if "ASIL D" in text or text == "D":
        return "D"
    if "ASIL C" in text or text == "C":
        return "C"
    if "ASIL B" in text or text == "B":
        return "B"
    if "ASIL A" in text or text == "A":
        return "A"
    if "QM" in text or "QUALITY MANAGED" in text:
        return "QM"
    return "QM"


def normalize_requirements(df: pd.DataFrame) -> pd.DataFrame:
    working = df.copy()
    working.columns = [clean_cell_text(column) for column in working.columns]

    validate_required_upload_columns(working)

    requirement_column = find_requirement_column(working)
    if requirement_column is None:
        raise ValueError(
            "No usable requirement text column was found. Include a requirement/description column or rows containing requirement-like text."
        )

    id_column = find_column_by_candidates(working, ID_COLUMN_CANDIDATES)
    asil_column = find_column_by_candidates(working, ASIL_COLUMN_CANDIDATES)

    normalized = pd.DataFrame(index=working.index)
    normalized["description"] = working[requirement_column].map(clean_cell_text)
    normalized = normalized[normalized["description"] != ""].copy()

    normalized = normalized[
        normalized["description"].map(
            lambda value: len(value) >= 12 and normalize_column_name(value) not in REQUIREMENT_COLUMN_CANDIDATES
        )
    ].copy()

    if normalized.empty:
        raise ValueError("No usable requirement descriptions were found in the uploaded file.")

    if id_column and id_column in working.columns:
        ids = working.loc[normalized.index, id_column].map(clean_cell_text)
        if ids[ids == ""].any():
            raise ValueError("400: Bad Request - Requirement ID column contains blank cell(s).")
        normalized["requirement_id"] = ids
    else:
        raise ValueError("400: Bad Request - Requirement ID column is required.")

    if asil_column and asil_column in working.columns:
        asil_values = working.loc[normalized.index, asil_column].map(clean_cell_text)
        if asil_values[asil_values == ""].any():
            raise ValueError("400: Bad Request - ASIL Level column contains blank cell(s).")
        normalized["asil_level"] = asil_values.map(normalize_asil)
    else:
        raise ValueError("400: Bad Request - ASIL Level column is required.")

    normalized = normalized[["requirement_id", "description", "asil_level"]].reset_index(drop=True)
    normalized["requirement_id"] = normalized["requirement_id"].map(clean_cell_text)
    normalized["requirement_id"] = normalized["requirement_id"].where(
        normalized["requirement_id"] != "",
        pd.Series([f"REQ-{i + 1:03d}" for i in range(len(normalized))]),
    )

    return normalized


def build_parser_info_details(raw_df: pd.DataFrame, normalized_df: pd.DataFrame, parser_info: dict[str, Any]) -> dict[str, Any]:
    working = raw_df.copy()
    working.columns = [clean_cell_text(column) for column in working.columns]

    requirement_column = find_requirement_column(working)
    id_column = find_column_by_candidates(working, ID_COLUMN_CANDIDATES)
    asil_column = find_column_by_candidates(working, ASIL_COLUMN_CANDIDATES)

    parser_info["requirementIdColumn"] = id_column or "Not found; generated automatically"
    parser_info["requirementTextColumn"] = requirement_column or "Not found"
    parser_info["asilColumn"] = asil_column or "Not found; defaulted to QM"
    parser_info["parsedRequirements"] = int(len(normalized_df))

    if id_column is None:
        parser_info["warnings"].append("Requirement ID column was not found. IDs were generated automatically.")
    if asil_column is None:
        parser_info["warnings"].append("ASIL column was not found. ASIL values defaulted to QM.")

    if requirement_column is not None:
        wrapped_count = int(working[requirement_column].astype(str).str.contains(r"\n|\r", regex=True).sum())
        if wrapped_count > 0:
            parser_info["warnings"].append(f"Detected and normalized wrapped or multiline text in {wrapped_count} requirement cell(s).")

    if not parser_info["warnings"]:
        parser_info["warnings"].append("File structure matched expected requirement table format.")

    return parser_info


# --- Traceability Matrix + Audit Log support ---

def infer_coverage_type(match_score: float) -> str:
    if match_score >= 0.85:
        return "Direct Coverage"
    if match_score >= READY_APPROVAL_THRESHOLD:
        return "Partial Coverage"
    if match_score >= MAPPING_REVIEW_THRESHOLD:
        return "Candidate Coverage - Review Recommended"
    return "Candidate Coverage - Mapping Review Required"




def infer_review_status(asil_level: str, match_score: float) -> str:
    score = float(match_score or 0)
    if score < MAPPING_REVIEW_THRESHOLD:
        return "MANUAL_REVIEW_REQUIRED"
    if score < READY_APPROVAL_THRESHOLD:
        return "REVIEW_RECOMMENDED"
    return "READY_FOR_APPROVAL"


def build_mapping_review_reason_codes(match_score: float, requirement_text: str = "", ai_rationale: str = "") -> list[str]:
    normalized_score = float(match_score or 0)
    searchable_text = f"{requirement_text} {ai_rationale}".lower()
    reason_codes: list[str] = []

    if normalized_score < MAPPING_REVIEW_THRESHOLD:
        reason_codes.append("LOW_MATCH_SCORE")
    if any(term in searchable_text for term in ["ambiguous", "unclear", "not clear", "uncertain"]):
        reason_codes.append("AMBIGUOUS_REQUIREMENT")
    if any(term in searchable_text for term in ["weak match", "weak", "limited overlap", "low overlap"]):
        reason_codes.append("WEAK_DOMAIN_ALIGNMENT")
    if any(term in searchable_text for term in ["missing expected response", "expected response missing", "no expected response"]):
        reason_codes.append("MISSING_EXPECTED_RESPONSE")
    if any(term in searchable_text for term in ["no strong historical", "no historical", "no reusable", "insufficient historical"]):
        reason_codes.append("NO_STRONG_HISTORICAL_TEST")

    return reason_codes


def describe_mapping_review_reason(reason_codes: list[str]) -> str:
    if not reason_codes:
        return "Requirement-to-test mapping score is sufficient for engineer approval."

    reason_labels = {
        "LOW_MATCH_SCORE": "low semantic match score",
        "AMBIGUOUS_REQUIREMENT": "ambiguous requirement wording",
        "WEAK_DOMAIN_ALIGNMENT": "weak domain alignment",
        "MISSING_EXPECTED_RESPONSE": "missing or unclear expected response",
        "NO_STRONG_HISTORICAL_TEST": "no strong reusable historical test evidence",
    }
    readable_reasons = [reason_labels.get(code, code.lower().replace("_", " ")) for code in reason_codes]
    return "Mapping review required because of " + ", ".join(readable_reasons) + "."


def infer_mapping_review_status(match_score: float, requirement_text: str = "", ai_rationale: str = "") -> dict[str, Any]:
    reason_codes = build_mapping_review_reason_codes(match_score, requirement_text, ai_rationale)
    if reason_codes:
        return {
            "mappingReviewStatus": "MAPPING_REVIEW_REQUIRED",
            "reviewStatus": "MANUAL_REVIEW_REQUIRED",
            "mappingReviewReason": describe_mapping_review_reason(reason_codes),
            "mappingReviewReasonCodes": reason_codes,
        }
    score = float(match_score or 0)
    review_status = "REVIEW_RECOMMENDED" if score < READY_APPROVAL_THRESHOLD else "READY_FOR_APPROVAL"
    mapping_status = "REVIEW_RECOMMENDED" if score < READY_APPROVAL_THRESHOLD else "READY_FOR_APPROVAL"
    reason = "Review recommended before approval because the mapping score is in the cautious approval range." if score < READY_APPROVAL_THRESHOLD else describe_mapping_review_reason([])
    return {
        "mappingReviewStatus": mapping_status,
        "reviewStatus": review_status,
        "mappingReviewReason": reason,
        "mappingReviewReasonCodes": [],
    }


def calculate_regression_risk_score(asil_level: str, match_score: float, duration_minutes: int, requirement_text: str = "") -> int:
    asil_weight = {"QM": 5, "A": 15, "B": 25, "C": 35, "D": 45}.get(str(asil_level).upper(), 10)
    match_quality_penalty = 25 if match_score < MAPPING_REVIEW_THRESHOLD else 15 if match_score < READY_APPROVAL_THRESHOLD else 5 if match_score < 0.85 else 0
    safety_priority_groups = detect_safety_priority_groups(requirement_text)
    safety_behavior_weight = min(20, len(safety_priority_groups) * 4)
    duration_weight = min(20, max(0, int(duration_minutes) // 180))
    review_gate_weight = 15 if infer_review_status(asil_level, match_score) == "MANUAL_REVIEW_REQUIRED" else 0
    return min(100, asil_weight + match_quality_penalty + safety_behavior_weight + duration_weight + review_gate_weight)


def build_regression_ranking_reason(asil_level: str, match_score: float, duration_minutes: int, requirement_text: str = "") -> str:
    reasons: list[str] = []
    asil = str(asil_level).upper()
    safety_priority_groups = sorted(detect_safety_priority_groups(requirement_text))

    if asil in {"C", "D"}:
        reasons.append(f"ASIL {asil} safety priority")
    elif asil in {"A", "B"}:
        reasons.append(f"ASIL {asil} verification priority")
    else:
        reasons.append("QM baseline verification priority")

    if safety_priority_groups:
        reasons.append("safety behavior indicators: " + ", ".join(safety_priority_groups[:3]))

    if match_score < MAPPING_REVIEW_THRESHOLD:
        reasons.append("low semantic match score requiring mapping review")
    elif match_score < READY_APPROVAL_THRESHOLD:
        reasons.append("cautious approval range requiring engineer attention")
    elif match_score < 0.85:
        reasons.append("moderate semantic match score")

    if duration_minutes >= 2880:
        reasons.append("long-duration execution effort affecting regression schedule")
    elif duration_minutes >= 360:
        reasons.append("medium-duration execution effort")

    if infer_review_status(asil_level, match_score) == "MANUAL_REVIEW_REQUIRED":
        reasons.append("mapping review required before evidence use")

    return "Prioritized because of " + ", ".join(reasons) + "."


def build_deterministic_priority_factor_scores(
    asil_level: str,
    match_score: float,
    duration_minutes: int,
    requirement_text: str = "",
) -> dict[str, float]:
    return {
        "asil": float({"QM": 5, "A": 15, "B": 25, "C": 35, "D": 45}.get(str(asil_level).upper(), 10)),
        "safety_behavior": float(min(20, len(detect_safety_priority_groups(requirement_text)) * 4)),
        "mapping_uncertainty": float(15 if match_score < MAPPING_REVIEW_THRESHOLD else 8 if match_score < READY_APPROVAL_THRESHOLD else 3 if match_score < 0.85 else 0),
        "duration": float(min(10, max(0, int(duration_minutes) // 360))),
        "review_dependency": float(10 if infer_review_status(asil_level, match_score) == "MANUAL_REVIEW_REQUIRED" else 0),
    }


def infer_mapping_uncertainty(match_score: float) -> str:
    if match_score < MAPPING_REVIEW_THRESHOLD:
        return "high"
    if match_score < 0.85:
        return "medium"
    return "low"


def apply_c2_prioritization(match: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(match)
    asil_level = str(enriched.get("asil_level", "QM"))
    match_score = float(enriched.get("final_match_score", enriched.get("match_score", 0)))
    duration_minutes = int(enriched.get("test_duration_minutes", 0))
    requirement_text = str(enriched.get("requirement_description", ""))
    deterministic_score = calculate_regression_risk_score(
        asil_level,
        match_score,
        duration_minutes,
        requirement_text,
    )
    deterministic_rationale = build_regression_ranking_reason(
        asil_level,
        match_score,
        duration_minutes,
        requirement_text,
    )
    deterministic_factor_scores = build_deterministic_priority_factor_scores(
        asil_level,
        match_score,
        duration_minutes,
        requirement_text,
    )
    review_status = str(enriched.get("review_status", "review_required"))
    priority_payload = {
        "test_case_id": enriched.get("matched_test_case_id"),
        "test_case_name": enriched.get("matched_test_case_name"),
        "test_type": enriched.get("test_type"),
        "linked_requirement": {
            "requirement_id": enriched.get("requirement_id"),
            "description": requirement_text,
            "asil_level": asil_level,
        },
        "match_score": match_score,
        "mapping_uncertainty": infer_mapping_uncertainty(match_score),
        "estimated_duration_minutes": duration_minutes,
        "safety_behavior_indicators": sorted(detect_safety_priority_groups(requirement_text)),
        "review_gate_dependency": review_status,
        "deterministic_risk_score": deterministic_score,
        "deterministic_factor_scores": deterministic_factor_scores,
    }
    c2_response = run_c2_prioritizer_ai(priority_payload)
    c2_metadata = c2_response.metadata.model_dump()
    ai_succeeded = bool(c2_metadata.get("ai_used")) and not bool(c2_metadata.get("fallback_used"))
    ai_priority_score = float(c2_response.ai_priority_score) if ai_succeeded else float(deterministic_score)
    final_priority_score = (
        round(0.65 * ai_priority_score + 0.35 * deterministic_score, 2)
        if ai_succeeded
        else float(deterministic_score)
    )
    priority_rationale = str(c2_response.rationale).strip() if ai_succeeded else deterministic_rationale

    enriched.update(
        {
            "deterministic_regression_risk_score": deterministic_score,
            "ai_priority_score": round(ai_priority_score, 3),
            "final_priority_score": final_priority_score,
            "priority_factor_scores": dict(c2_response.factor_scores) if ai_succeeded else deterministic_factor_scores,
            "priority_rationale": priority_rationale,
            "c2_ai_metadata": dict(c2_metadata),
            "regression_risk_score": final_priority_score,
            "regression_ranking_reason": priority_rationale,
        }
    )
    return enriched


def detect_boundary_clues(requirement_text: str) -> list[str]:
    text = requirement_text.lower()
    clues: list[str] = []

    clue_rules = [
        ("Timing constraint", ["within", "ms", "second", "delay", "latency", "timing", "timeout"]),
        ("Fault detection", ["fault", "failure", "invalid", "inconsistent", "implausible", "corruption"]),
        ("Diagnostic behavior", ["diagnostic", "dtc", "trouble code", "freeze-frame", "response"]),
        ("Fallback or degraded mode", ["fallback", "degraded", "limp-home", "safe state", "disable", "suppression"]),
        ("Threshold condition", ["threshold", "exceeds", "below", "above", "minimum", "maximum", "limit"]),
        ("Driver warning / HMI", ["alert", "warning", "display", "indicator", "telltale", "driver"]),
        ("Redundancy / plausibility", ["redundant", "plausibility", "cross-check", "mismatch"]),
        ("Communication loss", ["communication", "timeout", "signal loss", "unavailable", "message"]),
    ]

    for clue_name, keywords in clue_rules:
        if any(keyword in text for keyword in keywords):
            clues.append(clue_name)

    if not clues:
        clues.append("No explicit boundary clue detected; engineer review should confirm hidden conditions.")

    return clues


def decompose_requirement_clauses(requirement_id: str, requirement_text: str) -> list[dict[str, Any]]:
    text = clean_cell_text(requirement_text)
    if not text:
        return []

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


def build_ai_rationale(requirement_text: str, test_case_name: str, test_case_description: str, match_score: float) -> str:
    clues = detect_boundary_clues(requirement_text)
    main_clue = clues[0] if clues else "semantic similarity"
    match_score_label = "high" if match_score >= 0.85 else "moderate" if match_score >= 0.70 else "low"

    return (
            f"Matched with a {match_score_label} AI match score because the requirement and candidate test share engineering relevance around "
            f"{main_clue.lower()}, technical keyword overlap, domain relevance, and reusable verification intent. "
            f"The test case '{test_case_name}' was selected as a reusable verification candidate based on: {test_case_description}"
    )


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

# Helper for alternative candidate test cases for rejection recovery
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

        candidate_test_case = generate_candidate_test_case(requirement_id, requirement_text, asil_level, boundary_clues)
        manual_test_design_candidate = build_manual_test_design_candidate(requirement_id, requirement_text, asil_level)
        best_match_score = float(primary_matches.iloc[0]["match_score"]) if not primary_matches.empty else 0.0
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

def tokenize_for_matching(text: str) -> set[str]:
    normalized = re.sub(r"[^a-z0-9]+", " ", str(text).lower())
    tokens = {token for token in normalized.split() if len(token) >= 3 and token not in STOPWORDS}
    return tokens


def detect_keyword_groups(text: str) -> set[str]:
    lowered = str(text).lower()
    groups: set[str] = set()
    for group_name, keywords in TECHNICAL_KEYWORD_GROUPS.items():
        if any(keyword in lowered for keyword in keywords):
            groups.add(group_name)
    return groups


def detect_domain_codes(text: str) -> set[str]:
    lowered = str(text).lower()
    codes: set[str] = set()
    for domain_keyword, test_codes in DOMAIN_TO_TEST_CODES.items():
        if domain_keyword in lowered:
            codes.update(test_codes)
    return codes


def jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def calculate_hybrid_match_score(requirement_text: str, asil_level: str, test_case: pd.Series) -> float:
    test_description = str(test_case["description"])
    test_name = str(test_case["test_case_name"])
    test_case_id = str(test_case["test_case_id"])
    test_code = test_case_id.split("-")[1] if "-" in test_case_id else ""

    sequence_score = difflib.SequenceMatcher(None, requirement_text.lower(), test_description.lower()).ratio()

    requirement_tokens = tokenize_for_matching(requirement_text)
    test_tokens = tokenize_for_matching(f"{test_name} {test_description}")
    token_score = jaccard_similarity(requirement_tokens, test_tokens)

    requirement_groups = detect_keyword_groups(requirement_text)
    test_groups = detect_keyword_groups(test_description)
    group_score = jaccard_similarity(requirement_groups, test_groups)

    domain_codes = detect_domain_codes(requirement_text)
    domain_score = 1.0 if test_code in domain_codes else 0.35 if domain_codes else 0.5

    hybrid_score = (
        0.22 * sequence_score
        + 0.33 * token_score
        + 0.28 * group_score
        + 0.17 * domain_score
    )

    if group_score >= 0.50 or domain_score == 1.0:
        hybrid_score += 0.18
    if token_score >= 0.18:
        hybrid_score += 0.10

    return round(min(0.96, max(0.25, hybrid_score)), 2)


def detect_safety_priority_groups(requirement_text: str) -> set[str]:
    requirement_groups = detect_keyword_groups(requirement_text)
    return requirement_groups & {"fault", "fallback", "threshold", "sensor", "communication", "thermal", "electrical", "memory", "actuator"}


def load_reference_mappings() -> list[dict[str, Any]]:
    try:
        payload = json.loads(REFERENCE_MAPPINGS_PATH.read_text(encoding="utf-8"))
        reference_mappings = payload.get("reference_mappings", [])
        return reference_mappings if isinstance(reference_mappings, list) else []
    except (OSError, json.JSONDecodeError, TypeError):
        return []


def requires_external_hmi_validation(requirement_text: str) -> bool:
    normalized = str(requirement_text).lower()
    return any(term in normalized for term in EXTERNAL_HMI_VALIDATION_TERMS)


def normalize_c1_review_status(review_status: str, match_score: float) -> str:
    normalized = str(review_status or "").strip().lower()
    if normalized == "external_validation_required":
        return normalized
    if match_score < MIN_MAPPING_SELECTION_SCORE:
        return "weak_fallback"
    if match_score < MAPPING_REVIEW_THRESHOLD:
        return "review_required"
    if match_score < READY_APPROVAL_THRESHOLD and normalized == "ready":
        return "review_recommended"
    if normalized in {
        "ready",
        "review_recommended",
        "review_required",
        "weak_fallback",
        "external_validation_required",
    }:
        return normalized
    if match_score < READY_APPROVAL_THRESHOLD:
        return "review_recommended"
    return "ready"


def normalize_c1_coverage_type(coverage_type: str, match_score: float) -> str:
    normalized = str(coverage_type or "").strip().lower()
    if normalized in {"direct", "partial", "weak", "external_validation_required"}:
        return normalized
    if match_score >= 0.85:
        return "direct"
    if match_score >= MAPPING_REVIEW_THRESHOLD:
        return "partial"
    return "weak"


def mapping_review_fields_from_match(match: dict[str, Any]) -> dict[str, Any]:
    review_status = str(match.get("review_status", "")).strip().lower()
    reason_codes = [str(code) for code in match.get("reason_codes", [])]
    if review_status in {"review_required", "weak_fallback", "external_validation_required"}:
        mapping_status = "MAPPING_REVIEW_REQUIRED"
    elif review_status == "review_recommended":
        mapping_status = "REVIEW_RECOMMENDED"
    else:
        mapping_status = "READY_FOR_APPROVAL"

    if reason_codes:
        reason = "Mapping review context: " + ", ".join(code.lower().replace("_", " ") for code in reason_codes) + "."
    elif mapping_status == "READY_FOR_APPROVAL":
        reason = "Requirement-to-test mapping score is sufficient for engineer approval."
    else:
        reason = "Engineer review is required before this mapping is used as verification evidence."

    return {
        "mappingReviewStatus": mapping_status,
        "mappingReviewReason": reason,
        "mappingReviewReasonCodes": reason_codes,
        "reviewStatus": review_status or "review_required",
    }


def match_requirements(requirements: pd.DataFrame) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    reference_mappings = load_reference_mappings()

    for _, row in requirements.reset_index(drop=True).iterrows():
        requirement_description = str(row["description"]).strip()
        requirement_id = str(row["requirement_id"])
        asil_level = str(row["asil_level"])
        scored_matches: list[dict[str, Any]] = []

        for _, test_case in TEST_CASES.iterrows():
            rounded_score = calculate_hybrid_match_score(requirement_description, asil_level, test_case)
            rounded_score = round(float(rounded_score), 2)
            duration_minutes = int(test_case["duration_minutes"])
            scored_matches.append(
                {
                    "requirement_id": requirement_id,
                    "requirement_description": requirement_description,
                    "asil_level": asil_level,
                    "matched_test_case_id": str(test_case["test_case_id"]),
                    "matched_test_case_name": str(test_case["test_case_name"]),
                    "test_type": str(test_case["test_type"]),
                    "test_duration_minutes": duration_minutes,
                    "test_description": str(test_case["description"]),
                    "legacy_rule_score": rounded_score,
                }
            )

        scored_matches.sort(key=lambda item: item["legacy_rule_score"], reverse=True)
        candidate_pool = scored_matches[:20]
        candidate_tests = [
            {
                "test_case_id": item["matched_test_case_id"],
                "test_case_name": item["matched_test_case_name"],
                "test_type": item["test_type"],
                "description": item["test_description"],
                "duration_minutes": item["test_duration_minutes"],
                "semantic_or_candidate_score": item["legacy_rule_score"],
                "legacy_rule_score": item["legacy_rule_score"],
            }
            for item in candidate_pool
        ]
        legacy_rule_scores = [
            {
                "test_case_id": item["matched_test_case_id"],
                "legacy_rule_score": item["legacy_rule_score"],
                "semantic_or_candidate_score": item["legacy_rule_score"],
            }
            for item in candidate_pool
        ]
        c1_response = run_c1_matching_ai(
            requirement={
                "requirement_id": requirement_id,
                "description": requirement_description,
                "asil_level": asil_level,
            },
            candidate_tests=candidate_tests,
            reference_mappings=reference_mappings,
            legacy_rule_scores=legacy_rule_scores,
        )
        c1_metadata = c1_response.metadata.model_dump()
        ai_succeeded = bool(c1_metadata.get("ai_used")) and not bool(c1_metadata.get("fallback_used"))
        candidate_lookup = {item["matched_test_case_id"]: item for item in scored_matches}
        finalized_matches: list[dict[str, Any]] = []

        for selected in c1_response.selected_mappings:
            test_case_id = str(selected.get("test_case_id", ""))
            candidate = candidate_lookup.get(test_case_id)
            if candidate is None:
                continue

            legacy_rule_score = float(candidate["legacy_rule_score"])
            ai_match_score = float(selected.get("ai_match_score", legacy_rule_score)) if ai_succeeded else legacy_rule_score
            final_match_score = (
                round(0.70 * ai_match_score + 0.15 * legacy_rule_score + 0.15 * legacy_rule_score, 3)
                if ai_succeeded
                else legacy_rule_score
            )
            reason_codes = [str(code) for code in selected.get("reason_codes", [])]
            if c1_metadata.get("fallback_used") and "AI_FALLBACK_USED" not in reason_codes:
                reason_codes.append("AI_FALLBACK_USED")
            if final_match_score < MAPPING_REVIEW_THRESHOLD and "LOW_MATCH_SCORE" not in reason_codes:
                reason_codes.append("LOW_MATCH_SCORE")
            coverage_type = normalize_c1_coverage_type(str(selected.get("coverage_type", "")), final_match_score)
            review_status = normalize_c1_review_status(c1_response.review_status, final_match_score)
            ai_rationale = str(selected.get("rationale", "")).strip() if ai_succeeded else ""
            if not ai_rationale:
                ai_rationale = build_ai_rationale(
                    requirement_description,
                    candidate["matched_test_case_name"],
                    candidate["test_description"],
                    final_match_score,
                )

            if requires_external_hmi_validation(requirement_description):
                coverage_type = "external_validation_required"
                review_status = "external_validation_required"
                if "EXTERNAL_HMI_VALIDATION_REQUIRED" not in reason_codes:
                    reason_codes.append("EXTERNAL_HMI_VALIDATION_REQUIRED")
                ai_rationale += " Physical HMI, visual, or audio behavior requires external validation before evidence approval."

            finalized_matches.append(
                {
                    "requirement_id": requirement_id,
                    "requirement_description": requirement_description,
                    "asil_level": asil_level,
                    "matched_test_case_id": test_case_id,
                    "matched_test_case_name": candidate["matched_test_case_name"],
                    "test_type": candidate["test_type"],
                    "test_duration_minutes": candidate["test_duration_minutes"],
                    "match_score": final_match_score,
                    "ai_match_score": round(ai_match_score, 3),
                    "legacy_rule_score": legacy_rule_score,
                    "final_match_score": final_match_score,
                    "coverage_type": coverage_type,
                    "coverageType": coverage_type,
                    "review_status": review_status,
                    "reviewStatus": review_status,
                    "reason_codes": reason_codes,
                    "reasonCodes": reason_codes,
                    "ai_metadata": dict(c1_metadata),
                    "regression_risk_score": calculate_regression_risk_score(
                        asil_level, final_match_score, candidate["test_duration_minutes"], requirement_description
                    ),
                    "regression_ranking_reason": build_regression_ranking_reason(
                        asil_level, final_match_score, candidate["test_duration_minutes"], requirement_description
                    ),
                    "ai_rationale": ai_rationale,
                }
            )

        selected_matches = [
            match for match in finalized_matches
            if float(match.get("match_score", 0)) >= MIN_MAPPING_SELECTION_SCORE
        ]
        if not selected_matches and scored_matches:
            best = scored_matches[0]
            legacy_score = float(best["legacy_rule_score"])
            fallback_reason = "No C1-selected mapping met the minimum mapping threshold; best legacy candidate used."
            reason_codes = ["WEAK_FALLBACK"]
            coverage_type = "weak"
            review_status = "weak_fallback"
            if requires_external_hmi_validation(requirement_description):
                coverage_type = "external_validation_required"
                review_status = "external_validation_required"
                reason_codes.append("EXTERNAL_HMI_VALIDATION_REQUIRED")
            selected_matches = [
                {
                    "requirement_id": requirement_id,
                    "requirement_description": requirement_description,
                    "asil_level": asil_level,
                    "matched_test_case_id": best["matched_test_case_id"],
                    "matched_test_case_name": best["matched_test_case_name"],
                    "test_type": best["test_type"],
                    "test_duration_minutes": best["test_duration_minutes"],
                    "match_score": legacy_score,
                    "ai_match_score": legacy_score,
                    "legacy_rule_score": legacy_score,
                    "final_match_score": legacy_score,
                    "coverage_type": coverage_type,
                    "coverageType": coverage_type,
                    "review_status": review_status,
                    "reviewStatus": review_status,
                    "reason_codes": reason_codes,
                    "reasonCodes": reason_codes,
                    "ai_metadata": {
                        "ai_used": False,
                        "model_name": c1_metadata.get("model_name"),
                        "fallback_used": True,
                        "fallback_reason": fallback_reason,
                    },
                    "regression_risk_score": calculate_regression_risk_score(
                        asil_level, legacy_score, best["test_duration_minutes"], requirement_description
                    ),
                    "regression_ranking_reason": build_regression_ranking_reason(
                        asil_level, legacy_score, best["test_duration_minutes"], requirement_description
                    ),
                    "ai_rationale": build_ai_rationale(
                        requirement_description,
                        best["matched_test_case_name"],
                        best["test_description"],
                        legacy_score,
                    ),
                }
            ]

        results.extend(apply_c2_prioritization(match) for match in selected_matches[:3])

    return results


def make_summary(matches: list[dict[str, Any]], requirement_count: int) -> dict[str, Any]:
    match_df = pd.DataFrame(matches)
    unique_tests = match_df.drop_duplicates(subset=["matched_test_case_id"]).copy()
    asil_order = {"QM": 0, "A": 1, "B": 2, "C": 3, "D": 4}
    asil_display_order = ["QM", "A", "B", "C", "D"]
    highest_asil = "N/A"

    if "asil_level" in match_df.columns and not match_df["asil_level"].empty:
        highest_asil = max(
            match_df["asil_level"].fillna("N/A").astype(str),
            key=lambda value: asil_order.get(value.upper(), -1),
        )

    requirement_best_matches = (
        match_df.sort_values("match_score", ascending=False)
        .drop_duplicates(subset=["requirement_id"], keep="first")
        .copy()
    )
    requirement_level_df = requirement_best_matches.copy()
    requirement_level_df["asil_level"] = requirement_level_df["asil_level"].fillna("N/A").astype(str).str.upper()
    match_df["asil_level"] = match_df["asil_level"].fillna("N/A").astype(str).str.upper()

    requirement_counts_by_asil = (
        requirement_level_df.groupby("asil_level")
        .size()
        .reindex(asil_display_order, fill_value=0)
        .reset_index(name="count")
        .rename(columns={"asil_level": "asilLevel"})
        .to_dict(orient="records")
    )

    test_type_counts = (
        unique_tests.groupby("test_type")
        .size()
        .reset_index(name="count")
        .rename(columns={"test_type": "testType"})
        .to_dict(orient="records")
    )

    coverage_rows: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    time_rows: list[dict[str, Any]] = []

    for asil_level in asil_display_order:
        asil_requirements = requirement_level_df[requirement_level_df["asil_level"] == asil_level]
        asil_matches = match_df[match_df["asil_level"] == asil_level]
        asil_best_matches = requirement_best_matches[requirement_best_matches["asil_level"] == asil_level]
        asil_unique_tests = asil_matches.drop_duplicates(subset=["matched_test_case_id"])
        covered_count = int(asil_matches["requirement_id"].nunique()) if not asil_matches.empty else 0
        requirement_total = int(len(asil_requirements))
        review_count = int(
            asil_best_matches.loc[asil_best_matches["match_score"] < MAPPING_REVIEW_THRESHOLD, "requirement_id"].nunique()
        ) if not asil_best_matches.empty else 0
        coverage_rate = round((covered_count / requirement_total) * 100, 1) if requirement_total else 0

        coverage_rows.append(
            {
                "asilLevel": asil_level,
                "requirements": requirement_total,
                "covered": covered_count,
                "coverageRate": coverage_rate,
            }
        )
        review_rows.append({"asilLevel": asil_level, "reviewNeeded": review_count})
        time_rows.append(
            {
                "asilLevel": asil_level,
                "estimatedMinutes": int(asil_unique_tests["test_duration_minutes"].sum())
                if not asil_unique_tests.empty
                else 0,
            }
        )

    requirement_match_scores = requirement_best_matches["match_score"]
    confidence_distribution = [
        {
            "label": "High Confidence",
            "range": "0.85-1.00",
            "count": int((requirement_match_scores >= 0.85).sum()),
            "status": "good",
        },
        {
            "label": "Acceptable",
            "range": "0.70-0.84",
            "count": int(((requirement_match_scores >= READY_APPROVAL_THRESHOLD) & (requirement_match_scores < 0.85)).sum()),
            "status": "normal",
        },
        {
            "label": "Review Recommended",
            "range": "0.65-0.69",
            "count": int(((requirement_match_scores >= MAPPING_REVIEW_THRESHOLD) & (requirement_match_scores < READY_APPROVAL_THRESHOLD)).sum()),
            "status": "warning",
        },
        {
            "label": "Mapping Review Required",
            "range": "0.55-0.64",
            "count": int(((requirement_match_scores >= MIN_MAPPING_SELECTION_SCORE) & (requirement_match_scores < MAPPING_REVIEW_THRESHOLD)).sum()),
            "status": "danger",
        },
        {
            "label": "Weak Fallback Only",
            "range": "Below 0.55",
            "count": int((requirement_match_scores < MIN_MAPPING_SELECTION_SCORE).sum()),
            "status": "danger",
        },
    ]

    # (Old duplicate requirement_best_matches block removed)
    review_items_df = requirement_best_matches[
        requirement_best_matches["match_score"] < MAPPING_REVIEW_THRESHOLD
    ].head(12)

    review_items = [
        {
            "requirementId": str(row["requirement_id"]),
            "asilLevel": str(row["asil_level"]),
            "matchedTestCaseId": str(row["matched_test_case_id"]),
            "matchedTestCaseName": str(row["matched_test_case_name"]),
            "confidence": float(row["match_score"]),
            "mappingReviewReasonCodes": build_mapping_review_reason_codes(
                float(row["match_score"]),
                str(row.get("requirement_description", "")),
                str(row.get("ai_rationale", "")),
            ),
            "action": "Mapping Review Required",
        }
        for _, row in review_items_df.iterrows()
    ]

    longest_tests = (
        unique_tests.sort_values("test_duration_minutes", ascending=False)
        .head(10)[
            ["matched_test_case_id", "matched_test_case_name", "test_type", "test_duration_minutes"]
        ]
        .rename(
            columns={
                "matched_test_case_id": "testCaseId",
                "matched_test_case_name": "testCaseName",
                "test_type": "testType",
                "test_duration_minutes": "durationMinutes",
            }
        )
        .to_dict(orient="records")
    )

    top_reused_tests = (
        match_df.groupby(["matched_test_case_id", "matched_test_case_name", "test_type"])
        .size()
        .reset_index(name="mappedRequirements")
        .sort_values("mappedRequirements", ascending=False)
        .head(10)
        .rename(
            columns={
                "matched_test_case_id": "testCaseId",
                "matched_test_case_name": "testCaseName",
                "test_type": "testType",
            }
        )
        .to_dict(orient="records")
    )

    total_mappings = int(len(match_df))
    low_confidence_count = int((match_df["match_score"] < MAPPING_REVIEW_THRESHOLD).sum())
    review_needed_requirements = int(
        requirement_best_matches.loc[
            requirement_best_matches["match_score"] < MAPPING_REVIEW_THRESHOLD,
            "requirement_id",
        ].nunique()
    )
    high_risk_requirement_count = int(requirement_level_df["asil_level"].isin(["C", "D"]).sum())
    high_risk_review_count = int(
        match_df.loc[
            (match_df["asil_level"].isin(["C", "D"])) & (match_df["match_score"] < 0.70),
            "requirement_id",
        ].nunique()
    )
    total_test_time_minutes = int(unique_tests["test_duration_minutes"].sum())
    average_match_score = round(float(match_df["match_score"].mean()), 3) if total_mappings else 0
    coverage_rate = round((match_df["requirement_id"].nunique() / requirement_count) * 100, 1) if requirement_count else 0
    test_reuse_ratio = round(total_mappings / len(unique_tests), 2) if len(unique_tests) else 0
    average_tests_per_requirement = round(total_mappings / requirement_count, 2) if requirement_count else 0

    executive_summary = (
        f"The uploaded requirement set contains {requirement_count} software safety requirements. "
        f"{coverage_rate}% are currently linked to candidate test coverage across {len(unique_tests)} unique test cases. "
        f"Average AI match score is {round(average_match_score * 100, 1)}%, with "
        f"{review_needed_requirements} requirements requiring engineer review. "
        f"ASIL {highest_asil} is the highest observed safety level, and estimated unique test execution time is "
        f"{round(total_test_time_minutes / 60, 1)} hours."
    )

    return {
        "requirementsUploaded": requirement_count,
        "requirementTestMappings": total_mappings,
        "uniqueTestCases": len(unique_tests),
        "totalTestTimeMinutes": total_test_time_minutes,
        "highestAsilLevel": highest_asil,
        "coverageRate": coverage_rate,
        "averageConfidence": average_match_score,
        "averageMatchScore": average_match_score,
        "lowConfidenceCount": low_confidence_count,
        "reviewNeededRequirements": review_needed_requirements,
        "reviewNeeded": review_needed_requirements,
        "reviewNeededCount": review_needed_requirements,
        "lowConfidenceRequirementCount": review_needed_requirements,
        "highRiskRequirementCount": high_risk_requirement_count,
        "highRiskReviewCount": high_risk_review_count,
        "testReuseRatio": test_reuse_ratio,
        "averageTestsPerRequirement": average_tests_per_requirement,
        "requirementsFullyCovered": int(match_df["requirement_id"].nunique()),
        "uncoveredRequirements": int(max(requirement_count - match_df["requirement_id"].nunique(), 0)),
        "executiveSummary": executive_summary,
        "asilCounts": requirement_counts_by_asil,
        "requirementCountsByAsil": requirement_counts_by_asil,
        "testTypeCounts": test_type_counts,
        "coverageByAsil": coverage_rows,
        "reviewNeededByAsil": review_rows,
        "estimatedTestTimeByAsil": time_rows,
        "confidenceDistribution": confidence_distribution,
        "reviewItems": review_items,
        "longestTests": longest_tests,
        "topReusedTests": top_reused_tests,
    }


class ReviewDecision(BaseModel):
    testCaseId: str
    decision: str
    evidenceFileName: str | None = None
    reviewNote: str | None = None


class ReportRequest(BaseModel):
    matches: list[dict[str, Any]]
    decisions: list[ReviewDecision]
    candidate1Decisions: dict[str, str] = {}
    candidate1ReviewNotes: dict[str, str] = {}
    candidate1RecoveryRecords: dict[str, dict[str, Any]] = {}
    traceabilityMatrix: list[dict[str, Any]] = []
    simulationResults: list[dict[str, Any]] = []


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
