import React, { useState } from 'react';

const CONCEPTS = ['GOOD', 'SOLVE', 'EVALUATE', 'VERIFY', 'REWRITE', 'SEARCH', 'NAVIGATE', 'LEARN'];

export default function TeachingPanel({
  onDemonstrate,
  onQuery,
}) {
  const [concept, setConcept] = useState('GOOD');
  const [mode, setMode] = useState('demonstrate');
  const [result, setResult] = useState(null);

  const handleDemonstrate = (c) => {
    setResult('Demonstrating...');
    onDemonstrate(c);
  };

  const handleQuery = async (c) => {
    setResult('Querying...');
    onQuery(c);
  };

  const handleInject = async (c) => {
    setResult('Injecting...');
    try {
      const r = await fetch('/player/inject_concept', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mote_id: null, concept: c }),
      });
      const data = await r.json();
      setResult(data.status === 'injected' ? `Injected "${c}"` : 'Inject failed');
    } catch {
      setResult('Inject failed');
    }
  };

  return (
    <div className="teaching-panel">
      <div className="panel-title">Grounded Teaching</div>

      <div className="mode-toggle">
        <button className={mode === 'demonstrate' ? 'active' : ''} onClick={() => setMode('demonstrate')}>
          Demonstrate
        </button>
        <button className={mode === 'inject' ? 'active' : ''} onClick={() => setMode('inject')}>
          Inject
        </button>
        <button className={mode === 'query' ? 'active' : ''} onClick={() => setMode('query')}>
          Query
        </button>
      </div>

      <div className="concept-grid">
        {CONCEPTS.map((c) => (
          <button
            key={c}
            className={`concept-btn ${concept === c ? 'active' : ''}`}
            onClick={() => {
              setConcept(c);
              if (mode === 'demonstrate') handleDemonstrate(c);
              if (mode === 'query') handleQuery(c);
              if (mode === 'inject') handleInject(c);
            }}
          >
            {c}
          </button>
        ))}
      </div>

      <div className="status-line">
        {mode === 'demonstrate' && <span>Demonstrate <b>{concept}</b> to the mote</span>}
        {mode === 'inject' && <span>Directly inject <b>{concept}</b> into causal model</span>}
        {mode === 'query' && <span>Query mote's causal belief about <b>{concept}</b></span>}
      </div>

      {result && (
        <div className="status-line" style={{ color: '#4ade80', marginTop: 4 }}>
          {result}
        </div>
      )}
    </div>
  );
}
