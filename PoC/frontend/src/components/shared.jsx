import React from 'react';

export function ProgressBox({ title, progress }) {
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

export function Kpi({ title, value }) {
  return (
    <div className="kpi">
      <span>{title}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function ChartCard({ title, children }) {
  return (
    <div className="chart-card mis-chart-card">
      <h3>{title}</h3>
      {children}
    </div>
  );
}

export function DataTable({ rows, limit }) {
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
