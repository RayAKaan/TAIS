import { useEffect, useRef, useState, useCallback } from 'react';

const API_BASE = '';

export function useTAISStream() {
  const [connected, setConnected] = useState(false);
  const [latest, setLatest] = useState(null);
  const [events, setEvents] = useState([]);
  const [stats, setStats] = useState({});
  const stateRef = useRef(null);
  const lastEventTick = useRef(0);

  // SSE stream for state snapshots
  useEffect(() => {
    const es = new EventSource(`${API_BASE}/stream`);
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    es.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data);
        stateRef.current = payload;
        setLatest(payload);
        // Compute aggregate stats from motes
        const motes = payload.motes || [];
        const alive = motes.filter((m) => m.alive);
        const avgEnergy = alive.length
          ? alive.reduce((s, m) => s + (m.energy || 0), 0) / alive.length
          : 0;
        const avgPredAcc = alive.length
          ? alive.reduce((s, m) => s + (m.metacognition?.prediction_accuracy || 0), 0) / alive.length
          : 0;
        const avgCausalLinks = alive.length
          ? alive.reduce((s, m) => s + Object.keys(m.causal?.links || {}).length, 0) / alive.length
          : 0;
        const plansCreated = motes.reduce((s, m) => s + (m.planner?.stats?.plans_created || 0), 0);
        setStats({
          tick: payload.tick,
          population: payload.population,
          avgEnergy: Math.round(avgEnergy * 10) / 10,
          avgPredAcc: Math.round(avgPredAcc * 1000) / 1000,
          avgCausalLinks: Math.round(avgCausalLinks * 10) / 10,
          plansCreated,
          grammarRules: payload.grammar_rules?.length || 0,
        });
      } catch (e) {}
    };
    return () => es.close();
  }, []);

  // Poll /events for conversation stream
  useEffect(() => {
    const poll = async () => {
      try {
        const r = await fetch(`${API_BASE}/events?limit=50`);
        const data = await r.json();
        if (data.length) {
          const maxTick = Math.max(...data.map((e) => e.tick));
          if (maxTick > lastEventTick.current) {
            lastEventTick.current = maxTick;
            setEvents(data.reverse());
          }
        }
      } catch (e) {}
    };
    poll();
    const iv = setInterval(poll, 1500);
    return () => clearInterval(iv);
  }, []);

  const getMoteById = useCallback((id) => {
    if (!stateRef.current?.motes) return null;
    return stateRef.current.motes.find((m) => m.id === id) || null;
  }, []);

  const getEmergentStructures = useCallback(() => {
    const state = stateRef.current;
    if (!state?.motes) return [];

    const alerts = [];
    const globalLexicon = {};

    for (const m of state.motes) {
      if (!m.lexicon) continue;
      for (const [token, entry] of Object.entries(m.lexicon)) {
        if (!globalLexicon[token]) globalLexicon[token] = {};
        const concept = entry.concept || 'UNKNOWN';
        globalLexicon[token][concept] = (globalLexicon[token][concept] || 0) + 1;
      }
    }

    for (const [token, concepts] of Object.entries(globalLexicon)) {
      const total = Object.values(concepts).reduce((a, b) => a + b, 0);
      const sorted = Object.entries(concepts).sort((a, b) => b[1] - a[1]);
      if (sorted[0][1] / total > 0.6 && total >= 3) {
        alerts.push({
          type: 'convergence',
          severity: 'info',
          text: `${sorted[0][1]} motes use "${token}" → ${sorted[0][0]}`,
        });
      }
      if (sorted.length > 1 && sorted[1][1] / total > 0.25) {
        alerts.push({
          type: 'polysemy',
          severity: 'warning',
          text: `"${token}" is polysemous: ${sorted[0][0]} (${sorted[0][1]}) vs ${sorted[1][0]} (${sorted[1][1]})`,
        });
      }
    }

    const trustEdges = [];
    for (const m of state.motes) {
      if (!m.trust_vector) continue;
      for (const [otherId, score] of Object.entries(m.trust_vector)) {
        if (score > 0.7) trustEdges.push({ from: m.id, to: otherId, score });
      }
    }
    if (trustEdges.length > 0) {
      alerts.push({ type: 'trust_cluster', severity: 'info', text: `${trustEdges.length} high-trust edges detected` });
    }
    if (state.grammar_rules && state.grammar_rules.length > 0) {
      alerts.push({ type: 'grammar', severity: 'success', text: `${state.grammar_rules.length} emergent grammar rule(s) discovered` });
    }
    return alerts;
  }, []);

  return { connected, latest, stats, events, getMoteById, getEmergentStructures };
}
