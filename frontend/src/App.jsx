import React, { useEffect, useRef, useState, useCallback } from 'react';
import MoteInspector from './components/MoteInspector.jsx';
import TeachingPanel from './components/TeachingPanel.jsx';

const API_BASE = '';

export default function App() {
  const [connected, setConnected] = useState(false);
  const [mote, setMote] = useState(null);
  const [events, setEvents] = useState([]);
  const [moteId, setMoteId] = useState(null);
  const [toast, setToast] = useState(null);
  const lastEventTick = useRef(0);
  const pollRef = useRef(null);

  const showToast = useCallback((msg, type = 'info') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

  useEffect(() => {
    const es = new EventSource(`${API_BASE}/stream`);
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    es.onmessage = (ev) => {
      try {
        const d = JSON.parse(ev.data);
        if (d.type === 'snapshot') {
          setMote(d.data);
          if (!moteId && d.data?.id) setMoteId(d.data.id);
        }
      } catch (e) {}
    };
    return () => es.close();
  }, [moteId]);

  useEffect(() => {
    const poll = async () => {
      try {
        const r = await fetch(`${API_BASE}/events?limit=50`);
        const data = await r.json();
        if (data.length) {
          const maxTick = Math.max(...data.map(e => e.tick));
          if (maxTick > lastEventTick.current) {
            lastEventTick.current = maxTick;
            setEvents(data.reverse());
          }
        }
      } catch (e) {}
    };
    poll();
    const iv = setInterval(poll, 1500);
    pollRef.current = iv;
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    if (!moteId) {
      fetch(`${API_BASE}/motes`)
        .then(r => r.json())
        .then(data => {
          if (data.length) setMoteId(data[0].id);
        })
        .catch(() => {});
    }
  }, [moteId]);

  const handleReset = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/mote/reset`, { method: 'POST' });
      const data = await r.json();
      setMoteId(data.new_id);
      showToast('Mote reset', 'info');
    } catch (e) {
      showToast('Reset failed', 'error');
    }
  }, [showToast]);

  const handleDemonstrate = useCallback(async (concept) => {
    try {
      await fetch(`${API_BASE}/player/demonstrate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ concept }),
      });
      showToast(`Demonstrated concept "${concept}"`, 'success');
    } catch (e) {
      showToast('Demonstrate failed', 'error');
    }
  }, [showToast]);

  const handleQuery = useCallback(async (concept) => {
    try {
      const r = await fetch(`${API_BASE}/player/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mote_id: moteId, concept }),
      });
      const data = await r.json();
      showToast(
        `Causal belief for "${concept}": ${data.causal_strength?.toFixed(3) ?? 'N/A'}`,
        'info'
      );
    } catch (e) {
      showToast('Query failed', 'error');
    }
  }, [moteId, showToast]);

  return (
    <div className="app">
      <header className="app-header">
        <h1>TAIS — Mote Inspector</h1>
        <div className="header-right">
          <div className={`status ${connected ? 'online' : 'offline'}`}>
            {connected ? '● SSE Live' : '○ Disconnected'}
          </div>
        </div>
      </header>

      <main className="app-main">
        <div className="left-col">
          <div className="event-feed">
            <div className="event-feed-header">
              <span>Event Stream</span>
              <span className="event-count">{events.length} recent</span>
            </div>
            <div className="event-list">
              {events.length === 0 && <div className="event-empty">No events yet</div>}
              {events.map((ev, i) => (
                <div key={i} className="event-item">
                  <span className="event-tick">T{ev.tick}</span>
                  <span className="event-type">{ev.type}</span>
                  <span className="event-data">
                    {ev.type === 'ACTION_TAKEN' ? ev.data?.action || ev.data?.name : ''}
                    {ev.type === 'TASK_SUCCESS' ? ev.data?.goal || 'Goal met' : ''}
                    {ev.type === 'MOTE_SPAWNED' ? `id=${ev.data?.mote_id}` : ''}
                    {ev.type === 'COUNTERFACTUAL' ? ev.data?.outcome : ''}
                    {![ 'ACTION_TAKEN', 'TASK_SUCCESS', 'MOTE_SPAWNED', 'COUNTERFACTUAL' ].includes(ev.type) ? JSON.stringify(ev.data) : ''}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="sidebar">
          <MoteInspector moteId={moteId} mote={mote} />
          <TeachingPanel
            onDemonstrate={handleDemonstrate}
            onQuery={handleQuery}
          />
          <div className="controls">
            <button onClick={handleReset}>Reset Mote</button>
          </div>
        </div>
      </main>

      {toast && (
        <div className={`toast ${toast.type}`}>
          {toast.msg}
        </div>
      )}
    </div>
  );
}
