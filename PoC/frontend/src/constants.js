export const API_BASE = '/api';

export const ASIL_COLORS = {
  QM: '#64748b',
  A: '#2563eb',
  B: '#16a34a',
  C: '#f97316',
  D: '#dc2626',
};

export const STATUS_COLORS = {
  good: '#16a34a',
  normal: '#2563eb',
  warning: '#f97316',
  danger: '#dc2626',
};

export const TEST_TYPE_COLORS = ['#2563eb', '#7c3aed', '#16a34a', '#f97316', '#dc2626', '#0f766e', '#4f46e5'];

export const DASHBOARD_INFO = {
  dashboard: 'This dashboard summarizes uploaded requirements, AI-generated traceability mappings, estimated verification effort, match-score quality, ASIL distribution, and mapping-review workload. It is a decision-support view for engineer review, not final safety evidence by itself.',
  totalRequirements: 'Total Requirements is the number of normalized software safety requirements extracted from the uploaded file after parser cleanup. If requirement IDs are missing, the backend parser may generate them automatically.',
  uniqueTestCases: 'Unique Test Cases counts distinct reusable or generated test cases selected by the matching algorithm. Multiple requirements may map to the same test case, so this is usually smaller than the total number of mappings.',
  coverageRate: 'Coverage Rate is the percentage of uploaded requirements that have at least one candidate test case mapping. It means candidate coverage, not final validated ISO 26262 coverage.',
  averageConfidence: 'Average Match Score is the mean AI-generated requirement-to-test matching score. It is a heuristic relevance score based on text similarity, technical keyword overlap, domain relevance, and constraint overlap; it should not be interpreted as calibrated probability.',
  reviewNeeded: 'Mapping Review Queue counts requirement-to-test mappings classified by the backend as low-confidence or ambiguous. These mappings require engineer review before they are trusted for downstream planning, simulation, or report evidence.',
  estimatedTestTime: 'Estimated Test Time sums the unique selected test-case execution durations. It supports regression scheduling and planning, but it is not a guaranteed physical bench execution time.',
  highRiskRequirements: 'High-Risk Requirements counts ASIL C and ASIL D requirements. These are highlighted because higher ASIL levels require stronger traceability, review discipline, and evidence quality.',
  testReuseRatio: 'Test Reuse Ratio shows how many requirement mappings are supported per unique test case. A higher ratio suggests reusable verification assets, but excessive reuse still requires validation to avoid weak evidence.',
  asilCharts: 'ASIL-Based Verification Charts group metrics by safety criticality: requirement count, coverage rate, estimated effort, and review burden. This helps identify whether high-ASIL items are adequately covered and reviewed.',
  portfolioCharts: 'Test Portfolio & Match Score Charts explain selected test-case composition and AI match-score quality. They support test planning and review prioritization.',
  riskQueue: 'Risk / Review Queue lists mappings that require manual review. Engineers should check these items before report drafting or final approval.',
  testPortfolio: 'Test Portfolio shows the longest selected test cases to support execution planning, schedule estimation, and regression prioritization.',
  regressionOptimizer: 'AI Regression Optimizer ranks unique test cases for execution planning. It uses regression risk score, ASIL relevance, average match confidence, mapped requirement count, and estimated test duration to help engineers decide what to execute first.',
  candidate1Workspace: 'AI Requirement Extraction & Test Case Derivation shows extracted requirement text, detected boundary clues, recommended historical tests, and AI-generated candidate test cases. Engineers must approve, reject, revise, or explain each candidate before treating it as useful verification evidence.',
  traceabilityMatrix: 'Traceability Matrix links requirements to candidate test cases with ASIL level, coverage type, AI match score, rationale, and mapping-review status. It is the core evidence map for showing how requirements are connected to verification activities.',
  auditLog: 'Audit Log records system actions such as upload handling, parser detection, requirement normalization, AI matching, and review-gate assignment. It supports reviewability and accountability in the POC workflow.',
  exportCenter: 'Export Center downloads evidence artifacts such as the traceability matrix and audit log. These exports are intended for review, presentation, or documentation support.',
  verificationSimulation: 'Verification Simulation runs a proof-of-concept execution pass over the matched test cases. It simulates protocol traces, pass/review outcomes, and anomaly candidates rather than communicating with a real ECU bench.',
  simulatedResults: 'Simulated Test Results summarize execution outcomes after verification simulation. PASS means the simulated result stayed within the expected range, while REVIEW means engineer confirmation is required.',
  anomalyReview: 'AI Anomaly Detection Review shows only simulated results that require engineer attention. It classifies anomaly type, confidence, observed behavior, AI explanation, and expected engineer follow-up.',
  engineerReview: 'Engineer Review Confirmation is the human decision gate. The report draft button stays disabled until all review-needed cases have been accepted or rejected by the engineer.',
  draftReport: 'Draft ISO 26262 Compliance Report presents generated report text based on traceability mappings, simulation outputs, anomaly review, and engineer decisions. It remains draft evidence until final approval.',
};
