import React from 'react';
import InfoPopup from './InfoPopup.jsx';
import { DASHBOARD_INFO } from '../constants.js';

export default function AuditLog({ rows, liveCount = 0 }) {
  const visibleRows = rows.slice().reverse().slice(0, 300);
  const latestLiveEvent = rows.slice().reverse().find((row) => row.isLive || String(row.eventId || '').startsWith('LIVE'));

  return (
    <section className="card audit-card">
      <div className="audit-toggle-header">
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
        </div>
      </div>

      {latestLiveEvent && (
        <div className="audit-live-note">
          <strong>Latest live event:</strong> {latestLiveEvent.eventType} · {latestLiveEvent.relatedItem} — {latestLiveEvent.details}
        </div>
      )}

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
    </section>
  );
}
