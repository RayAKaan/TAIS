import React from 'react';

export default function AnalysisOverlay({ alerts }) {
  if (!alerts || alerts.length === 0) return null;

  return (
    <div className="analysis-overlay">
      <div className="overlay-title">Emergent Structure</div>
      <div className="alerts-list">
        {alerts.map((a, i) => (
          <div key={i} className={`alert alert-${a.severity}`}>
            <span className="alert-badge">{a.type}</span>
            <span className="alert-text">{a.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
