"""Shared response contracts for optional AI services."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AIMetadata(BaseModel):
    ai_used: bool = False
    model_name: str | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None


class C1MatchingResponse(BaseModel):
    selected_mappings: list[dict[str, Any]] = Field(default_factory=list)
    review_status: str = "MANUAL_REVIEW_REQUIRED"
    metadata: AIMetadata


class C2PrioritizationResponse(BaseModel):
    ai_priority_score: float = 0.0
    factor_scores: dict[str, float] = Field(default_factory=dict)
    rationale: str = ""
    metadata: AIMetadata


class C3AnomalyResponse(BaseModel):
    verdict: Literal["PASS", "REVIEW"] = "REVIEW"
    anomaly_type: str = "AI service unavailable"
    confidence: float = 0.0
    observed_behavior: str = ""
    explanation: str = ""
    recommended_engineer_action: str = "Perform manual engineer review."
    metadata: AIMetadata


class C3ReportDraftResponse(BaseModel):
    scope_summary: str = ""
    safety_context: str = ""
    traceability_evidence: str = ""
    test_portfolio_summary: str = ""
    anomaly_review_summary: str = ""
    engineer_decision_summary: str = ""
    limitations: str = ""
    approval_gate_statement: str = ""
    metadata: AIMetadata


class LLMClientResult(BaseModel):
    data: dict[str, Any] | None = None
    metadata: AIMetadata
