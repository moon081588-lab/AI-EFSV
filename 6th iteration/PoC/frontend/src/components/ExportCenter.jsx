import React from 'react';
import InfoPopup from './InfoPopup.jsx';
import { DASHBOARD_INFO } from '../constants.js';

export default function ExportCenter({ hasTraceability, hasAuditLog, exportTraceability, exportAuditLog }) {
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
