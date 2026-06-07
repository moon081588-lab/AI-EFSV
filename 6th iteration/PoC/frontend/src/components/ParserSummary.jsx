import React from 'react';

export default function ParserSummary({ parserInfo }) {
  const [isOpen, setIsOpen] = React.useState(false);

  if (!parserInfo) return null;

  const warnings = Array.isArray(parserInfo.warnings) ? parserInfo.warnings : [];
  const statusText = String(parserInfo.status || 'parsed').replaceAll('_', ' ');

  return (
    <section className="card parser-summary-card">
      <button className="parser-toggle-header" type="button" onClick={() => setIsOpen((current) => !current)}>
        <div>
          <h2>File Parsing Summary</h2>
          <p>The uploaded file was automatically inspected and normalized before verification analysis.</p>
        </div>
        <div className="parser-toggle-right">
          <span className="parser-status-pill">{statusText}</span>
          <span className="parser-toggle-icon">{isOpen ? 'Hide details' : 'Show details'}</span>
        </div>
      </button>

      {isOpen && (
        <div className="parser-summary-body">
          <div className="parser-info-grid">
            <div className="parser-info-item">
              <span>File Type</span>
              <strong>{parserInfo.fileType || 'N/A'}</strong>
            </div>
            <div className="parser-info-item">
              <span>Sheet / Source</span>
              <strong>{parserInfo.sheetName || 'N/A'}</strong>
            </div>
            <div className="parser-info-item">
              <span>Detected Header Row</span>
              <strong>{parserInfo.headerRow || 'N/A'}</strong>
            </div>
            <div className="parser-info-item">
              <span>Parsed Requirements</span>
              <strong>{parserInfo.parsedRequirements || 0}</strong>
            </div>
            <div className="parser-info-item">
              <span>Requirement ID Column</span>
              <strong>{parserInfo.requirementIdColumn || 'N/A'}</strong>
            </div>
            <div className="parser-info-item">
              <span>Requirement Text Column</span>
              <strong>{parserInfo.requirementTextColumn || 'N/A'}</strong>
            </div>
            <div className="parser-info-item">
              <span>ASIL Column</span>
              <strong>{parserInfo.asilColumn || 'N/A'}</strong>
            </div>
            <div className="parser-info-item">
              <span>Tables Scanned</span>
              <strong>{parserInfo.candidateTablesScanned || 1}</strong>
            </div>
          </div>

          {warnings.length > 0 && (
            <div className="parser-warning-box">
              <h3>Parser Notes</h3>
              <ul>
                {warnings.map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
