import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = '';
const TABS = ['Overview', 'Metacognition', 'Causal', 'Planning'];

async function fetchJSON(url) {
  try {
    const r = await fetch(url);
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}

export default function MoteInspector({ moteId, mote }) {
  const [tab, setTab] = useState('Overview');
  const [meta, setMeta] = useState(null);
  const [causal, setCausal] = useState(null);
  const [planning, setPlanning] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchTabData = useCallback(async (t) => {
    if (!moteId) return;
    setLoading(true);
    if (t === 'Metacognition') {
      const d = await fetchJSON(`${API_BASE}/motes/${moteId}/metacognition`);
      setMeta(d);
    } else if (t === 'Causal') {
      const d = await fetchJSON(`${API_BASE}/motes/${moteId}/causal`);
      setCausal(d);
    } else if (t === 'Planning') {
      const d = await fetchJSON(`${API_BASE}/motes/${moteId}/planning`);
      setPlanning(d);
    }
    setLoading(false);
  }, [moteId]);

  const handleTab = (t) => {
    setTab(t);
    if (t !== 'Overview') fetchTabData(t);
  };

  if (!mote) {
    return (
      <div className="inspector">
        <div className="inspector-empty">Waiting for mote data...</div>
      </div>
    );
  }

  return (
    <div className="inspector">
      <div className="inspector-header">
        <span className="mote-id">Mote #{mote.id}</span>
        <span>
          <span className="mote-energy">⚡ {Math.round(mote.energy || 0)}</span>
          {' '}
          <span className={mote.alive ? 'mote-alive' : 'mote-dead'}>
            {mote.alive ? '● Alive' : '● Dead'}
          </span>
        </span>
      </div>

      <div className="tabs">
        {TABS.map(t => (
          <button key={t} className={tab === t ? 'active' : ''} onClick={() => handleTab(t)}>
            {t}
          </button>
        ))}
      </div>

      <div className="tab-content">
        {loading && <div className="loading">Loading...</div>}
        {!loading && tab === 'Overview' && <OverviewTab mote={mote} />}
        {!loading && tab === 'Metacognition' && <MetaTab data={meta} />}
        {!loading && tab === 'Causal' && <CausalTab data={causal} />}
        {!loading && tab === 'Planning' && <PlanTab data={planning} />}
      </div>
    </div>
  );
}

function OverviewTab({ mote }) {
  return (
    <div className="raw-panel">
      <div className="overview-grid">
        <div className="overview-card">
          <div className="label">Age</div>
          <div className="value">{mote.age}</div>
        </div>
        <div className="overview-card">
          <div className="label">Actions</div>
          <div className="value">{mote.actions || 0}</div>
        </div>
        <div className="overview-card">
          <div className="label">Energy</div>
          <div className={`value ${(mote.energy || 0) > 500 ? 'good' : (mote.energy || 0) > 200 ? 'warn' : 'bad'}`}>
            {Math.round(mote.energy || 0)}
          </div>
        </div>
        <div className="overview-card">
          <div className="label">Reward</div>
          <div className={`value ${(mote.total_reward || 0) >= 0 ? 'good' : 'bad'}`}>
            {Math.round(mote.total_reward || 0)}
          </div>
        </div>
        <div className="overview-card">
          <div className="label">Prediction Error</div>
          <div className={mote.prediction_improving ? 'value good' : 'value bad'}>
            {mote.mean_prediction_error != null ? mote.mean_prediction_error.toFixed(3) : 'N/A'}
            <div style={{ fontSize: 10, color: mote.prediction_improving ? '#4ade80' : '#f87171' }}>
              {mote.prediction_improving ? '↓ Improving' : '↑ Not improving'}
            </div>
          </div>
        </div>
        <div className="overview-card">
          <div className="label">Invalid Actions</div>
          <div className={`value ${(mote.invalid_actions || 0) === 0 ? 'good' : 'bad'}`}>
            {mote.invalid_actions || 0}
          </div>
        </div>
      </div>

      <div className="subhead">Cognitive Engines</div>
      <div className="kv-row">
        <span>Metacognition Confidence</span>
        <span>{mote.metacog_confidence != null ? mote.metacog_confidence.toFixed(3) : 'N/A'}</span>
      </div>
      <div className="kv-row">
        <span>Exploration Rate</span>
        <span>{mote.metacog_exploration_rate != null ? mote.metacog_exploration_rate.toFixed(3) : 'N/A'}</span>
      </div>
      <div className="kv-row">
        <span>Causal Links</span>
        <span>{mote.causal_links_count || 0} ({mote.causal_is_causal_count || 0} causal)</span>
      </div>
      <div className="kv-row">
        <span>Active Plan</span>
        <span>{mote.planner_active_plan || 'None'}</span>
      </div>
      <div className="kv-row">
        <span>Plan Library</span>
        <span>{mote.planner_library_size || 0} plans</span>
      </div>

      <div className="subhead">Domains</div>
      <div className="domain-list">
        {(mote.domains || []).map(d => (
          <span key={d} className="domain-badge">{d}</span>
        ))}
        {(!mote.domains || mote.domains.length === 0) && <span className="domain-badge">none</span>}
      </div>

      <div className="subhead">Transfer Priors</div>
      <div className="kv-row">
        <span>Uses</span>
        <span>{mote.transfer_prior_uses || 0}</span>
      </div>
      <div className="kv-row">
        <span>Precision</span>
        <span>{(mote.transfer_prior_precision || 0).toFixed(3)}</span>
      </div>
      <div className="kv-row">
        <span>Correct / Incorrect</span>
        <span>{mote.transfer_prior_correct || 0} / {mote.transfer_prior_incorrect || 0}</span>
      </div>

      <div className="subhead">Memory</div>
      {mote.memory && (
        <>
          <div className="kv-row"><span>Patterns</span><span>{mote.memory.patterns || 0}</span></div>
          <div className="kv-row"><span>Episodes</span><span>{mote.memory.episodes || 0}</span></div>
        </>
      )}
    </div>
  );
}

function MetaTab({ data }) {
  if (!data) return <div className="raw-panel">No metacognition data.</div>;
  return (
    <div className="raw-panel">
      <div className="subhead">Self Model</div>
      {data.self_model && (
        <>
          <div className="kv-row"><span>Learning Speed</span><span>{data.self_model.learning_speed}</span></div>
          <div className="kv-row"><span>Memory Reliability</span><span>{data.self_model.memory_reliability}</span></div>
          <div className="kv-row"><span>Exploration Tendency</span><span>{data.self_model.exploration_tendency}</span></div>
          <div className="kv-row"><span>Planning Depth</span><span>{data.self_model.planning_depth}</span></div>
          <div className="kv-row"><span>Predictions</span><span>{data.self_model.prediction_count}</span></div>
        </>
      )}

      <div className="subhead">Prediction Tracker</div>
      {data.predictions && Object.keys(data.predictions).length > 0 ? (
        <table className="raw-table">
          <thead>
            <tr><th>Strategy</th><th>Accuracy</th><th>Samples</th></tr>
          </thead>
          <tbody>
            {Object.entries(data.predictions).map(([strategy, info]) => (
              <tr key={strategy}>
                <td><code>{strategy}</code></td>
                <td>{info.accuracy}</td>
                <td>{info.samples}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div style={{ color: '#64748b', padding: 4 }}>No predictions recorded</div>
      )}

      <div className="subhead">Strategy History (last 20)</div>
      {data.strategy_history && data.strategy_history.length > 0 ? (
        <table className="raw-table">
          <thead>
            <tr><th>Tick</th><th>Strategy</th><th>Urgency</th></tr>
          </thead>
          <tbody>
            {data.strategy_history.map(([tick, strategy, urgency], i) => (
              <tr key={i}>
                <td>{tick}</td>
                <td><code>{strategy}</code></td>
                <td>{urgency}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div style={{ color: '#64748b', padding: 4 }}>No strategy history</div>
      )}
    </div>
  );
}

function CausalTab({ data }) {
  if (!data) return <div className="raw-panel">No causal model.</div>;
  const links = data.links || [];
  return (
    <div className="raw-panel">
      <div className="kv-row"><span>Event Count</span><span>{data.event_count || 0}</span></div>

      <div className="subhead">Causal Links</div>
      {links.length > 0 ? (
        <table className="raw-table">
          <thead>
            <tr><th>Outcome</th><th>Δ-P</th><th>Conf</th><th>Samples</th><th>Causal?</th></tr>
          </thead>
          <tbody>
            {links.map((link, i) => (
              <tr key={i}>
                <td><code>{link.outcome}</code></td>
                <td>{(link.delta_p || 0).toFixed(3)}</td>
                <td>{(link.confidence || 0).toFixed(3)}</td>
                <td>{link.sample_count || 0}</td>
                <td>{link.is_causal ? '✓' : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div style={{ color: '#64748b', padding: 4 }}>No causal links yet</div>
      )}

      {data.counterfactuals && data.counterfactuals.length > 0 && (
        <>
          <div className="subhead">Counterfactuals (last 10)</div>
          <table className="raw-table">
            <thead>
              <tr><th>Action</th><th>Outcome</th><th>Expected</th><th>Counterfactual</th></tr>
            </thead>
            <tbody>
              {data.counterfactuals.map((cf, i) => (
                <tr key={i}>
                  <td><code>{cf.action}</code></td>
                  <td>{cf.outcome}</td>
                  <td>{(cf.expected || 0).toFixed(3)}</td>
                  <td>{(cf.counterfactual || 0).toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

function PlanTab({ data }) {
  if (!data) return <div className="raw-panel">No planning data.</div>;
  return (
    <div className="raw-panel">
      <div className="kv-row"><span>Active Plan</span><span>{data.active_plan ? 'YES' : 'NONE'}</span></div>
      <div className="kv-row"><span>Library Size</span><span>{Object.keys(data.plan_library || {}).length || 0}</span></div>
      <div className="kv-row"><span>History</span><span>{(data.history || []).length} entries</span></div>

      {data.active_plan && (
        <>
          <div className="subhead">Active Plan</div>
          <div className="kv-row"><span>Goal</span><span><code>{data.active_plan.goal}</code></span></div>
          <div className="kv-row"><span>Utility</span><span>{(data.active_plan.expected_utility || 0).toFixed(3)}</span></div>
          <div className="kv-row"><span>Created</span><span>Tick {data.active_plan.tick_created}</span></div>
          <div className="kv-row"><span>Step</span><span>{data.active_plan.current_step || 0} / {(data.active_plan.steps || []).length}</span></div>
          {data.active_plan.steps && data.active_plan.steps.length > 0 && (
            <div className="plan-steps">
              <div className="subhead">Steps:</div>
              {data.active_plan.steps.map((s, i) => (
                <div key={i} className="step-row">
                  {i}. <code>{s.action}</code> → {s.expected_outcome}
                  {s.target_concept && s.target_concept !== s.expected_outcome && ` (${s.target_concept})`}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {data.plan_library && Object.keys(data.plan_library).length > 0 && (
        <>
          <div className="subhead">Plan Library</div>
          {Object.entries(data.plan_library).map(([goal, plans]) => (
            <div key={goal} style={{ marginBottom: 6 }}>
              <div style={{ color: '#38bdf8', fontSize: 11 }}>Goal: <code>{goal}</code></div>
              {plans.map((plan, i) => (
                <div key={i} className="kv-row" style={{ paddingLeft: 8 }}>
                  <span>Plan #{i + 1}</span>
                  <span style={{ color: '#94a3b8' }}>
                    {plan.steps?.length || 0} steps, utility={(plan.expected_utility || 0).toFixed(3)},
                    success rate={(plan.success_rate || 0).toFixed(3)}
                  </span>
                </div>
              ))}
            </div>
          ))}
        </>
      )}

      {data.history && data.history.length > 0 && (
        <>
          <div className="subhead">History (last 20)</div>
          <table className="raw-table">
            <thead>
              <tr><th>Tick</th><th>Goal</th><th>Success</th></tr>
            </thead>
            <tbody>
              {data.history.map(([tick, goal, success], i) => (
                <tr key={i}>
                  <td>{tick}</td>
                  <td><code>{goal}</code></td>
                  <td style={{ color: success ? '#4ade80' : '#f87171' }}>{success ? '✓' : '✗'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
