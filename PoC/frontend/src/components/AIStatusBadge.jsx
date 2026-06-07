import { useEffect, useRef, useState } from 'react';
import { API_BASE } from '../constants.js';

const MODEL_KEYS = ['c1_matching', 'c2_prioritizer', 'c3a_anomaly', 'c3b_report'];

export default function AIStatusBadge() {
  const [status, setStatus] = useState(null);
  const [expanded, setExpanded] = useState(false);
  const [lastChecked, setLastChecked] = useState(null);
  const intervalRef = useRef(null);

  async function fetchStatus() {
    try {
      const res = await fetch(`${API_BASE}/ai/status`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setStatus(data);
      setLastChecked(new Date());
    } catch {
      setStatus(null);
    }
  }

  useEffect(() => {
    fetchStatus();
    intervalRef.current = setInterval(fetchStatus, 30_000);
    return () => clearInterval(intervalRef.current);
  }, []);

  if (!status) return null;

  const { running_count, total_count, models, ai_enabled } = status;
  const allGood = running_count === total_count;
  const anyRunning = running_count > 0;
  const summaryColor = allGood ? 'green' : anyRunning ? 'amber' : 'red';

  return (
    <div className="ai-status-badge">
      <button
        type="button"
        className={`ai-status-pill ai-status-pill--${summaryColor}`}
        onClick={() => setExpanded((v) => !v)}
        title="Click to see AI model status"
      >
        <span className={`ai-status-dot ai-status-dot--${summaryColor}`} />
        <span className="ai-status-label">
          AI {running_count}/{total_count}
        </span>
        <span className="ai-status-chevron">{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div className="ai-status-panel">
          <p className="ai-status-panel-title">Model Status</p>
          <ul className="ai-status-model-list">
            {MODEL_KEYS.map((key) => {
              const m = models[key];
              if (!m) return null;
              const dotColor = m.running ? 'green' : ai_enabled || key === 'c3a_anomaly' ? 'red' : 'gray';
              return (
                <li key={key} className="ai-status-model-row">
                  <span className={`ai-status-dot ai-status-dot--${dotColor}`} />
                  <div className="ai-status-model-info">
                    <span className="ai-status-model-label">{m.label}</span>
                    <span className="ai-status-model-name">{m.model}</span>
                    {!m.running && m.reason && (
                      <span className="ai-status-model-reason">{m.reason}</span>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
          <div className="ai-status-panel-footer">
            {lastChecked && (
              <span className="ai-status-last-checked">
                Checked {lastChecked.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
            )}
            <button type="button" className="ai-status-refresh" onClick={fetchStatus}>
              Refresh
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
