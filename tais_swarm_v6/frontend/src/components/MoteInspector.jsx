import React, { useState } from 'react';

const TABS = ['Overview', 'Metacognition', 'Causal', 'Planning', 'Lexicon', 'Trust'];

export default function MoteInspector({ mote }) {
  const [tab, setTab] = useState('Overview');

  if (!mote) {
    return (
      <div className="inspector">
        <div className="inspector-empty">Select a mote to inspect raw substrate state.</div>
      </div>
    );
  }

  return (
    <div className="inspector">
      <div className="inspector-header">
        <span className="mote-id">Mote {String(mote.id).slice(0, 8)}</span>
        <span className="mote-energy">⚡ {Math.round(mote.energy || 0)}</span>
      </div>

      <div className="tabs">
        {TABS.map((t) => (
          <button key={t} className={tab === t ? 'active' : ''} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>

      <div className="tab-content">
        {tab === 'Overview' && <OverviewTab mote={mote} />}
        {tab === 'Metacognition' && <MetaTab data={mote.metacognition} />}
        {tab === 'Causal' && <CausalTab data={mote.causal} />}
        {tab === 'Planning' && <PlanTab data={mote.planner} />}
        {tab === 'Lexicon' && <LexiconTab data={mote.lexicon} />}
        {tab === 'Trust' && <TrustTab data={mote.trust_vector} />}
      </div>
    </div>
  );
}

function OverviewTab({ mote }) {
  return (
    <div className="raw-panel">
      <div className="kv-row"><span>Position</span><span>({mote.x?.toFixed(1)}, {mote.y?.toFixed(1)})</span></div>
      <div className="kv-row"><span>Age</span><span>{mote.age}</span></div>
      <div className="kv-row"><span>Energy</span><span>{Math.round(mote.energy || 0)}</span></div>
      <div className="kv-row"><span>Genome</span><span>{JSON.stringify(mote.genome)}</span></div>
      <div className="kv-row"><span>Strategy</span><span>{mote.metacognition?.current_strategy || 'N/A'}</span></div>
      <div className="kv-row"><span>PredAcc</span><span>{(mote.metacognition?.prediction_accuracy || 0).toFixed(3)}</span></div>
    </div>
  );
}

function MetaTab({ data }) {
  if (!data) return <div className="raw-panel">No metacognition data.</div>;
  return (
    <div className="raw-panel">
      <div className="kv-row"><span>Strategy</span><span>{data.current_strategy}</span></div>
      <div className="kv-row"><span>Accuracy</span><span>{data.prediction_accuracy?.toFixed(3)}</span></div>
      <div className="kv-row"><span>Window</span><span>{JSON.stringify(data.prediction_window)}</span></div>
      <div className="kv-row"><span>Self-Model</span><span>{JSON.stringify(data.self_model)}</span></div>
      <div className="kv-row"><span>Domain Strategies</span><span>{JSON.stringify(data.domain_strategies)}</span></div>
    </div>
  );
}

function CausalTab({ data }) {
  if (!data || !data.links) return <div className="raw-panel">No causal model.</div>;
  return (
    <div className="raw-panel">
      <table className="raw-table">
        <thead>
          <tr><th>Action</th><th>Outcome</th><th>Δ-P</th><th>N</th></tr>
        </thead>
        <tbody>
          {Object.entries(data.links).map(([key, link]) => (
            <tr key={key}>
              <td>{link.action}</td>
              <td>{link.outcome}</td>
              <td>{link.strength?.toFixed(3)}</td>
              <td>{link.co_occurrences || 0}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PlanTab({ data }) {
  if (!data) return <div className="raw-panel">No planning data.</div>;
  return (
    <div className="raw-panel">
      <div className="kv-row"><span>Active Plan</span><span>{data.active_plan ? 'YES' : 'NONE'}</span></div>
      <div className="kv-row"><span>Library Size</span><span>{data.plan_library?.length || 0}</span></div>
      <div className="kv-row"><span>Plans Created</span><span>{data.stats?.plans_created || 0}</span></div>
      <div className="kv-row"><span>Completed</span><span>{data.stats?.plans_completed || 0}</span></div>
      <div className="kv-row"><span>Failed</span><span>{data.stats?.plans_failed || 0}</span></div>
      {data.active_plan?.steps && (
        <div className="plan-steps">
          <div className="subhead">Steps:</div>
          {data.active_plan.steps.map((s, i) => (
            <div key={i} className="step-row">
              {i}. {s.action} → {s.expected_outcome}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function LexiconTab({ data }) {
  if (!data || Object.keys(data).length === 0) return <div className="raw-panel">Empty lexicon.</div>;
  return (
    <div className="raw-panel">
      <table className="raw-table">
        <thead>
          <tr><th>Token</th><th>Concept</th><th>Conf</th><th>Grounded</th></tr>
        </thead>
        <tbody>
          {Object.entries(data).map(([token, entry]) => (
            <tr key={token}>
              <td><code>{token}</code></td>
              <td>{entry.concept}</td>
              <td>{entry.confidence?.toFixed(2)}</td>
              <td>{entry.grounded_count || 0}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TrustTab({ data }) {
  if (!data) return <div className="raw-panel">No trust data.</div>;
  return (
    <div className="raw-panel">
      <table className="raw-table">
        <thead>
          <tr><th>Mote</th><th>Score</th></tr>
        </thead>
        <tbody>
          {Object.entries(data).map(([id, score]) => (
            <tr key={id}>
              <td>{String(id).slice(0, 8)}</td>
              <td>{score.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
