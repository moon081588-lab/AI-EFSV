import React from 'react';

export default function ProtocolExecutionLog({ logs }) {
  if (!logs.length) return null;

  return (
    <div className="protocol-log-card">
      <div className="protocol-log-header">
        <h3>Live Protocol Action Log</h3>
        <span>{logs.length} trace events</span>
      </div>
      <div className="protocol-log-list">
        {logs.map((log, index) => (
          <div className="protocol-log-row" key={`${log.time}-${index}`}>
            <span className="log-time">[{log.time}]</span>
            <span className={`protocol-badge protocol-${String(log.protocol).toLowerCase().replace('/', '-')}`}>{log.protocol}</span>
            <span className={`direction-badge direction-${String(log.direction).toLowerCase()}`}>{log.direction}</span>
            <span className="log-id">ID: {log.id}</span>
            <code className="log-data">{log.data}</code>
            <span className="log-detail">{log.detail}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
