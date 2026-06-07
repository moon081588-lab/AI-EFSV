import React from 'react';
import { CheckCircle, XCircle } from 'lucide-react';
import InfoPopup from './InfoPopup.jsx';
import { DASHBOARD_INFO } from '../constants.js';
import { asilColorClass, formatConfidence, formatHours, formatMappingReviewReasonCode } from '../utils.js';

export default function Candidate1ReviewWorkspace({ rows, decisions, reviewNotes, recoveryRecords, setDecision, setReviewNote, setRecoveryRecord, appendAuditEvent }) {
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
                          setCandidate1Filter('rejected');
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

          {candidate1Filter === 'rejected' && rejectedRows.length > 0 && (
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
