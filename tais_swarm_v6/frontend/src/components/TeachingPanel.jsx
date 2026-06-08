import React from 'react';

const CONCEPTS = ['FOOD', 'WATER', 'PREDATOR', 'SHELTER', 'SAFE', 'COME', 'GO'];
const CHANNELS = ['WHISPER', 'SPEAK', 'SHOUT'];

export default function TeachingPanel({
  selectedMoteId,
  activeConcept,
  activeChannel,
  onSetConcept,
  onSetChannel,
  onDemonstrate,
  onInject,
  onQuery,
}) {
  const [localConcept, setLocalConcept] = React.useState('FOOD');
  const [localChannel, setLocalChannel] = React.useState('SPEAK');
  const [mode, setMode] = React.useState('demonstrate');

  const concept = activeConcept ?? localConcept;
  const channel = activeChannel ?? localChannel;
  const handleSetConcept = onSetConcept || setLocalConcept;
  const handleSetChannel = onSetChannel || setLocalChannel;

  return (
    <div className="teaching-panel">
      <div className="panel-title">Grounded Teaching</div>

      <div className="mode-toggle">
        <button className={mode === 'demonstrate' ? 'active' : ''} onClick={() => setMode('demonstrate')}>
          Demonstrate
        </button>
        <button className={mode === 'direct' ? 'active' : ''} onClick={() => setMode('direct')}>
          Direct Inject
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
              handleSetConcept(c);
              if (mode === 'demonstrate') onDemonstrate?.(null, c);
            }}
          >
            {c}
          </button>
        ))}
      </div>

      <div className="channel-row">
        {CHANNELS.map((ch) => (
          <button
            key={ch}
            className={channel === ch ? 'active' : ''}
            onClick={() => handleSetChannel(ch)}
          >
            {ch}
          </button>
        ))}
      </div>

      <div className="status-line">
        {mode === 'demonstrate' && (
          <span>Click on canvas to emit <b>{concept}</b> via <b>{channel}</b></span>
        )}
        {mode === 'direct' && (
          <span>
            Send <b>{concept}</b> to {selectedMoteId ? String(selectedMoteId).slice(0, 8) : 'NO MOTE SELECTED'}
          </span>
        )}
        {mode === 'query' && (
          <span>Query {selectedMoteId ? String(selectedMoteId).slice(0, 8) : 'NO MOTE'} for <b>{concept}</b></span>
        )}
      </div>

      {mode === 'direct' && selectedMoteId && (
        <button className="action-btn" onClick={() => onInject(selectedMoteId, concept)}>
          INJECT CONCEPT
        </button>
      )}

      {mode === 'query' && selectedMoteId && (
        <button className="action-btn" onClick={() => onQuery(selectedMoteId, concept)}>
          SEND QUERY
        </button>
      )}
    </div>
  );
}
