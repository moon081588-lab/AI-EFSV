import React from 'react';
import InfoPopup from './InfoPopup.jsx';
import { DASHBOARD_INFO } from '../constants.js';
import { formatConfidence } from '../utils.js';

export default function AIAnomalyDetectionReview({ rows }) {
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
