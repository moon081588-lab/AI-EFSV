import React from 'react';
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
import InfoPopup from './InfoPopup.jsx';
import { ChartCard } from './shared.jsx';
import { ASIL_COLORS, STATUS_COLORS, TEST_TYPE_COLORS, DASHBOARD_INFO } from '../constants.js';
import { asilColorClass, formatPercent, formatConfidence, formatHours } from '../utils.js';

export default function Dashboard({ summary }) {
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
