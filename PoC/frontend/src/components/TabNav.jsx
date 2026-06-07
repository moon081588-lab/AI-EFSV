const NAV_ITEMS = [
  { id: 'upload',         label: 'Upload' },
  { id: 'parser-summary', label: 'Parser Summary' },
  { id: 'dashboard',      label: 'Dashboard' },
  { id: 'c1-review',      label: 'Mapping Review' },
  { id: 'regression',     label: 'Regression' },
  { id: 'traceability',   label: 'Traceability' },
  { id: 'audit-log',      label: 'Audit Log' },
  { id: 'export',         label: 'Export' },
  { id: 'simulation',     label: 'Simulation' },
  { id: 'test-results',   label: 'Test Results' },
  { id: 'anomaly-review', label: 'Anomaly Review' },
  { id: 'draft-report',   label: 'Draft Report' },
];

export default function TabNav({ activeSection, visibleSections, onTabChange }) {
  return (
    <nav className="tab-nav" aria-label="Sections">
      <div className="tab-nav-scroll">
        {NAV_ITEMS.map(({ id, label }) => {
          const enabled = visibleSections.has(id);
          const active  = activeSection === id;
          return (
            <button
              key={id}
              type="button"
              className={`tab-nav-item${active ? ' tab-nav-item--active' : ''}${!enabled ? ' tab-nav-item--locked' : ''}`}
              onClick={() => enabled && onTabChange(id)}
              disabled={!enabled}
              title={!enabled ? 'Complete previous steps to unlock' : label}
            >
              {label}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
