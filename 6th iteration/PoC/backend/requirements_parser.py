from __future__ import annotations

import io
import re
from typing import Any

import pandas as pd

from config import (
    ASIL_COLUMN_CANDIDATES,
    ID_COLUMN_CANDIDATES,
    REQUIREMENT_COLUMN_CANDIDATES,
    REQUIREMENT_KEYWORD_PATTERN,
)


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
