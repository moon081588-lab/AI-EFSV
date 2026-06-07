"""Optional AI service adapters for the AI-EFSV backend.

These services are intentionally not wired into the existing API business
flows yet. Callers can opt in after validating provider configuration and
response quality.
"""

from .anomaly_ai import run_c3_anomaly_ai
from .matching_ai import run_c1_matching_ai
from .prioritizer_ai import run_c2_prioritizer_ai
from .report_ai import run_c3_report_drafter_ai

__all__ = [
    "run_c1_matching_ai",
    "run_c2_prioritizer_ai",
    "run_c3_anomaly_ai",
    "run_c3_report_drafter_ai",
]
