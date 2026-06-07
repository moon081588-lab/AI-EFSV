from __future__ import annotations

from typing import Any

from pydantic import BaseModel


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
