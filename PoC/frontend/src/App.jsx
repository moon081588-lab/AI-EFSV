import React from 'react';
import { Upload, Play, FileText, CheckCircle, XCircle } from 'lucide-react';

import ParserSummary from './components/ParserSummary.jsx';
import Dashboard from './components/Dashboard.jsx';
import Candidate1ReviewWorkspace from './components/Candidate1ReviewWorkspace.jsx';
import AIRegressionOptimizer from './components/AIRegressionOptimizer.jsx';
import TraceabilityMatrix from './components/TraceabilityMatrix.jsx';
import AuditLog from './components/AuditLog.jsx';
import ExportCenter from './components/ExportCenter.jsx';
import FinalReportApprovalGate from './components/FinalReportApprovalGate.jsx';
import InfoPopup from './components/InfoPopup.jsx';
import ProtocolExecutionLog from './components/ProtocolExecutionLog.jsx';
import { ProgressBox, Kpi, DataTable } from './components/shared.jsx';
import StickyNav from './components/StickyNav.jsx';
import AIStatusBadge from './components/AIStatusBadge.jsx';

import {
  normalizeSummary,
  getRequirementIdFromRow,
  getTestCaseIdFromRow,
  getAsilFromRow,
  getMatchScoreFromRow,
  getTestDurationFromRow,
  getCoverageTypeFromRow,
  isMappingReviewRequiredRow,
  formatConfidence,
  formatHours,
  asilColorClass,
} from './utils.js';
import { API_BASE, DASHBOARD_INFO } from './constants.js';

export default function App() {
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

  const visibleSections = new Set(['upload']);
  if (analysis) {
    visibleSections.add('parser-summary');
    visibleSections.add('dashboard');
    visibleSections.add('c1-review');
    visibleSections.add('regression');
    visibleSections.add('traceability');
    visibleSections.add('audit-log');
    visibleSections.add('export');
    visibleSections.add('simulation');
  }
  if (testResults) visibleSections.add('test-results');
  if (reviewItems.length > 0) visibleSections.add('anomaly-review');
  if (report) visibleSections.add('draft-report');

  return (
    <div className="app-layout">
    <StickyNav visibleSections={visibleSections} />
    <main className="page">
      <header className="hero">
        <div className="hero-top">
          <h1>AI Assisted Software Verification Tool</h1>
          <AIStatusBadge />
        </div>
        <p>Upload requirements, match reusable test cases, simulate execution, confirm review items, and draft ISO 26262-style evidence.</p>
        <p className="address">Public URL: https://active-mustard-chemicals.ngrok-free.dev</p>
      </header>

      <section
        id="upload"
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
          <div id="parser-summary"><ParserSummary parserInfo={analysis.parserInfo} /></div>
          <div id="dashboard"><Dashboard summary={activeSummary ?? analysis.summary} /></div>
          <div id="c1-review"><Candidate1ReviewWorkspace
            rows={analysis.candidate1ReviewItems || []}
            decisions={candidate1Decisions}
            reviewNotes={candidate1ReviewNotes}
            recoveryRecords={candidate1RecoveryRecords}
            setDecision={setCandidate1Decision}
            setReviewNote={setCandidate1ReviewNote}
            setRecoveryRecord={setCandidate1RecoveryRecord}
            appendAuditEvent={appendAuditEvent}
          /></div>
          <div id="regression"><AIRegressionOptimizer
            matches={activeMatches}
            sortMode={optimizerSortMode}
            setSortMode={setOptimizerSortMode}
          /></div>
          <div id="traceability"><TraceabilityMatrix rows={activeTraceabilityMatrix} /></div>
          <div id="audit-log"><AuditLog rows={combinedAuditLog} liveCount={liveAuditEvents.length} /></div>
          <div id="export"><ExportCenter
            hasTraceability={Boolean(activeTraceabilityMatrix.length)}
            hasAuditLog={Boolean(combinedAuditLog.length)}
            exportTraceability={exportTraceabilityMatrix}
            exportAuditLog={exportAuditLog}
          /></div>

          <section id="simulation" className="card">
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
        <section id="test-results" className="card simulated-results-card">
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

      {reviewItems.length > 0 && (
        <section id="anomaly-review" className="card combined-review-card">
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
        <section id="draft-report" className="card report-card">
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
    </div>
  );
}
