import React, { useState, useCallback } from 'react';
import { useTAISStream } from './hooks/useTAISStream';
import SwarmCanvas from './components/SwarmCanvas';
import MoteInspector from './components/MoteInspector';
import TeachingPanel from './components/TeachingPanel';
import AnalysisOverlay from './components/AnalysisOverlay';

const API_BASE = '';

export default function App() {
  const { connected, latest, stats, events, getMoteById, getEmergentStructures } = useTAISStream();
  const [selectedMoteId, setSelectedMoteId] = useState(null);
  const [playerMode, setPlayerMode] = useState('inspect');
  const [activeConcept, setActiveConcept] = useState('FOOD');
  const [activeChannel, setActiveChannel] = useState('SPEAK');
  const [playerPos, setPlayerPos] = useState({ x: 16, y: 16 });

  const selectedMote = selectedMoteId ? getMoteById(selectedMoteId) : null;
  const alerts = getEmergentStructures();

  const handleDemonstrate = useCallback(async (x, y, concept, channel) => {
    try {
      await fetch(`${API_BASE}/player/demonstrate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ concept, x, y, channel }),
      });
    } catch (e) {
      console.error('Demonstrate failed', e);
    }
  }, []);

  const handleInject = useCallback(async (moteId, concept) => {
    try {
      await fetch(`${API_BASE}/player/inject_concept`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mote_id: moteId, concept }),
      });
    } catch (e) {
      console.error('Inject failed', e);
    }
  }, []);

  const handleQuery = useCallback(async (moteId, concept) => {
    try {
      await fetch(`${API_BASE}/player/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mote_id: moteId, concept }),
      });
    } catch (e) {
      console.error('Query failed', e);
    }
  }, []);

  const handleMovePlayer = useCallback((x, y) => {
    setPlayerPos({ x, y });
  }, []);

  const modeClass = (mode) => (playerMode === mode ? 'mode-btn active' : 'mode-btn');

  return (
    <div className="app">
      <header className="app-header">
        <h1>TAIS V6 — Raw Substrate Inspector</h1>
        <div className="header-right">
          <div className={`status ${connected ? 'online' : 'offline'}`}>
            {connected ? '● SSE Live' : '○ Disconnected'}
          </div>
        </div>
      </header>

      <div className="stats-bar">
        <span className="stat-item">Tick: <strong>{stats.tick ?? latest?.tick ?? 0}</strong></span>
        <span className="stat-item">Population: <strong>{stats.population ?? latest?.population ?? 0}</strong></span>
        <span className="stat-item">Avg Energy: <strong>{stats.avgEnergy ?? '—'}</strong></span>
        <span className="stat-item">Avg Pred Acc: <strong>{stats.avgPredAcc ?? '—'}</strong></span>
        <span className="stat-item">Avg Causal Links: <strong>{stats.avgCausalLinks ?? '—'}</strong></span>
        <span className="stat-item">Plans: <strong>{stats.plansCreated ?? 0}</strong></span>
        <span className="stat-item">Grammar Rules: <strong>{stats.grammarRules ?? 0}</strong></span>
      </div>

      <div className="mode-row">
        <button className={modeClass('inspect')} onClick={() => setPlayerMode('inspect')}>Inspect</button>
        <button className={modeClass('move')} onClick={() => setPlayerMode('move')}>Move</button>
        <button className={modeClass('demonstrate')} onClick={() => setPlayerMode('demonstrate')}>Demonstrate</button>
      </div>

      <main className="app-main">
        <div className="left-col">
          <div className="canvas-pane">
            <SwarmCanvas
              state={latest}
              selectedMoteId={selectedMoteId}
              onSelectMote={setSelectedMoteId}
              playerMode={playerMode}
              activeConcept={activeConcept}
              activeChannel={activeChannel}
              onDemonstrate={handleDemonstrate}
              playerPos={playerPos}
              onMovePlayer={handleMovePlayer}
            />
            <AnalysisOverlay alerts={alerts} />
          </div>

          <div className="event-stream">
            <div className="event-stream-header">
              <span>Event Stream</span>
              <span className="event-count">{events.length} recent</span>
            </div>
            <div className="event-list">
              {events.length === 0 && <div className="event-empty">No events yet</div>}
              {events.map((ev, i) => (
                <div key={i} className={`event-item event-${ev.type?.toLowerCase() || 'unknown'}`}>
                  <span className="event-tick">T{ev.tick}</span>
                  <span className="event-type">{ev.type}</span>
                  {ev.mote_id !== undefined && <span className="event-mote">mote={ev.mote_id}</span>}
                  {ev.data?.concept && <span className="event-data">{ev.data.concept}</span>}
                  {ev.type === 'UTTERANCE' && ev.data?.content && (
                    <span className="event-data">"{ev.data.content}"</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="sidebar">
          <MoteInspector mote={selectedMote} />
          <TeachingPanel
            selectedMoteId={selectedMoteId}
            activeConcept={activeConcept}
            activeChannel={activeChannel}
            onSetConcept={setActiveConcept}
            onSetChannel={setActiveChannel}
            onDemonstrate={(id, c) => {
              setPlayerMode('demonstrate');
              setActiveConcept(c);
            }}
            onInject={handleInject}
            onQuery={handleQuery}
          />
          <div className="controls">
            <button onClick={() => fetch(`${API_BASE}/save`, { method: 'POST' })}>Save Colony</button>
            <button onClick={() => fetch(`${API_BASE}/reset`, { method: 'POST' })}>Reset</button>
          </div>
        </div>
      </main>
    </div>
  );
}
