import React from 'react';
import InfoPopup from './InfoPopup.jsx';
import { DASHBOARD_INFO } from '../constants.js';
import { asilColorClass, formatConfidence } from '../utils.js';

export default function TraceabilityMatrix({ rows }) {
  const visibleRows = rows.slice(0, 250);
  const reviewRequired = rows.filter((row) => String(row.reviewStatus || '').toLowerCase().includes('review')).length;

  return (
    <section className="card traceability-card">
      <div className="traceability-toggle-header">
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
        </div>
      </div>

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
    </section>
  );
}
