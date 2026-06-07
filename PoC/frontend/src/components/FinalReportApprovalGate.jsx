import React from 'react';
import { CheckCircle, XCircle } from 'lucide-react';

export default function FinalReportApprovalGate({ approvalGate, approvalStatus, setApprovalStatus, exportReport, hasReport, revisionNote, setRevisionNote }) {
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
