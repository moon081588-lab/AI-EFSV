import React from 'react';
import { createRoot } from 'react-dom/client';
import { Upload, Play, FileText, CheckCircle, XCircle, HelpCircle } from 'lucide-react';
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from 'recharts';
import './styles.css';

const API_BASE = '/api';

const ASIL_COLORS = {
  QM: '#64748b',
  A: '#2563eb',
  B: '#16a34a',
  C: '#f97316',
  D: '#dc2626',
};

const STATUS_COLORS = {
  good: '#16a34a',
  normal: '#2563eb',
  warning: '#f97316',
  danger: '#dc2626',
};


const TEST_TYPE_COLORS = ['#2563eb', '#7c3aed', '#16a34a', '#f97316', '#dc2626', '#0f766e', '#4f46e5'];

const DASHBOARD_INFO = {
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

const formatPercent = (value) => `${Number(value ?? 0).toFixed(1)}%`;
const formatConfidence = (value) => `${(Number(value ?? 0) * 100).toFixed(1)}%`;
const formatHours = (minutes) => `${(Number(minutes ?? 0) / 60).toFixed(1)} h`;

const ASIL_ORDER = ['QM', 'A', 'B', 'C', 'D'];

const getRequirementIdFromRow = (row) => (
  row?.requirement_id ??
  row?.requirementId ??
  row?.RequirementID ??
  row?.requirementID ??
  row?.requirement_id_raw ??
  row?.requirementIdRaw
);

const getTestCaseIdFromRow = (row) => (
  row?.matched_test_case_id ??
  row?.testCaseId ??
  row?.test_case_id ??
  row?.matchedTestCaseId
);

const getAsilFromRow = (row) => String(row?.asil_level ?? row?.asilLevel ?? 'QM').toUpperCase();
const getMatchScoreFromRow = (row) => Number(row?.match_score ?? row?.confidence ?? row?.final_match_score ?? 0);
const getTestDurationFromRow = (row) => Number(row?.test_duration_minutes ?? row?.durationMinutes ?? row?.estimatedDurationMinutes ?? 0);
const getCoverageTypeFromRow = (row) => String(row?.coverage_type ?? row?.coverageType ?? '').toLowerCase();

const isMappingReviewRequiredRow = (row) => {
  const reviewStatus = String(row?.reviewStatus ?? row?.review_status ?? '').toUpperCase();
  const mappingReviewStatus = String(row?.mappingReviewStatus ?? row?.mapping_review_status ?? '').toUpperCase();
  return (
    reviewStatus === 'MANUAL_REVIEW_REQUIRED' ||
    reviewStatus === 'REVIEW_REQUIRED' ||
    reviewStatus === 'WEAK_FALLBACK' ||
    reviewStatus === 'EXTERNAL_VALIDATION_REQUIRED' ||
    mappingReviewStatus === 'MAPPING_REVIEW_REQUIRED'
  );
};

function normalizeSummary(rawSummary = {}, activeSummary = {}, activeMatches = [], activeReviewItems = []) {
  const requirementIds = new Set(activeMatches.map(getRequirementIdFromRow).filter(Boolean));
  const uniqueTests = new Map();
  activeMatches.forEach((row) => {
    const testCaseId = getTestCaseIdFromRow(row);
    if (testCaseId && !uniqueTests.has(testCaseId)) uniqueTests.set(testCaseId, row);
  });

  const rawRequirementsUploaded = Number(
    activeSummary.requirementsUploaded ??
    rawSummary.requirementsUploaded ??
    rawSummary.totalRequirements ??
    rawSummary.requirementCount ??
    requirementIds.size
  );
  const totalRequirements = Number(activeSummary.totalRequirements ?? activeSummary.requirementCount ?? requirementIds.size);
  const mappingCount = Number(activeSummary.mappingCount ?? activeSummary.requirementTestMappings ?? activeMatches.length);
  const uniqueTestCases = Number(activeSummary.uniqueTestCases ?? activeSummary.uniqueTestCaseCount ?? uniqueTests.size);
  const totalTestTimeMinutes = Number(
    activeSummary.totalTestTimeMinutes ??
    activeSummary.estimatedTestTimeMinutes ??
    activeSummary.totalEstimatedTestTimeMinutes ??
    Array.from(uniqueTests.values()).reduce((sum, row) => sum + getTestDurationFromRow(row), 0)
  );
  const reviewRequirementIds = new Set(activeReviewItems.map(getRequirementIdFromRow).filter(Boolean));
  const reviewNeeded = Number(
    activeSummary.reviewNeeded ??
    activeSummary.reviewNeededCount ??
    activeSummary.reviewNeededRequirements ??
    reviewRequirementIds.size
  );
  const averageConfidence = Number(
    activeSummary.averageConfidence ??
    activeSummary.avgMatchScore ??
    (activeMatches.length
      ? activeMatches.reduce((sum, row) => sum + getMatchScoreFromRow(row), 0) / activeMatches.length
      : 0)
  );

  const requirementAsil = new Map();
  activeMatches.forEach((row) => {
    const requirementId = getRequirementIdFromRow(row);
    if (requirementId) requirementAsil.set(requirementId, getAsilFromRow(row));
  });
  const requirementCountsByAsil = ASIL_ORDER.map((asilLevel) => ({
    asilLevel,
    count: Array.from(requirementAsil.values()).filter((level) => level === asilLevel).length,
  }));
  const reviewNeededByAsil = ASIL_ORDER.map((asilLevel) => ({
    asilLevel,
    reviewNeeded: new Set(
      activeReviewItems.filter((row) => getAsilFromRow(row) === asilLevel).map(getRequirementIdFromRow).filter(Boolean)
    ).size,
  }));
  const coverageByAsil = requirementCountsByAsil.map(({ asilLevel, count }) => {
    const rawCount = Number((rawSummary.requirementCountsByAsil ?? rawSummary.asilCounts ?? [])
      .find((item) => item.asilLevel === asilLevel)?.count ?? count);
    return {
      asilLevel,
      requirements: rawCount,
      covered: count,
      coverageRate: rawCount > 0 ? Math.round((count / rawCount) * 1000) / 10 : 0,
    };
  });
  const estimatedTestTimeByAsil = ASIL_ORDER.map((asilLevel) => ({
    asilLevel,
    estimatedMinutes: Array.from(uniqueTests.values())
      .filter((row) => getAsilFromRow(row) === asilLevel)
      .reduce((sum, row) => sum + getTestDurationFromRow(row), 0),
  }));
  const testTypeCounts = Array.from(uniqueTests.values()).reduce((counts, row) => {
    const testType = String(row?.test_type ?? row?.testType ?? 'Unknown');
    const existing = counts.find((item) => item.testType === testType);
    if (existing) existing.count += 1;
    else counts.push({ testType, count: 1 });
    return counts;
  }, []);
  const confidenceDistribution = [
    { label: 'High (>= 0.80)', status: 'good', count: activeMatches.filter((row) => getMatchScoreFromRow(row) >= 0.8).length },
    { label: 'Medium (0.65-0.79)', status: 'warning', count: activeMatches.filter((row) => getMatchScoreFromRow(row) >= 0.65 && getMatchScoreFromRow(row) < 0.8).length },
    { label: 'Low (< 0.65)', status: 'danger', count: activeMatches.filter((row) => getMatchScoreFromRow(row) < 0.65).length },
  ];
  const reviewItems = activeReviewItems.map((row) => ({
    requirementId: getRequirementIdFromRow(row),
    asilLevel: getAsilFromRow(row),
    matchedTestCaseId: getTestCaseIdFromRow(row),
    matchedTestCaseName: row?.matched_test_case_name ?? row?.testCaseName ?? row?.generatedCandidateTestCase?.testCaseName ?? 'Pending verification evidence',
    confidence: getMatchScoreFromRow(row),
    action: getCoverageTypeFromRow(row) === 'external_validation_required' ? 'External Validation' : 'Manual Review',
  }));
  const longestTests = Array.from(uniqueTests.values())
    .map((row) => ({
      testCaseId: getTestCaseIdFromRow(row),
      testCaseName: row?.matched_test_case_name ?? row?.testCaseName ?? 'Unnamed test case',
      testType: row?.test_type ?? row?.testType ?? 'Unknown',
      durationMinutes: getTestDurationFromRow(row),
    }))
    .sort((a, b) => b.durationMinutes - a.durationMinutes)
    .slice(0, 10);
  const highRiskRequirementCount = new Set(
    activeMatches.filter((row) => ['C', 'D'].includes(getAsilFromRow(row))).map(getRequirementIdFromRow).filter(Boolean)
  ).size;
  const coverageRate = Number(
    activeSummary.coverageRate ??
    (rawRequirementsUploaded > 0 ? Math.round((totalRequirements / rawRequirementsUploaded) * 1000) / 10 : 0)
  );
  const testReuseRatio = Number(
    activeSummary.testReuseRatio ??
    (uniqueTestCases > 0 ? Math.round((mappingCount / uniqueTestCases) * 100) / 100 : 0)
  );
  const highestAsilLevel = [...ASIL_ORDER].reverse().find((level) => requirementCountsByAsil.find((row) => row.asilLevel === level)?.count > 0) ?? 'N/A';
  const executiveSummary = (
    `${totalRequirements} of ${rawRequirementsUploaded} uploaded requirements are currently eligible for active evidence, ` +
    `using ${uniqueTestCases} unique test cases and ${mappingCount} active mappings. ` +
    `${reviewNeeded} requirement(s) remain visible in the review queue.`
  );

  return {
    ...rawSummary,
    ...activeSummary,
    rawRequirementsUploaded,
    requirementsUploaded: totalRequirements,
    totalRequirements,
    requirementCount: totalRequirements,
    requirementTestMappings: mappingCount,
    mappingCount,
    uniqueTestCases,
    uniqueTestCaseCount: uniqueTestCases,
    totalTestTimeMinutes,
    estimatedTestTimeMinutes: totalTestTimeMinutes,
    totalEstimatedTestTimeMinutes: totalTestTimeMinutes,
    reviewNeededRequirements: reviewNeeded,
    reviewNeeded,
    reviewNeededCount: reviewNeeded,
    highRiskRequirementCount,
    highRiskRequirements: highRiskRequirementCount,
    averageConfidence,
    avgMatchScore: averageConfidence,
    averageMatchScore: averageConfidence,
    coverageRate,
    testReuseRatio,
    highestAsilLevel,
    requirementCountsByAsil,
    asilCounts: requirementCountsByAsil,
    testTypeCounts,
    coverageByAsil,
    estimatedTestTimeByAsil,
    reviewNeededByAsil,
    confidenceDistribution,
    reviewItems,
    longestTests,
    requirementsFullyCovered: totalRequirements,
    uncoveredRequirements: Math.max(rawRequirementsUploaded - totalRequirements, 0),
    executiveSummary,
  };
}

const MAPPING_REVIEW_REASON_LABELS = {
  LOW_MATCH_SCORE: 'Low match score',
  AMBIGUOUS_REQUIREMENT: 'Ambiguous requirement',
  WEAK_DOMAIN_ALIGNMENT: 'Weak domain alignment',
  MISSING_EXPECTED_RESPONSE: 'Missing expected response',
  NO_STRONG_HISTORICAL_TEST: 'No strong historical test',
};

const formatMappingReviewReasonCode = (code) => (
  MAPPING_REVIEW_REASON_LABELS[code] || String(code || '').replaceAll('_', ' ').toLowerCase()
);

const asilColorClass = (asilLevel) => {
  const level = String(asilLevel || '').toUpperCase();
  if (level === 'D') return 'asil-d';
  if (level === 'C') return 'asil-c';
  if (level === 'B') return 'asil-b';
  if (level === 'A') return 'asil-a';
  return 'asil-qm';
};

function App() {
  const [selectedFile, setSelectedFile] = React.useState(null);
  const [isDragging, setIsDragging] = React.useState(false);
  const [uploadStage, setUploadStage] = React.useState('idle');
  const [uploadProgress, setUploadProgress] = React.useState(0);
  const [uploadElapsedSeconds, setUploadElapsedSeconds] = React.useState(0);
  const [analysis, setAnalysis] = React.useState(null);
  const [uploadError, setUploadError] = React.useState('');
  const [uploadNotice, setUploadNotice] = React.useState('');

  const [testStage, setTestStage] = React.useState('idle');
  const [testProgress, setTestProgress] = React.useState(0);
  const [testResults, setTestResults] = React.useState(null);
  const [testError, setTestError] = React.useState('');
  const [executionLogs, setExecutionLogs] = React.useState([]);
  const [liveAuditEvents, setLiveAuditEvents] = React.useState([]);

  const [reviewDecisions, setReviewDecisions] = React.useState({});
  const [reviewEvidenceFiles, setReviewEvidenceFiles] = React.useState({});
  const [candidate1Decisions, setCandidate1Decisions] = React.useState({});
  const [candidate1ReviewNotes, setCandidate1ReviewNotes] = React.useState({});
  const [candidate1RecoveryRecords, setCandidate1RecoveryRecords] = React.useState({});
  const [report, setReport] = React.useState(null);
  const [reportError, setReportError] = React.useState('');
  const [reportStage, setReportStage] = React.useState('idle');
  const [reportProgress, setReportProgress] = React.useState(0);
  const [reportApprovalStatus, setReportApprovalStatus] = React.useState('Pending Safety Engineer Review');
  const [finalReportRevisionNote, setFinalReportRevisionNote] = React.useState('');
  const [optimizerSortMode, setOptimizerSortMode] = React.useState('risk');
  const [reviewNotes, setReviewNotes] = React.useState({});

  const uploadTimerRef = React.useRef(null);
  const uploadAbortControllerRef = React.useRef(null);
  const dragCounterRef = React.useRef(0);
  const testTimerRef = React.useRef(null);
  const reportTimerRef = React.useRef(null);

  function appendAuditEvent(eventType, actor, relatedItem, details) {
    const now = new Date();
    const timestamp = now.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });

    setLiveAuditEvents((current) => [
      ...current,
      {
        eventId: `LIVE-${String(current.length + 1).padStart(3, '0')}`,
        eventType,
        actor,
        relatedItem,
        details: `[${timestamp}] ${details}`,
        timestamp: now.toISOString(),
        isLive: true,
      },
    ]);
  }

  React.useEffect(() => {
    return () => {
      if (uploadTimerRef.current) clearInterval(uploadTimerRef.current);
      if (uploadAbortControllerRef.current) uploadAbortControllerRef.current.abort();
      if (testTimerRef.current) clearInterval(testTimerRef.current);
      if (reportTimerRef.current) clearInterval(reportTimerRef.current);
    };
  }, []);

  function validateAndUpload(files) {
    const fileList = Array.from(files || []);
    setUploadError('');
    setUploadNotice('');

    if (fileList.length !== 1) {
      setUploadError('Please upload exactly one requirements file.');
      return;
    }

    const file = fileList[0];
    const extension = file.name.includes('.') ? `.${file.name.split('.').pop().toLowerCase()}` : '';
    if (!['.csv', '.xlsx', '.xls'].includes(extension)) {
      setUploadError('Unsupported file format. Please upload a CSV, XLSX, or XLS file.');
      return;
    }

    handleUpload(file);
  }

  function handleDragEnter(event) {
    event.preventDefault();
    event.stopPropagation();
    dragCounterRef.current += 1;
    setIsDragging(true);
  }

  function handleDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    event.dataTransfer.dropEffect = 'copy';
    setIsDragging(true);
  }

  function handleDragLeave(event) {
    event.preventDefault();
    event.stopPropagation();
    dragCounterRef.current = Math.max(0, dragCounterRef.current - 1);
    if (dragCounterRef.current === 0) setIsDragging(false);
  }

  function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    dragCounterRef.current = 0;
    setIsDragging(false);

    if (uploadStage === 'analyzing' || uploadStage === 'rendering') {
      setUploadError('An analysis is already in progress. Cancel it before uploading another file.');
      return;
    }

    validateAndUpload(event.dataTransfer.files);
  }

  function startUploadProgressTimer() {
    const start = Date.now();
    if (uploadTimerRef.current) clearInterval(uploadTimerRef.current);

    const updateEstimatedProgress = () => {
      const elapsedSeconds = Math.floor((Date.now() - start) / 1000);
      let progress;

      if (elapsedSeconds <= 10) {
        progress = 5 + (elapsedSeconds / 10) * 15;
      } else if (elapsedSeconds <= 60) {
        progress = 20 + ((elapsedSeconds - 10) / 50) * 35;
      } else if (elapsedSeconds <= 180) {
        progress = 55 + ((elapsedSeconds - 60) / 120) * 30;
      } else {
        progress = Math.min(94, 85 + ((elapsedSeconds - 180) / 180) * 9);
      }

      setUploadElapsedSeconds(elapsedSeconds);
      setUploadProgress(Math.round(progress));
    };

    updateEstimatedProgress();
    uploadTimerRef.current = setInterval(updateEstimatedProgress, 1000);
  }

  function cancelUpload() {
    if (uploadAbortControllerRef.current) uploadAbortControllerRef.current.abort();
    if (uploadTimerRef.current) clearInterval(uploadTimerRef.current);
    uploadAbortControllerRef.current = null;
    uploadTimerRef.current = null;
    setUploadStage('idle');
    setUploadProgress(0);
    setUploadElapsedSeconds(0);
    setUploadError('');
    setUploadNotice('Analysis was cancelled.');
  }

  async function handleUpload(file) {
    if (!file) return;

    setSelectedFile(file);
    setAnalysis(null);
    setUploadError('');
    setUploadNotice('');
    setReport(null);
    setReportStage('idle');
    setReportProgress(0);
    setReportApprovalStatus('Pending Safety Engineer Review');
    setFinalReportRevisionNote('');
    setTestResults(null);
    setReviewDecisions({});
    setReviewEvidenceFiles({});
    setReviewNotes({});
    setCandidate1Decisions({});
    setCandidate1ReviewNotes({});
    setCandidate1RecoveryRecords({});
    setLiveAuditEvents([]);
    appendAuditEvent('File Upload Started', 'User', file.name, 'User selected a requirements file for upload and analysis.');
    setUploadStage('analyzing');
    setUploadProgress(5);
    setUploadElapsedSeconds(0);
    startUploadProgressTimer();

    const formData = new FormData();
    formData.append('file', file);
    const controller = new AbortController();
    uploadAbortControllerRef.current = controller;

    const apiPromise = fetch(`${API_BASE}/analyze`, {
      method: 'POST',
      body: formData,
      signal: controller.signal,
    }).then(async (response) => {
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || 'Upload failed.');
      }
      return payload;
    });

    try {
      const payload = await apiPromise;
      if (uploadTimerRef.current) clearInterval(uploadTimerRef.current);
      uploadTimerRef.current = null;
      setUploadStage('rendering');
      setUploadProgress(100);
      await new Promise((resolve) => setTimeout(resolve, 300));
      if (controller.signal.aborted) return;
      setAnalysis(payload);
      appendAuditEvent('File Upload Completed', 'System', file.name, 'Requirements file uploaded and backend analysis payload received.');
      setUploadStage('done');
    } catch (error) {
      if (uploadTimerRef.current) clearInterval(uploadTimerRef.current);
      uploadTimerRef.current = null;
      setUploadProgress(0);
      if (error.name === 'AbortError') {
        setUploadStage('idle');
      } else {
        setUploadError(error.message);
        setUploadStage('error');
      }
    } finally {
      if (uploadAbortControllerRef.current === controller) {
        uploadAbortControllerRef.current = null;
      }
    }
  }

  async function runTests() {
    if (!analysis?.matches?.length) return;

    setTestError('');
    setTestResults(null);
    setReport(null);
    setReportStage('idle');
    setReportProgress(0);
    setReportApprovalStatus('Pending Safety Engineer Review');
    setFinalReportRevisionNote('');
    setReviewDecisions({});
    setReviewEvidenceFiles({});
    setReviewNotes({});
    setCandidate1Decisions({});
    setCandidate1ReviewNotes({});
    setCandidate1RecoveryRecords({});
    appendAuditEvent('Verification Simulation Started', 'System', 'Matched Test Queue', 'Verification simulation was started for the current matched test cases.');
    setTestStage('running');
    setTestProgress(0);
    setExecutionLogs([]);

    const apiPromise = fetch(`${API_BASE}/simulate-tests`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ matches: activeMatches }),
    }).then(async (response) => {
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || 'Test simulation failed.');
      }
      return payload;
    });

    const animationPromise = runTestAnimation();

    try {
      const [payload] = await Promise.all([apiPromise, animationPromise]);
      // Defensive handling of payload
      const safeResults = Array.isArray(payload?.results) ? payload.results : [];
      const safeProtocolLogs = Array.isArray(payload?.protocolLogs) ? payload.protocolLogs : [];
      const safeAnomalyReview = Array.isArray(payload?.anomalyReview) ? payload.anomalyReview : [];
      const safeSummary = {
        executedTestCases: payload?.summary?.executedTestCases ?? safeResults.length,
        passCount: payload?.summary?.passCount ?? safeResults.filter((row) => row.result === 'PASS').length,
        reviewCount: payload?.summary?.reviewCount ?? safeResults.filter((row) => row.result === 'REVIEW').length,
        estimatedTotalTimeMinutes: payload?.summary?.estimatedTotalTimeMinutes ?? 0,
      };
      const safePayload = {
        ...payload,
        summary: safeSummary,
        results: safeResults,
        protocolLogs: safeProtocolLogs,
        anomalyReview: safeAnomalyReview,
      };

      setTestResults(safePayload);
      appendAuditEvent(
        'Verification Simulation Completed',
        'System',
        'Protocol Evidence Log',
        `${safeSummary.executedTestCases} test cases executed; ${safeSummary.reviewCount} require engineer review.`
      );
      setExecutionLogs(safeProtocolLogs);
      setTestStage('done');
      setTestProgress(100);
    } catch (error) {
      setTestError(error.message);
      setTestStage('error');
    }
  }

  function runTestAnimation() {
    return new Promise((resolve) => {
      const start = Date.now();
      let logIndex = 0;
      if (testTimerRef.current) clearInterval(testTimerRef.current);

      const progressLogs = buildProtocolProgressLogs();
      setExecutionLogs([progressLogs[0]]);

      testTimerRef.current = setInterval(() => {
        const elapsed = Date.now() - start;
        const percent = Math.min(100, Math.round((elapsed / 10000) * 100));
        setTestProgress(percent);

        const targetLogIndex = Math.min(progressLogs.length - 1, Math.floor((elapsed / 10000) * progressLogs.length));
        if (targetLogIndex > logIndex) {
          logIndex = targetLogIndex;
          setExecutionLogs(progressLogs.slice(0, logIndex + 1));
        }

        if (elapsed >= 10000) {
          clearInterval(testTimerRef.current);
          testTimerRef.current = null;
          setExecutionLogs(progressLogs);
          resolve();
        }
      }, 120);
    });
  }

  function buildProtocolProgressLogs() {
    return [
      { time: '00:00', protocol: 'SYS', direction: 'INIT', id: 'ENV', data: 'BOOT', detail: 'Initializing ECU verification environment' },
      { time: '00:01', protocol: 'SYS', direction: 'LOAD', id: 'QUEUE', data: 'MATCHED TESTS', detail: 'Loading matched requirement-to-test queue' },
      { time: '00:02', protocol: 'CAN', direction: 'TX', id: '0x180', data: 'PENDING', detail: 'Preparing CAN signal transmission simulation' },
      { time: '00:03', protocol: 'UDS', direction: 'TX', id: '0x7E0', data: 'PENDING', detail: 'Preparing UDS diagnostic request simulation' },
      { time: '00:04', protocol: 'LIN', direction: 'TX', id: '0x12', data: 'PENDING', detail: 'Preparing LIN body-control message simulation' },
      { time: '00:05', protocol: 'CAN-FD', direction: 'TX', id: '0x401', data: 'PENDING', detail: 'Preparing CAN-FD battery signal simulation' },
      { time: '00:06', protocol: 'ETH', direction: 'RX', id: 'SOME/IP', data: 'PENDING', detail: 'Preparing Ethernet/SOME-IP event capture' },
      { time: '00:08', protocol: 'SYS', direction: 'ANALYZE', id: 'TRACE', data: 'RX/TX BUFFER', detail: 'Capturing response traces and signal validity metadata' },
      { time: '00:10', protocol: 'SYS', direction: 'WAIT', id: 'BACKEND', data: 'SYNC', detail: 'Waiting for backend-generated protocol evidence log' },
    ];
  }

  function setDecision(testCaseId, decision) {
    setReviewDecisions((current) => ({
      ...current,
      [testCaseId]: decision,
    }));
    setReport(null);
    appendAuditEvent('Simulated Result Review Decision', 'ECU Software Engineer', testCaseId, `Engineer set simulated test result decision to ${decision}.`);
  }

  function setReviewNote(testCaseId, note) {
    setReviewNotes((current) => ({
      ...current,
      [testCaseId]: note,
    }));
    setReport(null);
    if (note.trim()) {
      appendAuditEvent('Engineer Review Note Updated', 'ECU Software Engineer', testCaseId, 'Engineer updated the review note for a review-needed simulated result.');
    }
  }

  function setReviewEvidenceFile(testCaseId, file) {
    if (!file) return;

    setReviewEvidenceFiles((current) => ({
      ...current,
      [testCaseId]: file,
    }));
    appendAuditEvent('Engineer Evidence Uploaded', 'ECU Software Engineer', testCaseId, `Engineer uploaded review evidence file: ${file.name}.`);
  }

  function setCandidate1Decision(requirementId, decision) {
    setCandidate1Decisions((current) => ({
      ...current,
      [requirementId]: decision,
    }));
    appendAuditEvent('Candidate Test Decision', 'ECU Software Engineer', requirementId, `Candidate 1 requirement-level decision changed to ${decision}.`);
    setReport(null);
  }

  function setCandidate1ReviewNote(requirementId, note) {
    setCandidate1ReviewNotes((current) => ({
      ...current,
      [requirementId]: note,
    }));
    if (note.trim()) {
      appendAuditEvent('Candidate Review Note Updated', 'ECU Software Engineer', requirementId, 'Engineer updated the Candidate 1 review note.');
    }
    setReport(null);
  }

  function setCandidate1RecoveryRecord(requirementId, record) {
    setCandidate1RecoveryRecords((current) => ({
      ...current,
      [requirementId]: {
        ...(current[requirementId] || {}),
        ...record,
      },
    }));
    appendAuditEvent('Candidate Rejection Recovery Updated', 'ECU Software Engineer', requirementId, record.reportNote || `Recovery action updated to ${record.recoveryAction || 'UNKNOWN'}.`);
    setReport(null);
  }

  async function generateReport() {
    const decisions = Object.entries(reviewDecisions).map(([testCaseId, decision]) => ({
      testCaseId,
      decision,
      evidenceFileName: reviewEvidenceFiles[testCaseId]?.name || null,
      reviewNote: reviewNotes[testCaseId] || null,
    }));

    if (!decisions.length) {
      setReportError('Confirm or deny at least one review item before drafting the report.');
      return;
    }

    setReportError('');
    setReport(null);
    setReportStage('drafting');
    appendAuditEvent('Report Drafting Started', 'System', 'Draft ISO 26262 Compliance Report', 'Report drafting was requested after engineer review decisions.');
    setReportProgress(0);
    setReportApprovalStatus('Pending Safety Engineer Review');
    setFinalReportRevisionNote('');

    const apiPromise = fetch(`${API_BASE}/draft-report`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        matches: analysis?.matches ?? [],
        activeMappings: activeMatches,
        decisions,
        candidate1Decisions,
        candidate1ReviewNotes,
        candidate1RecoveryRecords,
        traceabilityMatrix: analysis?.traceabilityMatrix ?? [],
        simulationResults: testResults?.results ?? [],
      }),
    }).then(async (response) => {
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || 'Report drafting failed.');
      }
      return payload;
    });

    const animationPromise = runReportAnimation();

    try {
      const [payload] = await Promise.all([apiPromise, animationPromise]);
      setReport(payload);
      appendAuditEvent('Report Drafting Completed', 'System', 'Draft ISO 26262 Compliance Report', 'Draft report was generated and is pending final safety engineer review.');
      setReportStage('done');
      setReportProgress(100);
      setReportApprovalStatus(payload.approvalGate?.approvalStatus || 'Pending Safety Engineer Review');
      setFinalReportRevisionNote('');
    } catch (error) {
      setReportError(error.message);
      setReportStage('error');
    }
  }

  function runReportAnimation() {
    return new Promise((resolve) => {
      const start = Date.now();
      if (reportTimerRef.current) clearInterval(reportTimerRef.current);

      reportTimerRef.current = setInterval(() => {
        const elapsed = Date.now() - start;
        const percent = Math.min(100, Math.round((elapsed / 5000) * 100));
        setReportProgress(percent);

        if (elapsed >= 5000) {
          clearInterval(reportTimerRef.current);
          reportTimerRef.current = null;
          resolve();
        }
      }, 100);
    });
  }



  function setFinalReportApprovalStatus(status) {
    setReportApprovalStatus(status);
    if (status === 'Approved for Internal Review') {
      setFinalReportRevisionNote('');
    }
    appendAuditEvent('Final Report Approval Decision', 'Functional Safety Engineer', 'Draft ISO 26262 Compliance Report', `Final report approval status changed to ${status}.`);
  }

  function updateFinalReportRevisionNote(note) {
    setFinalReportRevisionNote(note);
    if (note.trim()) {
      appendAuditEvent('Final Report Revision Note Updated', 'Functional Safety Engineer', 'Draft ISO 26262 Compliance Report', 'Functional safety engineer updated the final report revision note.');
    }
  }


  function downloadTextFile(filename, content, mimeType = 'text/plain;charset=utf-8') {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  function htmlEscape(value) {
    const text = value === null || value === undefined ? '' : String(value);
    return text
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function buildStyledExcelWorkbook(title, rows, columns) {
    const headerCells = columns.map((column) => `<th>${htmlEscape(column.label)}</th>`).join('');
    const bodyRows = rows.map((row) => (
      `<tr>${columns.map((column) => `<td>${htmlEscape(row[column.key])}</td>`).join('')}</tr>`
    )).join('');

    return `
      <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
        <head>
          <meta charset="UTF-8" />
          <style>
            body { font-family: Arial, sans-serif; }
            h1 { color: #172033; font-size: 22px; }
            .meta { color: #475569; font-size: 12px; margin-bottom: 16px; }
            table { border-collapse: collapse; width: 100%; }
            th { background: #1e40af; color: #ffffff; font-weight: bold; border: 1px solid #94a3b8; padding: 8px; text-align: left; }
            td { border: 1px solid #cbd5e1; padding: 8px; vertical-align: top; mso-number-format: "\\@"; }
            tr:nth-child(even) td { background: #f8fafc; }
          </style>
        </head>
        <body>
          <h1>${htmlEscape(title)}</h1>
          <div class="meta">Generated from AI-Assisted ISO 26262 Verification POC</div>
          <table>
            <thead><tr>${headerCells}</tr></thead>
            <tbody>${bodyRows}</tbody>
          </table>
        </body>
      </html>
    `;
  }

  function exportTraceabilityMatrix() {
    const rows = activeTraceabilityMatrix;
    const workbook = buildStyledExcelWorkbook('ISO 26262 Traceability Matrix', rows, [
      { key: 'requirementId', label: 'Requirement ID' },
      { key: 'asilLevel', label: 'ASIL' },
      { key: 'requirementText', label: 'Requirement Text' },
      { key: 'decompositionStatus', label: 'Decomposition Status' },
      { key: 'decomposedRequirementClauses', label: 'Decomposed Requirement Clauses' },
      { key: 'testCaseId', label: 'Test Case ID' },
      { key: 'testCaseName', label: 'Test Case Name' },
      { key: 'testType', label: 'Test Type' },
      { key: 'coverageType', label: 'Coverage Type' },
      { key: 'confidence', label: 'AI Match Score' },
      { key: 'aiRationale', label: 'AI Rationale' },
      { key: 'mappingReviewReason', label: 'Mapping Review Reason' },
      { key: 'mappingReviewReasonCodes', label: 'Mapping Review Reason Codes' },
      { key: 'reviewStatus', label: 'Review Status' },
    ]);
    downloadTextFile('traceability_matrix.xls', workbook, 'application/vnd.ms-excel;charset=utf-8');
  }

  function exportAuditLog() {
    const rows = [...(analysis?.auditLog || []), ...liveAuditEvents].map((row) => ({
      ...row,
      source: row.isLive ? 'Live User Action' : 'Backend System Event',
    }));
    const workbook = buildStyledExcelWorkbook('ISO 26262 Verification Audit Log', rows, [
      { key: 'eventId', label: 'Event ID' },
      { key: 'eventType', label: 'Event Type' },
      { key: 'actor', label: 'Actor' },
      { key: 'relatedItem', label: 'Related Item' },
      { key: 'details', label: 'Details' },
    ]);
    downloadTextFile('audit_log.xls', workbook, 'application/vnd.ms-excel;charset=utf-8');
  }

  function exportDraftReport() {
    if (!report) return;

    const sectionHtml = report.sections.map((section) => {
      const body = Array.isArray(section.body)
        ? `<ul>${section.body.map((item) => `<li>${htmlEscape(item)}</li>`).join('')}</ul>`
        : `<p>${htmlEscape(section.body)}</p>`;
      return `
        <div class="section">
          <h2>${htmlEscape(section.title)}</h2>
          ${body}
        </div>
      `;
    }).join('');

    const approvalGate = report.approvalGate || {
      reviewerRole: 'Functional Safety Engineer',
      controlRationale: 'Final report export is available after draft generation. Formal approval metadata was not returned by the backend for this draft.',
    };

    const revisionNoteHtml = reportApprovalStatus === 'Revision Required' ? `
      <p><strong>Revision Note:</strong> ${htmlEscape(finalReportRevisionNote || 'Revision was requested, but no revision note was provided.')}</p>
    ` : '';

    const approvalHtml = `
      <div class="approval-box">
        <h2>Final Report Approval</h2>
        <p><strong>Approval Status:</strong> ${htmlEscape(reportApprovalStatus)}</p>
        <p><strong>Reviewer Role:</strong> ${htmlEscape(approvalGate.reviewerRole || 'Functional Safety Engineer')}</p>
        <p><strong>Control Rationale:</strong> ${htmlEscape(approvalGate.controlRationale)}</p>
        ${revisionNoteHtml}
      </div>
    `;

    const documentHtml = `
      <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns="http://www.w3.org/TR/REC-html40">
        <head>
          <meta charset="UTF-8" />
          <title>${htmlEscape(report.title)}</title>
          <style>
            @page { size: A4; margin: 0.75in; }
            body { font-family: Arial, sans-serif; color: #172033; line-height: 1.55; }
            .cover { border-bottom: 4px solid #2563eb; padding-bottom: 18px; margin-bottom: 24px; }
            .eyebrow { color: #2563eb; font-size: 12px; font-weight: bold; letter-spacing: 0.08em; text-transform: uppercase; }
            h1 { font-size: 28px; margin: 8px 0 10px; color: #0f172a; }
            h2 { font-size: 17px; color: #1e40af; margin: 18px 0 8px; border-bottom: 1px solid #cbd5e1; padding-bottom: 4px; }
            p { margin: 6px 0; }
            ul { margin-top: 6px; }
            li { margin-bottom: 5px; }
            .status { display: inline-block; background: #dbeafe; color: #1e40af; border: 1px solid #93c5fd; padding: 6px 10px; font-weight: bold; border-radius: 12px; }
            .section { background: #ffffff; border: 1px solid #e2e8f0; border-left: 5px solid #2563eb; padding: 12px 14px; margin: 12px 0; }
            .approval-box { background: #f0fdfa; border: 1px solid #99f6e4; border-left: 5px solid #0f766e; padding: 12px 14px; margin-top: 18px; }
            .footer { color: #64748b; font-size: 11px; margin-top: 28px; border-top: 1px solid #cbd5e1; padding-top: 10px; }
          </style>
        </head>
        <body>
          <div class="cover">
            <div class="eyebrow">AI-Assisted ISO 26262 Verification POC</div>
            <h1>${htmlEscape(report.title)}</h1>
            <p><span class="status">${htmlEscape(report.status || 'Draft')}</span></p>
            <p>Generated report package prepared from requirement parsing, traceability mapping, verification simulation, anomaly review, engineer confirmation, and final approval status.</p>
          </div>
          ${sectionHtml}
          ${approvalHtml}
          <div class="footer">Generated by the AI-Assisted ISO 26262 Software Verification Compliance POC. Treat as demonstration evidence unless validated by a qualified safety engineer.</div>
        </body>
      </html>
    `;

    downloadTextFile('draft_iso_26262_compliance_report.doc', documentHtml, 'application/msword;charset=utf-8');
  }


  const excludedEvidenceDecisions = new Set([
    'REJECTED_BY_ENGINEER',
    'REJECTED_WITH_ALTERNATIVE',
    'MANUAL_TEST_REQUESTED',
    'REJECTED_UNTESTABLE',
  ]);
  const excludedRecoveryActions = new Set([
    'KEEP_REJECTED',
    'KEEP_REJECTED_WITH_NEW_TEST_UPLOAD',
    'KEEP_REJECTED_UNTESTABLE',
    'MANUAL_TEST_REQUESTED',
    'ALTERNATIVE_SELECTED',
  ]);
  const excludedEvidenceRequirementIds = new Set(
    [
      ...Object.entries(candidate1Decisions)
        .filter(([, decision]) => excludedEvidenceDecisions.has(String(decision).toUpperCase()))
        .map(([requirementId]) => requirementId),
      ...Object.entries(candidate1RecoveryRecords)
        .filter(([, record]) => excludedRecoveryActions.has(String(record?.recoveryAction).toUpperCase()))
        .map(([requirementId]) => requirementId),
    ]
  );
  const engineerApprovedRequirementIds = new Set(
    Object.entries(candidate1Decisions)
      .filter(([, decision]) => String(decision).toUpperCase() === 'APPROVED_BY_ENGINEER')
      .map(([requirementId]) => requirementId)
  );
  const untestableRequirementIds = new Set(
    Object.entries(candidate1RecoveryRecords)
      .filter(([, record]) => record?.recoveryAction === 'KEEP_REJECTED_UNTESTABLE')
      .map(([requirementId]) => requirementId)
  );
  const allMatches = analysis?.matches ?? [];
  const activeMatches = allMatches.filter((row) => (
    !excludedEvidenceRequirementIds.has(getRequirementIdFromRow(row)) &&
    getCoverageTypeFromRow(row) !== 'external_validation_required' &&
    String(row?.review_status ?? row?.reviewStatus ?? '').toLowerCase() !== 'external_validation_required'
  ));
  // Traceability retains unresolved and external-validation rows so exclusions remain visible and auditable.
  const activeTraceabilityMatrix = analysis?.traceabilityMatrix ?? [];
  const candidateReviewItems = analysis?.candidate1ReviewItems ?? [];
  const traceabilityReviewRows = activeTraceabilityMatrix.filter((row) => (
    (isMappingReviewRequiredRow(row) && !engineerApprovedRequirementIds.has(getRequirementIdFromRow(row))) ||
    getCoverageTypeFromRow(row) === 'external_validation_required' ||
    excludedEvidenceRequirementIds.has(getRequirementIdFromRow(row))
  ));
  const candidateDecisionReviewRows = candidateReviewItems.filter((row) => (
    excludedEvidenceRequirementIds.has(getRequirementIdFromRow(row)) ||
    (isMappingReviewRequiredRow(row) && !engineerApprovedRequirementIds.has(getRequirementIdFromRow(row)))
  ));
  const activeReviewItems = Array.from(
    new Map(
      [...traceabilityReviewRows, ...candidateDecisionReviewRows].map((row) => [
        `${getRequirementIdFromRow(row)}:${getTestCaseIdFromRow(row) ?? 'candidate'}`,
        row,
      ])
    ).values()
  );
  const activeRequirementIds = new Set(activeMatches.map(getRequirementIdFromRow).filter(Boolean));
  const activeUniqueTestCaseIds = new Set(activeMatches.map(getTestCaseIdFromRow).filter(Boolean));
  const activeDurationByTest = new Map();
  activeMatches.forEach((row) => {
    const testCaseId = getTestCaseIdFromRow(row);
    if (testCaseId && !activeDurationByTest.has(testCaseId)) activeDurationByTest.set(testCaseId, getTestDurationFromRow(row));
  });
  const activeEstimatedTestTimeMinutes = Array.from(activeDurationByTest.values()).reduce((sum, minutes) => sum + minutes, 0);
  const activeSummary = analysis?.summary ? normalizeSummary(
    analysis.summary,
    {
      totalRequirements: activeRequirementIds.size,
      requirementCount: activeRequirementIds.size,
      uniqueTestCases: activeUniqueTestCaseIds.size,
      uniqueTestCaseCount: activeUniqueTestCaseIds.size,
      mappingCount: activeMatches.length,
      reviewNeeded: new Set(activeReviewItems.map(getRequirementIdFromRow).filter(Boolean)).size,
      estimatedTestTimeMinutes: activeEstimatedTestTimeMinutes,
      untestableRequirementCount: untestableRequirementIds.size,
      excludedEvidenceRequirementCount: excludedEvidenceRequirementIds.size,
      externalValidationRequiredCount: new Set(
        allMatches.filter((row) => getCoverageTypeFromRow(row) === 'external_validation_required').map(getRequirementIdFromRow)
      ).size,
    },
    activeMatches,
    activeReviewItems
  ) : null;

  const combinedAuditLog = [...(analysis?.auditLog || []), ...liveAuditEvents];
  const safeTestSummary = testResults?.summary || {
    executedTestCases: 0,
    passCount: 0,
    reviewCount: 0,
    estimatedTotalTimeMinutes: 0,
  };
  const safeTestResultRows = Array.isArray(testResults?.results) ? testResults.results : [];
  const safeAnomalyReviewRows = Array.isArray(testResults?.anomalyReview) ? testResults.anomalyReview : [];
  const anomalyLookup = Object.fromEntries(
    safeAnomalyReviewRows.map((row) => [row.testCaseId, row])
  );
  const reviewItems = safeTestResultRows.filter((row) => row.result === 'REVIEW');
  const reviewedItemCount = reviewItems.filter((item) => Boolean(reviewDecisions[item.test_case_id])).length;
  const allReviewItemsCompleted = reviewItems.length > 0 && reviewedItemCount === reviewItems.length;
  const isAnalyzing = uploadStage === 'analyzing' || uploadStage === 'rendering';
  const estimatedAnalysisStage = uploadStage === 'rendering'
    ? 'Rendering results'
    : uploadElapsedSeconds < 2
      ? 'Preparing file upload'
      : uploadElapsedSeconds < 10
        ? 'Parsing requirements file'
        : uploadElapsedSeconds < 60
          ? 'C1 requirement-test mapping in progress'
          : uploadElapsedSeconds < 150
            ? 'C2 regression priority calculation in progress'
            : 'Generating dashboard data';
  const estimatedRemainingMinutes = Math.max(0, Math.ceil((240 - uploadElapsedSeconds) / 60));

  return (
    <main className="page">
      <header className="hero">
        <h1>AI Assisted Software Verification Tool</h1>
        <p>Upload requirements, match reusable test cases, simulate execution, confirm review items, and draft ISO 26262-style evidence.</p>
        <p className="address">Public URL: https://active-mustard-chemicals.ngrok-free.dev</p>
      </header>

      <section
        className={`card upload-card${isDragging ? ' is-dragging' : ''}`}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="section-title">
          <Upload size={20} />
          <h2>Requirements Upload</h2>
        </div>
        <label className={`dropzone${isDragging ? ' is-dragging' : ''}${isAnalyzing ? ' is-disabled' : ''}`}>
          <input
            type="file"
            accept=".csv,.xlsx,.xls"
            disabled={isAnalyzing}
            onChange={(event) => {
              validateAndUpload(event.target.files);
              event.target.value = '';
            }}
          />
          <strong>{isDragging ? 'Drop the requirements file here' : 'Drag and drop or select a requirements file'}</strong>
          <span>Accepted formats: CSV, XLSX, XLS</span>
        </label>

        {selectedFile && <p className="file-name">Selected file: {selectedFile.name}</p>}

        {isAnalyzing && (
          <div className="analysis-progress-card" role="status" aria-live="polite">
            <div className="analysis-progress-header">
              <div className="analysis-spinner" aria-hidden="true" />
              <div>
                <strong>{estimatedAnalysisStage}</strong>
                <p>Local AI model analysis is in progress. This may take several minutes.</p>
              </div>
            </div>
            <div className="analysis-progress-meta">
              <span>Estimated progress</span>
              <strong>{uploadProgress}%</strong>
            </div>
            <div
              className="progress-shell"
              role="progressbar"
              aria-label="Estimated analysis progress"
              aria-valuemin="0"
              aria-valuemax="100"
              aria-valuenow={uploadProgress}
            >
              <div className="progress-fill" style={{ width: `${uploadProgress}%` }} />
            </div>
            <div className="analysis-progress-footer">
              <span>
                {uploadElapsedSeconds < 240
                  ? `Estimated wait: about ${estimatedRemainingMinutes} minute${estimatedRemainingMinutes === 1 ? '' : 's'}`
                  : 'Analysis is taking longer than estimated.'}
              </span>
              <button type="button" className="secondary-button analysis-cancel-button" onClick={cancelUpload}>
                Cancel analysis
              </button>
            </div>
          </div>
        )}

        {uploadError && <div className="error-box">{uploadError}</div>}
        {uploadNotice && <div className="notice-box">{uploadNotice}</div>}
      </section>

      {analysis && (
        <>
          <ParserSummary parserInfo={analysis.parserInfo} />
          <Dashboard summary={activeSummary ?? analysis.summary} />
          <Candidate1ReviewWorkspace
            rows={analysis.candidate1ReviewItems || []}
            decisions={candidate1Decisions}
            reviewNotes={candidate1ReviewNotes}
            recoveryRecords={candidate1RecoveryRecords}
            setDecision={setCandidate1Decision}
            setReviewNote={setCandidate1ReviewNote}
            setRecoveryRecord={setCandidate1RecoveryRecord}
            appendAuditEvent={appendAuditEvent}
          />
          <AIRegressionOptimizer
            matches={activeMatches}
            sortMode={optimizerSortMode}
            setSortMode={setOptimizerSortMode}
          />
          <TraceabilityMatrix rows={activeTraceabilityMatrix} />
          <AuditLog rows={combinedAuditLog} liveCount={liveAuditEvents.length} />
          <ExportCenter
            hasTraceability={Boolean(activeTraceabilityMatrix.length)}
            hasAuditLog={Boolean(combinedAuditLog.length)}
            exportTraceability={exportTraceabilityMatrix}
            exportAuditLog={exportAuditLog}
          />

          <section className="card">
            <div className="section-title">
              <Play size={20} />
              <h2 className="title-with-info">
                Verification Simulation
                <InfoPopup title="Verification Simulation" content={DASHBOARD_INFO.verificationSimulation} />
              </h2>
            </div>
            <button className="primary-button" onClick={runTests} disabled={testStage === 'running'}>
              {testStage === 'running' ? 'Running Verification Simulation...' : 'Run Verification Simulation'}
            </button>

            {testStage !== 'idle' && (
              <>
                <ProgressBox title={testStage === 'done' ? 'Verification simulation complete.' : 'Executing matched verification test cases...'} progress={testProgress} />
                <ProtocolExecutionLog logs={executionLogs} />
              </>
            )}
          </section>
        </>
      )}

      {testResults && (
        <section className="card simulated-results-card">
          <h2 className="title-with-info">
            Simulated Test Results
            <InfoPopup title="Simulated Test Results" content={DASHBOARD_INFO.simulatedResults} />
          </h2>
          <div className="mis-kpi-grid">
            <Kpi title="Executed Test Cases" value={safeTestSummary.executedTestCases} />
            <Kpi title="Pass" value={safeTestSummary.passCount} />
            <Kpi title="Execution Review Queue" value={safeTestSummary.reviewCount} />
            <Kpi title="Estimated Total Time" value={`${safeTestSummary.estimatedTotalTimeMinutes} min`} />
          </div>
          <DataTable rows={safeTestResultRows} limit={250} />
        </section>
      )}

      {/* AIAnomalyDetectionReview section removed as now combined with engineer review */}

      {reviewItems.length > 0 && (
        <section className="card combined-review-card">
          <h2 className="title-with-info">
            AI Anomaly Review & Engineer Confirmation
            <InfoPopup title="AI Anomaly Review & Engineer Confirmation" content="Review AI-flagged simulated ECU behavior, upload evidence, document engineering rationale, and confirm whether each result can be used as verification evidence." />
          </h2>
          <p>Review AI-flagged simulated ECU behavior, upload evidence, document engineering rationale, and confirm whether each result can be used as verification evidence.</p>
          <div className="review-progress-summary">
            <span>Reviewed Cases</span>
            <strong>{reviewedItemCount} / {reviewItems.length}</strong>
          </div>
          <div className="review-list">
            {reviewItems.map((item) => {
              const anomaly = anomalyLookup[item.test_case_id] || anomalyLookup[item.testCaseId] || {};
              return (
              <div className="review-item" key={item.test_case_id}>
                <h3>{item.test_case_id} — {item.test_case_name}</h3>
                <div className="combined-anomaly-context">
                  <div className="combined-anomaly-header">
                    <span className="status-pill status-danger">{anomaly.anomalyType || 'Review Required'}</span>
                    <span className="status-pill status-warning">Confidence: {anomaly.confidence !== undefined ? formatConfidence(anomaly.confidence) : 'N/A'}</span>
                  </div>
                  <div className="combined-anomaly-grid">
                    <div>
                      <strong>Expected Behavior</strong>
                      <p>{anomaly.expectedBehavior || item.expected_behavior || 'Expected behavior not available.'}</p>
                    </div>
                    <div>
                      <strong>Observed Behavior</strong>
                      <p>{anomaly.observedBehavior || item.measured_value || 'Observed behavior not available.'}</p>
                    </div>
                    <div>
                      <strong>AI Explanation</strong>
                      <p>{anomaly.aiExplanation || 'No AI anomaly explanation available for this item.'}</p>
                    </div>
                    <div>
                      <strong>Engineer Follow-up</strong>
                      <p>{anomaly.engineerDecision || 'Engineer must confirm whether this result is acceptable evidence, should be rejected, or requires rerun/escalation.'}</p>
                    </div>
                  </div>
                </div>
                <div className="review-evidence-upload">
                  <label>
                    <span>Upload engineer review evidence</span>
                    <input
                      type="file"
                      accept=".pdf,.doc,.docx,.txt,.csv,.xlsx,.xls,.png,.jpg,.jpeg"
                      onChange={(event) => setReviewEvidenceFile(item.test_case_id, event.target.files?.[0])}
                    />
                  </label>
                  {reviewEvidenceFiles[item.test_case_id] && (
                    <p className="evidence-file-name">Selected evidence: {reviewEvidenceFiles[item.test_case_id].name}</p>
                  )}
                </div>
                <div className="engineer-review-note-box">
                  <label htmlFor={`review-note-${item.test_case_id}`}>Engineer Review Note</label>
                  <textarea
                    id={`review-note-${item.test_case_id}`}
                    value={reviewNotes[item.test_case_id] || ''}
                    onChange={(event) => setReviewNote(item.test_case_id, event.target.value)}
                    placeholder="Explain why this review-needed result should be accepted, denied, rerun, revised, or escalated."
                  />
                </div>
                <div className="button-row">
                  <button className="confirm-button" onClick={() => setDecision(item.test_case_id, 'CONFIRMED_ACCEPTED')}>
                    <CheckCircle size={16} /> Confirm / Accept
                  </button>
                  <button className="deny-button" onClick={() => setDecision(item.test_case_id, 'DENIED_REJECTED')}>
                    <XCircle size={16} /> Deny / Reject
                  </button>
                  {reviewDecisions[item.test_case_id] && (
                    <span className={`decision-pill ${reviewDecisions[item.test_case_id] === 'DENIED_REJECTED' ? 'decision-rejected' : 'decision-accepted'}`}>
                      {reviewDecisions[item.test_case_id]}
                    </span>
                  )}
                </div>
              </div>
              );
            })}
          </div>
          <button className="primary-button" onClick={generateReport} disabled={reportStage === 'drafting' || !allReviewItemsCompleted}>
            {reportStage === 'drafting' ? 'Drafting Report...' : 'Draft ISO 26262 Compliance Report'}
          </button>
          {!allReviewItemsCompleted && (
            <p className="review-gate-note">Complete all review decisions before drafting the report.</p>
          )}
          {reportStage !== 'idle' && reportStage !== 'error' && (
            <ProgressBox
              title={reportStage === 'done' ? 'ISO 26262 compliance report draft complete.' : 'Drafting ISO 26262 compliance report...'}
              progress={reportProgress}
            />
          )}
          {reportError && <div className="error-box">{reportError}</div>}
        </section>
      )}

      {report && (
        <section className="card report-card">
          <div className="section-title">
            <FileText size={20} />
            <h2 className="title-with-info">
              Draft ISO 26262 Compliance Report
              <InfoPopup title="Draft ISO 26262 Compliance Report" content={DASHBOARD_INFO.draftReport} />
            </h2>
          </div>
          {report.sections.map((section) => (
            <div className="report-section" key={section.title}>
              <h3>{section.title}</h3>
              {Array.isArray(section.body) ? (
                <ul>
                  {section.body.map((item, index) => <li key={index}>{item}</li>)}
                </ul>
              ) : (
                <p>{section.body}</p>
              )}
            </div>
          ))}

          <FinalReportApprovalGate
            approvalGate={report.approvalGate}
            approvalStatus={reportApprovalStatus}
            setApprovalStatus={setFinalReportApprovalStatus}
            exportReport={exportDraftReport}
            hasReport={Boolean(report)}
            revisionNote={finalReportRevisionNote}
            setRevisionNote={updateFinalReportRevisionNote}
          />
        </section>
      )}
    </main>
  );
}

function ProtocolExecutionLog({ logs }) {
  if (!logs.length) return null;

  return (
    <div className="protocol-log-card">
      <div className="protocol-log-header">
        <h3>Live Protocol Action Log</h3>
        <span>{logs.length} trace events</span>
      </div>
      <div className="protocol-log-list">
        {logs.map((log, index) => (
          <div className="protocol-log-row" key={`${log.time}-${index}`}>
            <span className="log-time">[{log.time}]</span>
            <span className={`protocol-badge protocol-${String(log.protocol).toLowerCase().replace('/', '-')}`}>{log.protocol}</span>
            <span className={`direction-badge direction-${String(log.direction).toLowerCase()}`}>{log.direction}</span>
            <span className="log-id">ID: {log.id}</span>
            <code className="log-data">{log.data}</code>
            <span className="log-detail">{log.detail}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function InfoPopup({ title, content }) {
  const [isOpen, setIsOpen] = React.useState(false);

  return (
    <span className="info-popup-wrap">
      <button
        className="info-popup-button"
        type="button"
        aria-label={`Explain ${title}`}
        onClick={(event) => {
          event.stopPropagation();
          setIsOpen((current) => !current);
        }}
      >
        <HelpCircle size={15} />
      </button>
      {isOpen && (
        <span className="info-popup-card" role="note">
          <button
            className="info-popup-close"
            type="button"
            aria-label="Close explanation popup"
            onClick={(event) => {
              event.stopPropagation();
              setIsOpen(false);
            }}
          >
            ×
          </button>
          <strong>{title}</strong>
          <span>{content}</span>
        </span>
      )}
    </span>
  );
}

function ExportCenter({ hasTraceability, hasAuditLog, exportTraceability, exportAuditLog }) {
  return (
    <section className="card export-card">
      <div className="export-header">
        <div>
          <h2 className="title-with-info">
            Export Center
            <InfoPopup title="Export Center" content={DASHBOARD_INFO.exportCenter} />
          </h2>
          <p>Download verification evidence outputs for presentation, review, or external documentation.</p>
        </div>
      </div>

      <div className="export-button-grid">
        <button className="secondary-button export-button" type="button" onClick={exportTraceability} disabled={!hasTraceability}>
          Export Traceability Matrix Excel
        </button>
        <button className="secondary-button export-button" type="button" onClick={exportAuditLog} disabled={!hasAuditLog}>
          Export Audit Log Excel
        </button>
      </div>
    </section>
  );
}

function FinalReportApprovalGate({ approvalGate, approvalStatus, setApprovalStatus, exportReport, hasReport, revisionNote, setRevisionNote }) {
  const safeApprovalGate = approvalGate || {
    controlRationale: 'Final report export is available after draft generation. Formal approval metadata was not returned by the backend for this draft.',
    reviewerRole: 'Functional Safety Engineer',
    approvalRequired: true,
  };

  if (!hasReport) return null;

  const isApproved = approvalStatus === 'Approved for Internal Review';
  const requiresRevision = approvalStatus === 'Revision Required';
  const exportLabel = isApproved
    ? 'Export Approved Report Word File'
    : requiresRevision
      ? 'Export Revision Draft Word File'
      : 'Export Draft Report Word File';

  return (
    <div className="final-approval-card">
      <div className="final-approval-header">
        <div>
          <h3>Final Report Approval</h3>
          <p>{safeApprovalGate.controlRationale}</p>
        </div>
        <span className={`approval-status-pill ${isApproved ? 'status-good' : requiresRevision ? 'status-danger' : 'status-warning'}`}>
          {approvalStatus}
        </span>
      </div>

      <div className="approval-info-grid">
        <div>
          <span>Reviewer Role</span>
          <strong>{safeApprovalGate.reviewerRole || 'Functional Safety Engineer'}</strong>
        </div>
        <div>
          <span>Approval Required</span>
          <strong>{safeApprovalGate.approvalRequired ? 'Yes' : 'No'}</strong>
        </div>
      </div>

      <div className="button-row final-approval-actions">
        <button className="confirm-button" type="button" onClick={() => setApprovalStatus('Approved for Internal Review')}>
          <CheckCircle size={16} /> Approve Final Draft
        </button>
        <button className="deny-button" type="button" onClick={() => setApprovalStatus('Revision Required')}>
          <XCircle size={16} /> Request Revision
        </button>
      </div>

      {requiresRevision && (
        <div className="final-revision-note-box">
          <div className="final-revision-note-header">
            <div>
              <h4>Revision Request Note</h4>
              <p>Document what must be changed before this draft can be approved. This note is included in the exported revision draft and recorded in the audit workflow.</p>
            </div>
            <span className={revisionNote?.trim() ? 'revision-note-status complete' : 'revision-note-status required'}>
              {revisionNote?.trim() ? 'Revision note added' : 'Revision note required'}
            </span>
          </div>

          <label className="final-revision-note-label" htmlFor="final-report-revision-note">
            Required revision rationale
          </label>
          <textarea
            id="final-report-revision-note"
            className="final-revision-note-textarea"
            value={revisionNote || ''}
            onChange={(event) => setRevisionNote(event.target.value)}
            placeholder="Example: Clarify rejected test evidence for TC-BRK-007, rerun timing anomaly cases with trace evidence, and update traceability rationale before approval."
          />
          {!revisionNote?.trim() && (
            <p className="review-gate-note">Add a revision note so the requested changes are auditable.</p>
          )}
        </div>
      )}

      <div className="approved-report-export">
        <button className="secondary-button export-button" type="button" onClick={exportReport}>
          {exportLabel}
        </button>
      </div>
    </div>
  );
}

function AIAnomalyDetectionReview({ rows }) {
  const [isOpen, setIsOpen] = React.useState(false);
  const reviewRows = rows.filter((row) => row.reviewRequired);
  const visibleRows = reviewRows.slice(0, 250);

  return (
    <section className="card anomaly-card">
      <button className="anomaly-toggle-header" type="button" onClick={() => setIsOpen((current) => !current)}>
        <div>
          <h2 className="title-with-info">
            AI Anomaly Detection Review
            <InfoPopup title="AI Anomaly Detection Review" content={DASHBOARD_INFO.anomalyReview} />
          </h2>
          <p>AI-assisted review of simulated ECU response behavior, anomaly type, confidence, explanation, and required engineer follow-up.</p>
        </div>
        <div className="anomaly-toggle-right">
          <span className="anomaly-pill">{rows.length} analyzed</span>
          <span className="anomaly-pill warning">{reviewRows.length} anomalies</span>
          <span className="anomaly-toggle-icon">{isOpen ? 'Hide review' : 'Show review'}</span>
        </div>
      </button>

      {isOpen && (
        <div className="anomaly-body">
          <div className="table-wrap anomaly-table-wrap">
            <table className="mis-table anomaly-table">
              <thead>
                <tr>
                  <th>Test Case ID</th>
                  <th>Test Case Name</th>
                  <th>Expected Behavior</th>
                  <th>Observed Behavior</th>
                  <th>Anomaly Type</th>
                  <th>Confidence</th>
                  <th>AI Explanation</th>
                  <th>Engineer Decision</th>
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((row, index) => (
                  <tr key={`${row.testCaseId}-${index}`}>
                    <td>{row.testCaseId}</td>
                    <td>{row.testCaseName}</td>
                    <td className="long-text-cell">{row.expectedBehavior}</td>
                    <td>{row.observedBehavior}</td>
                    <td>
                      <span className={`status-pill ${row.reviewRequired ? 'status-danger' : 'status-good'}`}>
                        {row.anomalyType}
                      </span>
                    </td>
                    <td>{row.reviewRequired ? formatConfidence(row.confidence) : 'N/A'}</td>
                    <td className="long-text-cell rationale-cell">{row.aiExplanation}</td>
                    <td>
                      <span className={`status-pill ${row.reviewRequired ? 'status-warning' : 'status-good'}`}>
                        {row.engineerDecision}
                      </span>
                    </td>
                  </tr>
                ))}
                {!visibleRows.length && (
                  <tr><td colSpan="8">No anomalies detected. All analyzed test cases were within the expected verification range.</td></tr>
                )}
              </tbody>
            </table>
          </div>
          {reviewRows.length > visibleRows.length && (
            <p className="table-note">Showing first {visibleRows.length} of {reviewRows.length} anomaly review records.</p>
          )}
        </div>
      )}
    </section>
  );
}

function Candidate1ReviewWorkspace({ rows, decisions, reviewNotes, recoveryRecords, setDecision, setReviewNote, setRecoveryRecord, appendAuditEvent }) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [candidate1Filter, setCandidate1Filter] = React.useState('manual-review');
  const [selectedAlternatives, setSelectedAlternatives] = React.useState({});
  const [recoveryActions, setRecoveryActions] = React.useState({});
  const [collapsedRecoveryItems, setCollapsedRecoveryItems] = React.useState({});
  const [manualTestFiles, setManualTestFiles] = React.useState({});

  const untestableRows = rows.filter((item) => decisions[item.requirementId] === 'REJECTED_UNTESTABLE' || recoveryRecords[item.requirementId]?.recoveryAction === 'KEEP_REJECTED_UNTESTABLE');
  const rejectedRows = rows.filter((item) => ['REJECTED_BY_ENGINEER', 'REJECTED_WITH_ALTERNATIVE', 'MANUAL_TEST_REQUESTED', 'REJECTED_UNTESTABLE'].includes(decisions[item.requirementId]) || recoveryRecords[item.requirementId]?.recoveryAction === 'KEEP_REJECTED_UNTESTABLE');

  const isRecoveredOrRejected = (item) => (
    ['REJECTED_BY_ENGINEER', 'REJECTED_WITH_ALTERNATIVE', 'MANUAL_TEST_REQUESTED', 'REJECTED_UNTESTABLE'].includes(decisions[item.requirementId]) ||
    Boolean(recoveryRecords[item.requirementId]?.recoveryAction)
  );

  const requiresManualReview = (item) => {
    const reviewStatus = String(item.reviewStatus || item.engineerDecision || '').toUpperCase();
    const mappingReviewStatus = String(item.mappingReviewStatus || '').toUpperCase();

    return (
      reviewStatus === 'MANUAL_REVIEW_REQUIRED' ||
      mappingReviewStatus === 'MAPPING_REVIEW_REQUIRED'
    );
  };

  const manualReviewRows = rows.filter((item) => !isRecoveredOrRejected(item) && requiresManualReview(item));
  const readyRows = rows.filter((item) => !isRecoveredOrRejected(item) && !requiresManualReview(item));

  const filteredRows = candidate1Filter === 'manual-review'
    ? manualReviewRows
    : candidate1Filter === 'ready'
      ? readyRows
      : candidate1Filter === 'rejected'
        ? rejectedRows
        : candidate1Filter === 'untestable'
          ? untestableRows
          : rows;

  const visibleRows = filteredRows.slice(0, 20);

  const filterOptions = [
    { key: 'manual-review', label: 'Mapping Review Required', count: manualReviewRows.length },
    { key: 'ready', label: 'Ready for Engineer Approval', count: readyRows.length },
    { key: 'rejected', label: 'Rejected / Recovery', count: rejectedRows.length },
    { key: 'untestable', label: 'Untestable', count: untestableRows.length },
    { key: 'all', label: 'All Requirements', count: rows.length },
  ];

  function useAlternative(requirementId, alternative) {
    setSelectedAlternatives((current) => ({
      ...current,
      [requirementId]: alternative.alternativeId,
    }));
    setRecoveryActions((current) => ({
      ...current,
      [requirementId]: 'ALTERNATIVE_SELECTED',
    }));
    setCollapsedRecoveryItems((current) => ({
      ...current,
      [requirementId]: true,
    }));
    setDecision(requirementId, 'REJECTED_WITH_ALTERNATIVE');
    setRecoveryRecord(requirementId, {
      recoveryAction: 'ALTERNATIVE_SELECTED',
      selectedAlternativeId: alternative.alternativeId,
      selectedAlternativeTestCaseId: alternative.sourceTestCaseId,
      selectedAlternativeTestCaseName: alternative.sourceTestCaseName,
      manualTestFileName: null,
      reportNote: `Rejected AI-generated candidate was recovered by selecting alternative test case ${alternative.sourceTestCaseId}.`,
    });
  }

  function keepRejected(requirementId) {
    setSelectedAlternatives((current) => ({
      ...current,
      [requirementId]: null,
    }));
    setRecoveryActions((current) => ({
      ...current,
      [requirementId]: 'KEEP_REJECTED',
    }));
    setCollapsedRecoveryItems((current) => ({
      ...current,
      [requirementId]: true,
    }));
    setDecision(requirementId, 'REJECTED_BY_ENGINEER');
    setRecoveryRecord(requirementId, {
      recoveryAction: 'KEEP_REJECTED',
      selectedAlternativeId: null,
      selectedAlternativeTestCaseId: null,
      selectedAlternativeTestCaseName: null,
      manualTestFileName: null,
      reportNote: 'Rejected AI-generated candidate was kept rejected and should be reported as an unresolved verification evidence gap.',
    });
  }

  function requestManualTest(requirementId) {
    setSelectedAlternatives((current) => ({
      ...current,
      [requirementId]: null,
    }));
    setRecoveryActions((current) => ({
      ...current,
      [requirementId]: 'MANUAL_TEST_REQUESTED',
    }));
    setCollapsedRecoveryItems((current) => ({
      ...current,
      [requirementId]: false,
    }));
    setDecision(requirementId, 'MANUAL_TEST_REQUESTED');
    setRecoveryRecord(requirementId, {
      recoveryAction: 'MANUAL_TEST_REQUESTED',
      selectedAlternativeId: null,
      selectedAlternativeTestCaseId: null,
      selectedAlternativeTestCaseName: null,
      manualTestFileName: manualTestFiles[requirementId]?.name || null,
      reportNote: 'Manual test design was requested for a rejected AI-generated candidate.',
    });
  }

  function setManualTestFile(requirementId, file) {
    if (!file) return;
    setManualTestFiles((current) => ({
      ...current,
      [requirementId]: file,
    }));
    setRecoveryRecord(requirementId, {
      recoveryAction: 'MANUAL_TEST_REQUESTED',
      manualTestFileName: file.name,
      reportNote: `Manual test design was requested and uploaded as ${file.name}.`,
    });
    appendAuditEvent('Manual Test Case Uploaded', 'ECU Software Engineer', requirementId, `Manual test case file uploaded for rejected Candidate 1 item: ${file.name}.`);
  }

  function setKeptRejectedReplacementFile(requirementId, file) {
    if (!file) return;
    setManualTestFiles((current) => ({
      ...current,
      [`kept-${requirementId}`]: file,
    }));
    setRecoveryActions((current) => ({
      ...current,
      [requirementId]: 'KEEP_REJECTED_WITH_NEW_TEST_UPLOAD',
    }));
    setRecoveryRecord(requirementId, {
      recoveryAction: 'KEEP_REJECTED_WITH_NEW_TEST_UPLOAD',
      selectedAlternativeId: null,
      selectedAlternativeTestCaseId: null,
      selectedAlternativeTestCaseName: null,
      manualTestFileName: file.name,
      reportNote: `AI-generated candidate remained rejected, but engineer uploaded a new replacement test case file: ${file.name}.`,
    });
    appendAuditEvent('Kept-Rejected Replacement Test Uploaded', 'ECU Software Engineer', requirementId, `Engineer kept the AI candidate rejected and uploaded replacement test case file: ${file.name}.`);
  }

  function markKeptRejectedUntestable(requirementId) {
    setSelectedAlternatives((current) => ({
      ...current,
      [requirementId]: null,
    }));
    setRecoveryActions((current) => ({
      ...current,
      [requirementId]: 'KEEP_REJECTED_UNTESTABLE'
    }));
    setCollapsedRecoveryItems((current) => ({
      ...current,
      [requirementId]: true,
    }));
    setDecision(requirementId, 'REJECTED_UNTESTABLE');
    setRecoveryRecord(requirementId, {
      recoveryAction: 'KEEP_REJECTED_UNTESTABLE',
      selectedAlternativeId: null,
      selectedAlternativeTestCaseId: null,
      selectedAlternativeTestCaseName: null,
      manualTestFileName: null,
      reportNote: 'AI-generated candidate was kept rejected and the requirement was marked currently untestable by the engineer. This must remain an unresolved safety verification action until clarified, decomposed, or assigned a feasible verification method.',
    });
    appendAuditEvent('Requirement Marked Untestable', 'ECU Software Engineer', requirementId, 'Engineer kept the AI candidate rejected and marked the requirement currently untestable for this verification cycle.');
  }

  function toggleRecoveryCollapse(requirementId) {
    setCollapsedRecoveryItems((current) => ({
      ...current,
      [requirementId]: !current[requirementId],
    }));
    appendAuditEvent('Recovery Options Visibility Changed', 'ECU Software Engineer', requirementId, 'Rejected-candidate recovery options were expanded or collapsed.');
  }

  return (
    <section className="card candidate1-card">
      <button className="candidate1-toggle-header" type="button" onClick={() => setIsOpen((current) => !current)}>
        <div>
          <h2 className="title-with-info">
            AI Requirement Extraction & Test Case Derivation
            <InfoPopup title="AI Requirement Extraction & Test Case Derivation" content={DASHBOARD_INFO.candidate1Workspace} />
          </h2>
          <p>Review extracted requirements, detected boundary clues, reusable historical tests, and AI-generated candidate test cases before engineer approval.</p>
        </div>
        <div className="candidate1-toggle-right">
          <span className="candidate1-pill">{Math.max(0, rows.length - untestableRows.length)} active requirements</span>
          <span className="candidate1-pill warning">{manualReviewRows.length} mapping review</span>
          <span className="candidate1-pill success">{readyRows.length} ready for approval</span>
          {untestableRows.length > 0 && <span className="candidate1-pill warning">{untestableRows.length} untestable</span>}
          {rejectedRows.length > 0 && <span className="candidate1-pill danger">{rejectedRows.length} rejected</span>}
          <span className="candidate1-toggle-icon">{isOpen ? 'Hide workspace' : 'Show workspace'}</span>
        </div>
      </button>

      {isOpen && (
        <div className="candidate1-body">
          <div className="candidate1-filter-tabs">
            {filterOptions.map((option) => (
              <button
                key={option.key}
                className={`candidate1-filter-tab ${candidate1Filter === option.key ? 'active' : ''}`}
                type="button"
                onClick={() => setCandidate1Filter(option.key)}
              >
                <span>{option.label}</span>
                <strong>{option.count}</strong>
              </button>
            ))}
          </div>

          <div className="candidate1-filter-context">
            {candidate1Filter === 'manual-review'
              ? 'Showing requirement-to-test mappings that the backend classified as low-confidence or ambiguous and therefore require engineer review before downstream use.'
              : candidate1Filter === 'ready'
                ? 'Showing requirement-to-test mappings that the backend classified as ready for direct engineer approval.'
                : candidate1Filter === 'rejected'
                  ? 'Showing rejected candidates and recovery items requiring alternative selection, manual design, kept-rejected handling, or untestable resolution.'
                  : candidate1Filter === 'untestable'
                    ? 'Showing requirements currently marked untestable and removed from active downstream evidence calculations.'
                    : 'Showing all requirement review items.'}
          </div>

          <div className="candidate1-list">
            {visibleRows.map((item) => {
              const candidate = item.generatedCandidateTestCase || {};
              const historicalTests = item.recommendedHistoricalTests || [];
              const boundaryClues = item.boundaryClues || [];
              const decomposedClauses = Array.isArray(item.decomposedRequirementClauses) ? item.decomposedRequirementClauses : [];
              const mappingReviewReasonCodes = Array.isArray(item.mappingReviewReasonCodes) ? item.mappingReviewReasonCodes : [];
              const currentDecision = decisions[item.requirementId] || candidate.reviewStatus || item.engineerDecision;
              const currentReviewNote = reviewNotes[item.requirementId] || item.engineerReviewNote || '';

              return (
                <div className="candidate1-item" key={item.requirementId}>
                  <div className="candidate1-item-header">
                    <div>
                      <h3>{item.requirementId}</h3>
                      <p>{item.extractedRequirementText}</p>
                    </div>
                    <span className={`status-pill ${asilColorClass(item.asilLevel)}`}>{item.asilLevel}</span>
                  </div>

                  {(item.mappingReviewStatus || item.mappingReviewReason || mappingReviewReasonCodes.length > 0) && (
                    <div className={`mapping-review-reason-card ${item.mappingReviewStatus === 'MAPPING_REVIEW_REQUIRED' ? 'requires-review' : 'ready-review'}`}>
                      <div className="mapping-review-reason-header">
                        <strong>{item.mappingReviewStatus === 'MAPPING_REVIEW_REQUIRED' ? 'Mapping Review Required' : 'Ready for Engineer Approval'}</strong>
                        <span>{item.reviewStatus || 'READY_FOR_APPROVAL'}</span>
                      </div>
                      {item.mappingReviewReason && <p>{item.mappingReviewReason}</p>}
                      {mappingReviewReasonCodes.length > 0 && (
                        <div className="mapping-review-code-row">
                          {mappingReviewReasonCodes.map((code) => (
                            <span className="mapping-review-code-pill" key={`${item.requirementId}-${code}`}>
                              {formatMappingReviewReasonCode(code)}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {item.decompositionStatus === 'DECOMPOSED' && decomposedClauses.length > 1 ? (
                    <div className="requirement-decomposition-card decomposed">
                      <div className="requirement-decomposition-header">
                        <div>
                          <strong>Requirement Decomposition</strong>
                          <p>This requirement was split into smaller verification clauses before engineer review.</p>
                        </div>
                        <span>{decomposedClauses.length} clauses</span>
                      </div>
                      <div className="requirement-clause-list">
                        {decomposedClauses.map((clause) => (
                          <div className="requirement-clause-item" key={clause.clauseId}>
                            <div className="requirement-clause-title-row">
                              <strong>{clause.clauseId}</strong>
                              <span>{clause.verificationIntent || 'Requirement behavior'}</span>
                            </div>
                            <p>{clause.clauseText}</p>
                            {Array.isArray(clause.boundaryClues) && clause.boundaryClues.length > 0 && (
                              <div className="requirement-clause-tags">
                                {clause.boundaryClues.map((clue, index) => (
                                  <span key={`${clause.clauseId}-${index}`}>{clue}</span>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="single-clause-compact-pill">
                      <span>Single verification clause</span>
                    </div>
                  )}

                  <div className="candidate1-grid">
                    <div className="candidate1-panel">
                      <h4>Detected Boundary Clues</h4>
                      <div className="tag-row">
                        {boundaryClues.map((clue, index) => (
                          <span className="boundary-tag" key={index}>{clue}</span>
                        ))}
                      </div>
                    </div>

                    <div className="candidate1-panel">
                      <h4>Recommended Historical Tests</h4>
                      {historicalTests.map((test) => (
                        <div className="historical-test" key={test.testCaseId}>
                          <strong>{test.testCaseId} — {test.testCaseName}</strong>
                          <span>{test.testType} · {formatConfidence(test.confidence)}</span>
                          <p>{test.rationale}</p>
                        </div>
                      ))}
                      {!historicalTests.length && <p>No historical test recommendations available.</p>}
                    </div>
                  </div>

                  <div className="candidate-test-card">
                    <h4>{candidate.candidateTestCaseId} — {candidate.candidateTestCaseName}</h4>
                    <p><strong>Objective:</strong> {candidate.objective}</p>
                    <p><strong>Precondition:</strong> {candidate.precondition}</p>
                    <div>
                      <strong>Procedure:</strong>
                      <ol>
                        {(candidate.procedure || []).map((step, index) => (
                          <li key={index}>{step}</li>
                        ))}
                      </ol>
                    </div>
                    <p><strong>Expected Response:</strong> {candidate.expectedResponse}</p>
                    <div className="candidate1-review-note-box">
                      <label htmlFor={`candidate1-note-${item.requirementId}`}>Engineer Review Note</label>
                      <textarea
                        id={`candidate1-note-${item.requirementId}`}
                        value={currentReviewNote}
                        onChange={(event) => setReviewNote(item.requirementId, event.target.value)}
                        placeholder="Explain why this candidate test case should be approved, rejected, revised, or escalated."
                      />
                    </div>
                    <div className="button-row candidate1-actions">
                      <button className="confirm-button" type="button" onClick={() => setDecision(item.requirementId, 'APPROVED_BY_ENGINEER')}>
                        <CheckCircle size={16} /> Approve Candidate Test
                      </button>
                      <button
                        className="deny-button"
                        type="button"
                        onClick={() => {
                          setDecision(item.requirementId, 'REJECTED_BY_ENGINEER');
                          keepRejected(item.requirementId);
                        }}
                      >
                        <XCircle size={16} /> Reject Candidate Test
                      </button>
                      <span
                        className={`decision-pill ${
                          currentDecision === 'REJECTED_BY_ENGINEER'
                            ? 'decision-rejected'
                            : currentDecision === 'APPROVED_BY_ENGINEER' || currentDecision === 'REJECTED_WITH_ALTERNATIVE'
                              ? 'decision-accepted'
                              : currentDecision === 'MANUAL_TEST_REQUESTED'
                                ? 'decision-recovery'
                                : ''
                        }`}
                      >
                        {currentDecision}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
            {!visibleRows.length && (
              <div className="candidate1-empty">No requirement review items available for the current filter.</div>
            )}
          </div>
          {filteredRows.length > visibleRows.length && (
            <p className="table-note">Showing first {visibleRows.length} of {filteredRows.length} candidate review items in the current filter.</p>
          )}

          {untestableRows.length > 0 && (
            <div className="untestable-requirement-record-card">
              <h3>Currently Untestable Requirements Recorded</h3>
              <p>The following requirement(s) were removed from active downstream requirement counts, regression planning, traceability export, simulation input, and report evidence calculations until they are clarified or assigned a feasible verification method.</p>
              <ul>
                {untestableRows.map((item) => (
                  <li key={`untestable-${item.requirementId}`}>
                    <strong>{item.requirementId}</strong> — {item.extractedRequirementText}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {rejectedRows.length > 0 && (
            <div className="rejection-recovery-panel">
              <div className="rejection-recovery-header">
                <div>
                  <h3>Rejected Candidate Tests & Alternatives</h3>
                  <p>Rejected AI-generated candidate tests are grouped here so the engineer can select a replacement, keep the rejection, or request manual test design.</p>
                </div>
                <span>{rejectedRows.length} rejected candidates</span>
              </div>

              <div className="rejection-recovery-list">
                {rejectedRows.map((item) => {
                  const candidate = item.generatedCandidateTestCase || {};
                  const alternatives = item.alternativeCandidateTests || [];
                  const manualDesign = item.manualTestDesignCandidate || {};
                  const selectedAlternativeId = selectedAlternatives[item.requirementId];
                  const recoveryAction = recoveryActions[item.requirementId] || (decisions[item.requirementId] === 'MANUAL_TEST_REQUESTED' ? 'MANUAL_TEST_REQUESTED' : decisions[item.requirementId] === 'REJECTED_WITH_ALTERNATIVE' ? 'ALTERNATIVE_SELECTED' : 'KEEP_REJECTED');
                  const selectedAlternative = alternatives.find((alternative) => alternative.alternativeId === selectedAlternativeId);
                  const isRecoveryCollapsed = Boolean(collapsedRecoveryItems[item.requirementId]);
                  const manualTestFile = manualTestFiles[item.requirementId];
                  const keptRejectedReplacementFile = manualTestFiles[`kept-${item.requirementId}`];
                  const isKeptRejectedFlow = ['KEEP_REJECTED', 'KEEP_REJECTED_WITH_NEW_TEST_UPLOAD', 'KEEP_REJECTED_UNTESTABLE'].includes(recoveryAction);

                  return (
                    <div className="rejection-recovery-item" key={`recovery-${item.requirementId}`}>
                      <div className="rejection-recovery-item-header">
                        <div>
                          <h4>{item.requirementId} — Rejected Candidate</h4>
                          <p>{candidate.candidateTestCaseId} — {candidate.candidateTestCaseName}</p>
                        </div>
                        <span className={`decision-pill ${recoveryAction === 'ALTERNATIVE_SELECTED' || recoveryAction === 'KEEP_REJECTED_WITH_NEW_TEST_UPLOAD' ? 'decision-accepted' : recoveryAction === 'MANUAL_TEST_REQUESTED' ? 'decision-recovery' : 'decision-rejected'}`}>
                          {recoveryAction === 'ALTERNATIVE_SELECTED'
                            ? 'Alternative Active'
                            : recoveryAction === 'MANUAL_TEST_REQUESTED'
                              ? 'Manual Design Active'
                              : recoveryAction === 'KEEP_REJECTED_WITH_NEW_TEST_UPLOAD'
                                ? 'New Test Uploaded'
                                : recoveryAction === 'KEEP_REJECTED_UNTESTABLE'
                                  ? 'Marked Untestable'
                                  : 'Rejected'}
                        </span>
                      </div>

                      <div className="rejection-recovery-status-grid">
                        <div>
                          <span>Current Recovery Status</span>
                          <strong>
                            {recoveryAction === 'ALTERNATIVE_SELECTED'
                              ? 'Alternative Selected'
                              : recoveryAction === 'MANUAL_TEST_REQUESTED'
                                ? 'Manual Test Design Requested'
                                : recoveryAction === 'KEEP_REJECTED_WITH_NEW_TEST_UPLOAD'
                                  ? 'Kept Rejected + New Test Uploaded'
                                  : recoveryAction === 'KEEP_REJECTED_UNTESTABLE'
                                    ? 'Kept Rejected + Marked Untestable'
                                    : 'Kept Rejected'}
                          </strong>
                        </div>
                        <div>
                          <span>Active Recovery Choice</span>
                          <strong>
                            {recoveryAction === 'ALTERNATIVE_SELECTED' && selectedAlternative
                              ? selectedAlternative.sourceTestCaseId
                              : recoveryAction === 'MANUAL_TEST_REQUESTED'
                                ? manualDesign.manualDesignId || 'Manual Test Design'
                                : recoveryAction === 'KEEP_REJECTED_WITH_NEW_TEST_UPLOAD'
                                  ? keptRejectedReplacementFile?.name || 'Replacement Test Uploaded'
                                  : recoveryAction === 'KEEP_REJECTED_UNTESTABLE'
                                    ? 'Currently Untestable'
                                    : 'None'}
                          </strong>
                        </div>
                        <div>
                          <span>Available Alternatives</span>
                          <strong>{alternatives.length}</strong>
                        </div>
                      </div>

                      {isRecoveryCollapsed && (
                        <div className="collapsed-recovery-summary">
                          <div>
                            <strong>
                              {recoveryAction === 'ALTERNATIVE_SELECTED' ? 'Alternative selected'
                                : recoveryAction === 'KEEP_REJECTED_WITH_NEW_TEST_UPLOAD' ? 'Replacement uploaded'
                                : recoveryAction === 'KEEP_REJECTED_UNTESTABLE' ? 'Marked untestable'
                                : recoveryAction === 'KEEP_REJECTED' ? 'Rejection kept'
                                : 'Recovery collapsed'}
                            </strong>
                            <span>
                              {recoveryAction === 'ALTERNATIVE_SELECTED' && selectedAlternative
                                ? `${selectedAlternative.sourceTestCaseId} is now the active replacement candidate.`
                                : recoveryAction === 'KEEP_REJECTED_WITH_NEW_TEST_UPLOAD'
                                  ? `${keptRejectedReplacementFile?.name || 'A replacement test case file'} was uploaded while keeping the AI candidate rejected.`
                                  : recoveryAction === 'KEEP_REJECTED_UNTESTABLE'
                                    ? 'This requirement is currently marked untestable and will remain an unresolved safety verification action.'
                                    : recoveryAction === 'KEEP_REJECTED'
                                      ? 'This rejection will be included as an unresolved evidence gap in the final report package.'
                                      : 'Recovery details are collapsed.'}
                            </span>
                          </div>
                          <button className="secondary-button" type="button" onClick={() => toggleRecoveryCollapse(item.requirementId)}>
                            Reopen Recovery Options
                          </button>
                        </div>
                      )}

                      {isKeptRejectedFlow && (
                        <div className="kept-rejected-followup-card">
                          <div className="kept-rejected-followup-header">
                            <div>
                              <h5>Kept-Rejected Follow-up Decision</h5>
                              <p>The AI-generated candidate remains rejected. Choose whether to upload a new engineer-authored test case or mark this requirement currently untestable.</p>
                            </div>
                            <span className={`decision-pill ${recoveryAction === 'KEEP_REJECTED_UNTESTABLE' ? 'decision-rejected' : recoveryAction === 'KEEP_REJECTED_WITH_NEW_TEST_UPLOAD' ? 'decision-accepted' : 'decision-recovery'}`}>
                              {recoveryAction === 'KEEP_REJECTED_UNTESTABLE'
                                ? 'Untestable Selected'
                                : recoveryAction === 'KEEP_REJECTED_WITH_NEW_TEST_UPLOAD'
                                  ? 'Replacement Uploaded'
                                  : 'Follow-up Needed'}
                            </span>
                          </div>

                          <div className="kept-rejected-followup-grid">
                            <div className="kept-rejected-option-card">
                              <h6>Upload New Test Case</h6>
                              <p>Use this when the AI candidate is rejected but the requirement can still be verified through a human-authored test case.</p>
                              <label className="kept-rejected-upload-label">
                                <span>Upload replacement test case file</span>
                                <input
                                  type="file"
                                  accept=".pdf,.doc,.docx,.txt,.csv,.xlsx,.xls,.png,.jpg,.jpeg"
                                  onChange={(event) => setKeptRejectedReplacementFile(item.requirementId, event.target.files?.[0])}
                                />
                              </label>
                              {keptRejectedReplacementFile && (
                                <p className="manual-test-file-name">Uploaded replacement test case: {keptRejectedReplacementFile.name}</p>
                              )}
                            </div>

                            <div className="kept-rejected-option-card danger-option">
                              <h6>Mark Requirement Untestable</h6>
                              <p>Use this only when the requirement cannot currently be verified because it is ambiguous, infeasible, missing conditions, or outside the current bench capability.</p>
                              <button className="deny-button" type="button" onClick={() => markKeptRejectedUntestable(item.requirementId)}>
                                Mark as Currently Untestable
                              </button>
                            </div>
                          </div>
                        </div>
                      )}

                      {!isRecoveryCollapsed && recoveryAction === 'ALTERNATIVE_SELECTED' && selectedAlternative && (
                        <div className="active-recovery-card active-alternative-card">
                          <h5>Active Replacement Candidate</h5>
                          <p><strong>{selectedAlternative.sourceTestCaseId} — {selectedAlternative.sourceTestCaseName}</strong></p>
                          <p>{selectedAlternative.replacementObjective}</p>
                          <p><strong>Expected Response:</strong> {selectedAlternative.expectedResponse}</p>
                        </div>
                      )}

                      {!isRecoveryCollapsed && recoveryAction === 'MANUAL_TEST_REQUESTED' && (
                        <div className="active-recovery-card manual-design-card">
                          <h5>{manualDesign.manualTestCaseName || `Manual Test Design Required for ${item.requirementId}`}</h5>
                          <p><strong>Objective:</strong> {manualDesign.objective || 'Create a human-authored verification test case for this rejected requirement.'}</p>
                          <div>
                            <strong>Recommended Manual Design Steps:</strong>
                            <ol>
                              {(manualDesign.recommendedSteps || [
                                'Review the rejected AI candidate and document the rejection rationale.',
                                'Define a targeted test stimulus and measurable pass/fail criteria.',
                                'Assign the manual test case for engineer review before evidence use.',
                              ]).map((step, index) => (
                                <li key={index}>{step}</li>
                              ))}
                            </ol>
                          </div>
                          <p><strong>Expected Response:</strong> {manualDesign.expectedResponse || 'The manually designed test should produce traceable verification evidence after engineer approval.'}</p>
                          <div className="manual-test-upload-box">
                            <label>
                              <span>Upload new manual test case file</span>
                              <input
                                type="file"
                                accept=".pdf,.doc,.docx,.txt,.csv,.xlsx,.xls,.png,.jpg,.jpeg"
                                onChange={(event) => setManualTestFile(item.requirementId, event.target.files?.[0])}
                              />
                            </label>
                            {manualTestFile && (
                              <p className="manual-test-file-name">Uploaded manual test case: {manualTestFile.name}</p>
                            )}
                          </div>
                        </div>
                      )}

                      {!isRecoveryCollapsed && <div className="alternative-list">
                        {alternatives.map((alternative) => (
                          <div
                            className={selectedAlternativeId === alternative.alternativeId ? 'alternative-card selected' : 'alternative-card'}
                            key={alternative.alternativeId}
                          >
                            <div className="alternative-card-header">
                              <div>
                                <h5>{alternative.sourceTestCaseId} — {alternative.sourceTestCaseName}</h5>
                                <span>{alternative.testType} · {formatConfidence(alternative.confidence)} · {formatHours(alternative.durationMinutes)}</span>
                              </div>
                              <button
                                className={selectedAlternativeId === alternative.alternativeId ? 'confirm-button' : 'secondary-button'}
                                type="button"
                                onClick={() => useAlternative(item.requirementId, alternative)}
                              >
                                {selectedAlternativeId === alternative.alternativeId ? 'Selected Alternative' : 'Use Alternative'}
                              </button>
                            </div>
                            <p><strong>Replacement Objective:</strong> {alternative.replacementObjective}</p>
                            <p><strong>Reason:</strong> {alternative.replacementReason}</p>
                            <p><strong>Expected Response:</strong> {alternative.expectedResponse}</p>
                          </div>
                        ))}
                        {!alternatives.length && (
                          <div className="alternative-empty">No ranked alternatives are available for this requirement. Manual test design is recommended.</div>
                        )}
                      </div>}

                      {!isRecoveryCollapsed && <div className="button-row rejection-recovery-actions">
                        <button className="deny-button" type="button" onClick={() => keepRejected(item.requirementId)}>
                          Keep Rejected
                        </button>
                        <button className="secondary-button" type="button" onClick={() => requestManualTest(item.requirementId)}>
                          Request Manual Test Design
                        </button>
                      </div>}

                      {!isRecoveryCollapsed && recoveryAction === 'ALTERNATIVE_SELECTED' && selectedAlternative && (
                        <div className="active-recovery-card active-alternative-card recovery-output-card">
                          <h5>Selected Recovery Path: Alternative Test Case</h5>
                          <p><strong>{selectedAlternative.sourceTestCaseId} — {selectedAlternative.sourceTestCaseName}</strong></p>
                          <p><strong>Objective:</strong> {selectedAlternative.replacementObjective}</p>
                          <p><strong>Expected Response:</strong> {selectedAlternative.expectedResponse}</p>
                        </div>
                      )}

                      {!isRecoveryCollapsed && recoveryAction === 'MANUAL_TEST_REQUESTED' && (
                        <div className="active-recovery-card manual-design-card recovery-output-card">
                          <h5>Selected Recovery Path: Manual Test Design</h5>
                          <p><strong>{manualDesign.manualTestCaseName || `Manual Test Design Required for ${item.requirementId}`}</strong></p>
                          <p><strong>Objective:</strong> {manualDesign.objective || 'Create a human-authored verification test case for this rejected requirement.'}</p>
                          <div>
                            <strong>Recommended Manual Design Steps:</strong>
                            <ol>
                              {(manualDesign.recommendedSteps || [
                                'Review the rejected AI candidate and document the rejection rationale.',
                                'Define a targeted test stimulus and measurable pass/fail criteria.',
                                'Assign the manual test case for engineer review before evidence use.',
                              ]).map((step, index) => (
                                <li key={index}>{step}</li>
                              ))}
                            </ol>
                          </div>
                          <p><strong>Expected Response:</strong> {manualDesign.expectedResponse || 'The manually designed test should produce traceable verification evidence after engineer approval.'}</p>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function TraceabilityMatrix({ rows }) {
  const [isOpen, setIsOpen] = React.useState(false);
  const visibleRows = rows.slice(0, 250);
  const reviewRequired = rows.filter((row) => String(row.reviewStatus || '').toLowerCase().includes('review')).length;

  return (
    <section className="card traceability-card">
      <button className="traceability-toggle-header" type="button" onClick={() => setIsOpen((current) => !current)}>
        <div>
          <h2 className="title-with-info">
            Traceability Matrix
            <InfoPopup title="Traceability Matrix" content={DASHBOARD_INFO.traceabilityMatrix} />
          </h2>
          <p>Requirement-to-test evidence table linking software safety requirements, ASIL level, candidate tests, confidence, coverage type, and engineer review status.</p>
        </div>
        <div className="traceability-toggle-right">
          <span className="traceability-pill">{rows.length} mappings</span>
          <span className="traceability-pill warning">{reviewRequired} review gates</span>
          <span className="traceability-toggle-icon">{isOpen ? 'Hide matrix' : 'Show matrix'}</span>
        </div>
      </button>

      {isOpen && (
        <div className="traceability-body">
          <div className="table-wrap traceability-table-wrap">
            <table className="mis-table traceability-table">
              <thead>
                <tr>
                  <th>Requirement ID</th>
                  <th>ASIL</th>
                  <th>Requirement Text</th>
                  <th>Test Case</th>
                  <th>Test Type</th>
                  <th>Coverage Type</th>
                  <th>Confidence</th>
                  <th>AI Rationale</th>
                  <th>Review Status</th>
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((row, index) => (
                  <tr key={`${row.requirementId}-${row.testCaseId}-${index}`}>
                    <td>{row.requirementId}</td>
                    <td><span className={`status-pill ${asilColorClass(row.asilLevel)}`}>{row.asilLevel}</span></td>
                    <td className="long-text-cell">{row.requirementText}</td>
                    <td>{row.testCaseId} — {row.testCaseName}</td>
                    <td>{row.testType}</td>
                    <td>{row.coverageType}</td>
                    <td>{formatConfidence(row.confidence)}</td>
                    <td className="long-text-cell rationale-cell">{row.aiRationale || 'No rationale available.'}</td>
                    <td><span className="status-pill status-warning">{row.reviewStatus}</span></td>
                  </tr>
                ))}
                {!visibleRows.length && (
                  <tr><td colSpan="9">No traceability mappings available.</td></tr>
                )}
              </tbody>
            </table>
          </div>
          {rows.length > visibleRows.length && (
            <p className="table-note">Showing first {visibleRows.length} of {rows.length} traceability mappings.</p>
          )}
        </div>
      )}
    </section>
  );
}

function AuditLog({ rows, liveCount = 0 }) {
  const [isOpen, setIsOpen] = React.useState(false);
  const visibleRows = rows.slice().reverse().slice(0, 300);
  const latestLiveEvent = rows.slice().reverse().find((row) => row.isLive || String(row.eventId || '').startsWith('LIVE'));

  return (
    <section className="card audit-card">
      <button className="audit-toggle-header" type="button" onClick={() => setIsOpen((current) => !current)}>
        <div>
          <h2 className="title-with-info">
            Audit Log
            <InfoPopup title="Audit Log" content={DASHBOARD_INFO.auditLog} />
          </h2>
          <p>System and live user-action trace of upload, parsing, AI matching, engineer decisions, rejection recovery, evidence upload, simulation, and report drafting.</p>
        </div>
        <div className="audit-toggle-right">
          <span className="audit-pill">{rows.length} total events</span>
          <span className="audit-pill live">{liveCount} live events</span>
          <span className="audit-toggle-icon">{isOpen ? 'Hide log' : 'Show log'}</span>
        </div>
      </button>

      {latestLiveEvent && (
        <div className="audit-live-note">
          <strong>Latest live event:</strong> {latestLiveEvent.eventType} · {latestLiveEvent.relatedItem} — {latestLiveEvent.details}
        </div>
      )}

      {isOpen && (
        <div className="audit-body">
          <div className="table-wrap audit-table-wrap">
            <table className="mis-table audit-table">
              <thead>
                <tr>
                  <th>Event ID</th>
                  <th>Event Type</th>
                  <th>Actor</th>
                  <th>Related Item</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((row, index) => {
                  const isLiveRow = row.isLive || String(row.eventId || '').startsWith('LIVE');
                  return (
                    <tr className={isLiveRow ? 'audit-live-row' : 'audit-system-row'} key={`${row.eventId}-${index}`}>
                      <td>{row.eventId}</td>
                      <td>{row.eventType}</td>
                      <td>{row.actor}</td>
                      <td>{row.relatedItem}</td>
                      <td className="long-text-cell">{row.details}</td>
                    </tr>
                  );
                })}
                {!rows.length && (
                  <tr><td colSpan="5">No audit events available.</td></tr>
                )}
              </tbody>
            </table>
            {rows.length > visibleRows.length && (
              <p className="table-note">Showing latest {visibleRows.length} of {rows.length} audit events.</p>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

function ParserSummary({ parserInfo }) {
  const [isOpen, setIsOpen] = React.useState(false);

  if (!parserInfo) return null;

  const warnings = Array.isArray(parserInfo.warnings) ? parserInfo.warnings : [];
  const statusText = String(parserInfo.status || 'parsed').replaceAll('_', ' ');

  return (
    <section className="card parser-summary-card">
      <button className="parser-toggle-header" type="button" onClick={() => setIsOpen((current) => !current)}>
        <div>
          <h2>File Parsing Summary</h2>
          <p>The uploaded file was automatically inspected and normalized before verification analysis.</p>
        </div>
        <div className="parser-toggle-right">
          <span className="parser-status-pill">{statusText}</span>
          <span className="parser-toggle-icon">{isOpen ? 'Hide details' : 'Show details'}</span>
        </div>
      </button>

      {isOpen && (
        <div className="parser-summary-body">
          <div className="parser-info-grid">
            <div className="parser-info-item">
              <span>File Type</span>
              <strong>{parserInfo.fileType || 'N/A'}</strong>
            </div>
            <div className="parser-info-item">
              <span>Sheet / Source</span>
              <strong>{parserInfo.sheetName || 'N/A'}</strong>
            </div>
            <div className="parser-info-item">
              <span>Detected Header Row</span>
              <strong>{parserInfo.headerRow || 'N/A'}</strong>
            </div>
            <div className="parser-info-item">
              <span>Parsed Requirements</span>
              <strong>{parserInfo.parsedRequirements || 0}</strong>
            </div>
            <div className="parser-info-item">
              <span>Requirement ID Column</span>
              <strong>{parserInfo.requirementIdColumn || 'N/A'}</strong>
            </div>
            <div className="parser-info-item">
              <span>Requirement Text Column</span>
              <strong>{parserInfo.requirementTextColumn || 'N/A'}</strong>
            </div>
            <div className="parser-info-item">
              <span>ASIL Column</span>
              <strong>{parserInfo.asilColumn || 'N/A'}</strong>
            </div>
            <div className="parser-info-item">
              <span>Tables Scanned</span>
              <strong>{parserInfo.candidateTablesScanned || 1}</strong>
            </div>
          </div>

          {warnings.length > 0 && (
            <div className="parser-warning-box">
              <h3>Parser Notes</h3>
              <ul>
                {warnings.map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function ProgressBox({ title, progress }) {
  return (
    <div className="progress-box">
      <p>{title}</p>
      <div className="progress-shell">
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>
      <span>{progress}%</span>
    </div>
  );
}

function Dashboard({ summary }) {
  const requirementCountsByAsil = summary.requirementCountsByAsil ?? summary.asilCounts ?? [];
  const testTypeCounts = summary.testTypeCounts ?? [];
  const coverageByAsil = summary.coverageByAsil ?? [];
  const estimatedTestTimeByAsil = summary.estimatedTestTimeByAsil ?? [];
  const confidenceDistribution = summary.confidenceDistribution ?? [];
  const reviewNeededByAsil = summary.reviewNeededByAsil ?? [];
  const reviewItems = summary.reviewItems ?? [];
  const longestTests = summary.longestTests ?? [];
  const [activeDashboardGroup, setActiveDashboardGroup] = React.useState('overview');
  const [expandedChartGroups, setExpandedChartGroups] = React.useState({ asil: false, portfolio: false });

  function toggleChartGroup(groupName) {
    setExpandedChartGroups((current) => ({
      ...current,
      [groupName]: !current[groupName],
    }));
  }

  return (
    <section className="card dashboard-card">
      <div className="dashboard-header">
        <div>
          <h2>Verification Statistics Dashboard</h2>
          <p>ISO 26262 AI-assisted requirement-to-test coverage overview</p>
        </div>
        <span className={`asil-badge ${asilColorClass(summary.highestAsilLevel)}`}>
          Highest ASIL: {summary.highestAsilLevel ?? 'N/A'}
        </span>
      </div>

      <div className="dashboard-group-tabs">
        <button
          className={activeDashboardGroup === 'overview' ? 'dashboard-tab active' : 'dashboard-tab'}
          type="button"
          onClick={() => setActiveDashboardGroup('overview')}
        >
          Overview
        </button>
        <button
          className={activeDashboardGroup === 'charts' ? 'dashboard-tab active' : 'dashboard-tab'}
          type="button"
          onClick={() => setActiveDashboardGroup('charts')}
        >
          Charts
        </button>
        <button
          className={activeDashboardGroup === 'risk' ? 'dashboard-tab active' : 'dashboard-tab'}
          type="button"
          onClick={() => setActiveDashboardGroup('risk')}
        >
          Risk / Review
        </button>
        <button
          className={activeDashboardGroup === 'portfolio' ? 'dashboard-tab active' : 'dashboard-tab'}
          type="button"
          onClick={() => setActiveDashboardGroup('portfolio')}
        >
          Test Portfolio
        </button>
      </div>

      {activeDashboardGroup === 'overview' && (
        <div className="dashboard-group-panel">
          <div className="mis-kpi-grid">
            <div className="kpi-card kpi-blue">
              <div className="kpi-label-row"><span>Active Evidence Requirements</span></div>
              <strong>{summary.totalRequirements ?? summary.requirementCount ?? 0}</strong>
              <small>Requirements currently eligible for active evidence</small>
            </div>
            <div className="kpi-card kpi-purple">
              <div className="kpi-label-row"><span>Unique Test Cases</span></div>
              <strong>{summary.uniqueTestCases ?? summary.uniqueTestCaseCount ?? 0}</strong>
              <small>Candidate tests selected by matching</small>
            </div>
            <div className="kpi-card kpi-green">
              <div className="kpi-label-row"><span>Coverage Rate</span></div>
              <strong>{formatPercent(summary.coverageRate)}</strong>
              <small>Requirements linked to candidate tests</small>
            </div>
            <div className="kpi-card kpi-orange">
              <div className="kpi-label-row"><span>Avg. Match Score</span></div>
              <strong>{formatConfidence(summary.averageConfidence)}</strong>
              <small>Mean AI match confidence</small>
            </div>
            <div className="kpi-card kpi-red">
              <div className="kpi-label-row"><span>Mapping Review Queue</span></div>
              <strong>{summary.reviewNeededRequirements ?? summary.reviewNeeded ?? 0}</strong>
              <small>Unresolved, external, or low-confidence mappings</small>
            </div>
            <div className="kpi-card kpi-teal">
              <div className="kpi-label-row"><span>Estimated Test Time</span></div>
              <strong>{formatHours(summary.totalTestTimeMinutes ?? summary.estimatedTestTimeMinutes)}</strong>
              <small>Total unique execution duration</small>
            </div>
            <div className="kpi-card kpi-slate">
              <div className="kpi-label-row"><span>High-Risk Requirements</span></div>
              <strong>{summary.highRiskRequirementCount ?? summary.highRiskRequirements ?? 0}</strong>
              <small>ASIL C and ASIL D requirements</small>
            </div>
            <div className="kpi-card kpi-indigo">
              <div className="kpi-label-row"><span>Test Reuse Ratio</span></div>
              <strong>{summary.testReuseRatio ?? 0}</strong>
              <small>Mappings per unique test case</small>
            </div>
          </div>

          <div className="executive-summary-card">
            <h3>Executive Summary</h3>
            <p>
              {summary.executiveSummary ??
                'Upload analysis completed. Review the coverage, confidence, and test planning indicators below.'}
            </p>
          </div>
        </div>
      )}

      {activeDashboardGroup === 'charts' && (
        <div className="dashboard-group-panel dashboard-chart-groups">
          <div className="dashboard-chart-group-card">
            <button className="dashboard-chart-group-header chart-group-toggle-header" type="button" onClick={() => toggleChartGroup('asil')}>
              <div>
                <h3 className="title-with-info">
                  ASIL-Based Verification Charts
                </h3>
                <p>ASIL-grouped indicators for requirement criticality, coverage, verification effort, and review burden.</p>
              </div>
              <span className="chart-group-toggle-icon">{expandedChartGroups.asil ? 'Hide charts' : 'Expand charts'}</span>
            </button>

            {expandedChartGroups.asil && (
              <div className="dashboard-grid">
              <ChartCard title="Requirements by ASIL Level">
                <div className="mis-chart-container">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={requirementCountsByAsil}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="asilLevel" />
                      <YAxis allowDecimals={false} />
                      <Tooltip />
                      <Bar dataKey="count" name="Requirements">
                        {requirementCountsByAsil.map((entry) => (
                          <Cell key={entry.asilLevel} fill={ASIL_COLORS[entry.asilLevel] || '#64748b'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </ChartCard>

              <ChartCard title="Coverage Rate by ASIL Level">
                <div className="chart-container">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={coverageByAsil}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="asilLevel" />
                      <YAxis domain={[0, 100]} tickFormatter={(value) => `${value}%`} />
                      <Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} />
                      <Bar dataKey="coverageRate" name="Coverage Rate">
                        {coverageByAsil.map((entry) => (
                          <Cell key={entry.asilLevel} fill={ASIL_COLORS[entry.asilLevel] || '#64748b'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </ChartCard>

              <ChartCard title="Estimated Test Time by ASIL">
                <div className="chart-container">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={estimatedTestTimeByAsil}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="asilLevel" />
                      <YAxis allowDecimals={false} />
                      <Tooltip formatter={(value) => `${value} min`} />
                      <Bar dataKey="estimatedMinutes" name="Estimated Minutes">
                        {estimatedTestTimeByAsil.map((entry) => (
                          <Cell key={entry.asilLevel} fill={ASIL_COLORS[entry.asilLevel] || '#64748b'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </ChartCard>

              <ChartCard title="Mapping Review Queue by ASIL Level">
                <div className="chart-container">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={reviewNeededByAsil}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="asilLevel" />
                      <YAxis allowDecimals={false} />
                      <Tooltip />
                      <Bar dataKey="reviewNeeded" name="Mapping Review Queue">
                        {reviewNeededByAsil.map((entry) => (
                          <Cell key={entry.asilLevel} fill={ASIL_COLORS[entry.asilLevel] || '#64748b'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </ChartCard>
              </div>
            )}
          </div>

          <div className="dashboard-chart-group-card">
            <button className="dashboard-chart-group-header chart-group-toggle-header" type="button" onClick={() => toggleChartGroup('portfolio')}>
              <div>
                <h3 className="title-with-info">
                  Test Portfolio & Match Score Charts
                </h3>
                <p>Supporting indicators for test-type composition and AI match confidence quality.</p>
              </div>
              <span className="chart-group-toggle-icon">{expandedChartGroups.portfolio ? 'Hide charts' : 'Expand charts'}</span>
            </button>

            {expandedChartGroups.portfolio && (
              <div className="dashboard-grid dashboard-grid-compact">
              <ChartCard title="Unique Test Cases by Test Type">
                <div className="chart-container">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={testTypeCounts}
                        dataKey="count"
                        nameKey="testType"
                        cx="50%"
                        cy="50%"
                        innerRadius={55}
                        outerRadius={90}
                        label
                      >
                        {testTypeCounts.map((_, index) => (
                          <Cell key={index} fill={TEST_TYPE_COLORS[index % TEST_TYPE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </ChartCard>

              <ChartCard title="Requirement-Level Match Score Distribution">
                <div className="chart-container">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={confidenceDistribution} layout="vertical" margin={{ left: 32 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" allowDecimals={false} />
                      <YAxis type="category" dataKey="label" width={140} />
                      <Tooltip />
                      <Bar dataKey="count" name="Mappings">
                        {confidenceDistribution.map((entry) => (
                          <Cell key={entry.label} fill={STATUS_COLORS[entry.status] || '#2563eb'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </ChartCard>
              </div>
            )}
          </div>
        </div>
      )}

      {activeDashboardGroup === 'risk' && (
        <div className="dashboard-group-panel table-grid single-dashboard-table">
          <div className="table-card">
            <h3 className="title-with-info">
              Risk / Review Queue
            </h3>
            <div className="table-wrap section-scroll-list">
              <table className="mis-table">
                <thead>
                  <tr>
                    <th>Requirement ID</th>
                    <th>ASIL</th>
                    <th>Candidate Test Case</th>
                    <th>Confidence</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {reviewItems.map((item) => (
                    <tr key={`${item.requirementId}-${item.matchedTestCaseId}`}>
                      <td>{item.requirementId}</td>
                      <td>
                        <span className={`status-pill ${asilColorClass(item.asilLevel)}`}>{item.asilLevel}</span>
                      </td>
                      <td>
                        {item.matchedTestCaseId} — {item.matchedTestCaseName}
                      </td>
                      <td>{formatConfidence(item.confidence)}</td>
                      <td>
                        <span className={`status-pill ${item.action === 'Manual Review' ? 'status-danger' : 'status-warning'}`}>{item.action}</span>
                      </td>
                    </tr>
                  ))}
                  {!reviewItems.length && (
                    <tr>
                      <td colSpan="5">No review items identified.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeDashboardGroup === 'portfolio' && (
        <div className="dashboard-group-panel table-grid single-dashboard-table">
          <div className="table-card">
            <h3 className="title-with-info">
              Longest Test Cases
            </h3>
            <div className="table-wrap section-scroll-list">
              <table className="mis-table">
                <thead>
                  <tr>
                    <th>Test Case ID</th>
                    <th>Test Case Name</th>
                    <th>Type</th>
                    <th>Duration</th>
                  </tr>
                </thead>
                <tbody>
                  {longestTests.map((item) => (
                    <tr key={item.testCaseId}>
                      <td>{item.testCaseId}</td>
                      <td>{item.testCaseName}</td>
                      <td>{item.testType}</td>
                      <td>{formatHours(item.durationMinutes)}</td>
                    </tr>
                  ))}
                  {!longestTests.length && (
                    <tr>
                      <td colSpan="4">No test duration data available.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function AIRegressionOptimizer({ matches, sortMode, setSortMode }) {
  const optimizedTests = React.useMemo(() => {
    const uniqueTests = new Map();

    matches.forEach((match) => {
      const testCaseId = match.matched_test_case_id;
      if (!testCaseId) return;

      if (!uniqueTests.has(testCaseId)) {
        uniqueTests.set(testCaseId, {
          testCaseId,
          testCaseName: match.matched_test_case_name,
          testType: match.test_type,
          asilLevel: match.asil_level,
          durationMinutes: Number(match.test_duration_minutes || 0),
          mappedRequirements: 0,
          averageConfidence: 0,
          confidenceTotal: 0,
          riskScoreTotal: 0,
          averageRiskScore: 0,
          rankingReasons: [],
        });
      }

      const test = uniqueTests.get(testCaseId);
      test.mappedRequirements += 1;
      test.confidenceTotal += Number(match.match_score || 0);
      test.riskScoreTotal += Number(match.regression_risk_score || 0);
      test.averageConfidence = test.confidenceTotal / test.mappedRequirements;
      test.averageRiskScore = Math.round(test.riskScoreTotal / test.mappedRequirements);
      if (match.regression_ranking_reason && !test.rankingReasons.includes(match.regression_ranking_reason)) {
        test.rankingReasons.push(match.regression_ranking_reason);
      }
    });

    return Array.from(uniqueTests.values()).sort((a, b) => {
      if (sortMode === 'risk') {
        return b.averageRiskScore - a.averageRiskScore;
      }
      if (sortMode === 'shortest') {
        return a.durationMinutes - b.durationMinutes;
      }
      return b.durationMinutes - a.durationMinutes;
    });
  }, [matches, sortMode]);

  return (
    <section className="card optimizer-card">
      <div className="optimizer-header">
        <div>
          <h2 className="title-with-info">
            AI Regression Optimizer
            <InfoPopup title="AI Regression Optimizer" content={DASHBOARD_INFO.regressionOptimizer} />
          </h2>
          <p>Prioritize regression test execution using risk score, ASIL relevance, confidence, review gates, and estimated execution duration.</p>
        </div>

        <div className="optimizer-toggle">
          <button
            className={sortMode === 'risk' ? 'toggle-button active' : 'toggle-button'}
            onClick={() => setSortMode('risk')}
          >
            Highest Risk First
          </button>
          <button
            className={sortMode === 'longest' ? 'toggle-button active' : 'toggle-button'}
            onClick={() => setSortMode('longest')}
          >
            Longest First
          </button>
          <button
            className={sortMode === 'shortest' ? 'toggle-button active' : 'toggle-button'}
            onClick={() => setSortMode('shortest')}
          >
            Shortest First
          </button>
        </div>
      </div>

      <div className="optimizer-summary">
        <div>
          <span>Sort Mode</span>
          <strong>{sortMode === 'risk' ? 'Highest Risk First' : sortMode === 'longest' ? 'Longest Duration First' : 'Shortest Duration First'}</strong>
        </div>
        <div>
          <span>Unique Test Cases</span>
          <strong>{optimizedTests.length}</strong>
        </div>
        <div>
          <span>Total Estimated Time</span>
          <strong>{formatHours(optimizedTests.reduce((sum, test) => sum + test.durationMinutes, 0))}</strong>
        </div>
      </div>

      {sortMode === 'risk' && (
        <div className="risk-score-explanation-card">
          <h3>How to Interpret Highest Risk First</h3>
          <p>
            The regression risk score ranks test cases by how urgently they should be executed or reviewed during regression testing.
            It considers safety criticality, AI match confidence, estimated duration, mapped requirement count, and verification relevance.
            A high score does not mean the test failed; it means the test is important to prioritize.
          </p>
          <div className="risk-score-guide-grid">
            <div>
              <strong>80–100</strong>
              <span>Execute or review early</span>
            </div>
            <div>
              <strong>50–79</strong>
              <span>Run in the normal regression cycle</span>
            </div>
            <div>
              <strong>0–49</strong>
              <span>Lower priority unless linked to recent changes</span>
            </div>
          </div>
        </div>
      )}

      <div className="table-wrap">
        <table className="mis-table optimizer-table">
          <thead>
            <tr>
              <th>Priority</th>
              <th>Test Case ID</th>
              <th>Test Case Name</th>
              <th>Type</th>
              <th>ASIL</th>
              <th>Risk Score</th>
              <th>Duration</th>
              <th>Mapped Requirements</th>
              <th>Avg. Match Score</th>
              <th>Ranking Reason</th>
            </tr>
          </thead>
          <tbody>
            {optimizedTests.map((test, index) => (
              <tr key={test.testCaseId}>
                <td>{index + 1}</td>
                <td>{test.testCaseId}</td>
                <td>{test.testCaseName}</td>
                <td>{test.testType}</td>
                <td><span className={`status-pill ${asilColorClass(test.asilLevel)}`}>{test.asilLevel}</span></td>
                <td><span className="status-pill status-warning">{test.averageRiskScore}</span></td>
                <td>{test.durationMinutes} min</td>
                <td>{test.mappedRequirements}</td>
                <td>{formatConfidence(test.averageConfidence)}</td>
                <td className="long-text-cell rationale-cell">{test.rankingReasons[0] || 'Prioritized from available execution metadata.'}</td>
              </tr>
            ))}
            {!optimizedTests.length && (
              <tr><td colSpan="10">No test cases available for optimization.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Kpi({ title, value }) {
  return (
    <div className="kpi">
      <span>{title}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ChartCard({ title, children }) {
  return (
    <div className="chart-card mis-chart-card">
      <h3>{title}</h3>
      {children}
    </div>
  );
}

function DataTable({ rows, limit }) {
  const visibleRows = rows.slice(0, limit);
  if (!visibleRows.length) return null;

  const columns = Object.keys(visibleRows[0]);

  return (
    <div className="table-wrap section-scroll-list">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column.replaceAll('_', ' ')}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {visibleRows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {columns.map((column) => (
                <td key={column}>{String(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
