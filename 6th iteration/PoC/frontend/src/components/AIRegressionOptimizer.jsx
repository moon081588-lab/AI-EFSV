import React from 'react';
import InfoPopup from './InfoPopup.jsx';
import { DASHBOARD_INFO } from '../constants.js';
import { asilColorClass, formatConfidence, formatHours } from '../utils.js';

export default function AIRegressionOptimizer({ matches, sortMode, setSortMode }) {
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
