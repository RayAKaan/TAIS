import React, { useRef, useEffect, useCallback, useState } from 'react';

const WORLD_SIZE = 64;
const COLORS = {
  bg: '#0a0a0f',
  grid: '#1a1a2e',
  food: '#22c55e',
  water: '#3b82f6',
  shelter: '#a16207',
  predator: '#ef4444',
  moteHigh: '#4ade80',
  moteMed: '#facc15',
  moteLow: '#f87171',
  utterance: '#e2e8f0',
  trustEdge: 'rgba(6,182,212,0.25)',
  selected: '#ffffff',
  player: '#818cf8',
  playerRing: 'rgba(129,140,248,0.4)',
  demonstrate: '#f472b6',
};

export default function SwarmCanvas({
  state,
  selectedMoteId,
  onSelectMote,
  playerMode,
  activeConcept,
  activeChannel,
  onDemonstrate,
  playerPos,
  onMovePlayer,
}) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const [hoveredMote, setHoveredMote] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  const toScreen = useCallback((x, y, w, h) => {
    const scaleX = w / WORLD_SIZE;
    const scaleY = h / WORLD_SIZE;
    return [x * scaleX, y * scaleY, scaleX, scaleY];
  }, []);

  const getMoteAt = useCallback((cx, cy) => {
    if (!state?.motes) return null;
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const scale = canvas.width / WORLD_SIZE;
    let nearest = null;
    let bestDist = Infinity;
    for (const m of state.motes) {
      const [sx, sy] = toScreen(m.x, m.y, canvas.width, canvas.height);
      const dx = sx + scale / 2 - cx;
      const dy = sy + scale / 2 - cy;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < scale * 1.2 && dist < bestDist) {
        bestDist = dist;
        nearest = m;
      }
    }
    return nearest;
  }, [state, toScreen]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !state) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;

    ctx.fillStyle = COLORS.bg;
    ctx.fillRect(0, 0, w, h);

    ctx.strokeStyle = COLORS.grid;
    ctx.lineWidth = 1;
    const step = w / WORLD_SIZE;
    for (let i = 0; i <= WORLD_SIZE; i++) {
      ctx.beginPath();
      ctx.moveTo(i * step, 0);
      ctx.lineTo(i * step, h);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, i * step);
      ctx.lineTo(w, i * step);
      ctx.stroke();
    }

    for (const r of state.resources || []) {
      const [sx, sy, ss] = toScreen(r.x, r.y, w, h);
      ctx.fillStyle = r.type === 'FOOD' ? COLORS.food : r.type === 'WATER' ? COLORS.water : COLORS.shelter;
      ctx.beginPath();
      ctx.arc(sx + ss / 2, sy + ss / 2, ss * 0.4, 0, Math.PI * 2);
      ctx.fill();
    }

    if (state.motes) {
      ctx.strokeStyle = COLORS.trustEdge;
      ctx.lineWidth = 1;
      for (const m of state.motes) {
        if (!m.trust_vector) continue;
        const [mx, my] = toScreen(m.x, m.y, w, h);
        for (const [otherId, score] of Object.entries(m.trust_vector)) {
          if (score < 0.5) continue;
          const other = state.motes.find((o) => o.id === otherId);
          if (!other) continue;
          const [ox, oy] = toScreen(other.x, other.y, w, h);
          ctx.beginPath();
          ctx.moveTo(mx + step / 2, my + step / 2);
          ctx.lineTo(ox + step / 2, oy + step / 2);
          ctx.stroke();
        }
      }
    }

    for (const m of state.motes || []) {
      const [sx, sy, ss] = toScreen(m.x, m.y, w, h);
      const energyRatio = Math.max(0, Math.min(1, (m.energy || 0) / 100));
      const color = energyRatio > 0.6 ? COLORS.moteHigh : energyRatio > 0.3 ? COLORS.moteMed : COLORS.moteLow;

      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(sx + ss / 2, sy + ss / 2, ss * 0.35, 0, Math.PI * 2);
      ctx.fill();

      if (m.id === selectedMoteId) {
        ctx.strokeStyle = COLORS.selected;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(sx + ss / 2, sy + ss / 2, ss * 0.45, 0, Math.PI * 2);
        ctx.stroke();
      }

      if (m.last_utterance && m.last_utterance_tick && state.tick - m.last_utterance_tick < 5) {
        ctx.fillStyle = COLORS.utterance;
        ctx.font = '10px monospace';
        ctx.textAlign = 'center';
        ctx.fillText(m.last_utterance, sx + ss / 2, sy - 4);
      }
    }

    for (const p of state.predators || []) {
      const [sx, sy, ss] = toScreen(p.x, p.y, w, h);
      ctx.fillStyle = COLORS.predator;
      ctx.beginPath();
      ctx.moveTo(sx + ss / 2, sy + ss * 0.1);
      ctx.lineTo(sx + ss * 0.9, sy + ss * 0.9);
      ctx.lineTo(sx + ss * 0.1, sy + ss * 0.9);
      ctx.closePath();
      ctx.fill();
    }

    if (playerPos) {
      const [px, py] = toScreen(playerPos.x, playerPos.y, w, h);
      ctx.fillStyle = COLORS.playerRing;
      ctx.beginPath();
      ctx.arc(px + step / 2, py + step / 2, step * 0.6, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = COLORS.player;
      ctx.beginPath();
      ctx.arc(px + step / 2, py + step / 2, step * 0.3, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = COLORS.selected;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(px + step / 2, py + step / 2, step * 0.3, 0, Math.PI * 2);
      ctx.stroke();
    }

    if (playerMode === 'demonstrate' && activeConcept) {
      ctx.fillStyle = COLORS.demonstrate;
      ctx.font = '12px monospace';
      ctx.textAlign = 'left';
      ctx.fillText(`DEMONSTRATE: ${activeConcept} [${activeChannel}]`, 10, 20);
    }
  }, [state, selectedMoteId, playerMode, activeConcept, activeChannel, toScreen, playerPos]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const resize = () => {
      const rect = container.getBoundingClientRect();
      canvas.width = rect.width;
      canvas.height = rect.height;
      draw();
    };

    resize();
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, [draw]);

  useEffect(() => {
    draw();
  }, [draw]);

  const canvasToWorld = useCallback((e) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const scale = canvas.width / WORLD_SIZE;
    return {
      cx: e.clientX - rect.left,
      cy: e.clientY - rect.top,
      wx: (e.clientX - rect.left) / scale,
      wy: (e.clientY - rect.top) / scale,
    };
  }, []);

  const handleClick = (e) => {
    const canvas = canvasRef.current;
    if (!canvas || !state) return;
    const { cx, cy, wx, wy } = canvasToWorld(e);

    if (playerMode === 'demonstrate' && activeConcept) {
      onDemonstrate(wx, wy, activeConcept, activeChannel);
      return;
    }

    if (playerMode === 'move') {
      onMovePlayer(wx, wy);
      return;
    }

    let nearest = null;
    let bestDist = Infinity;
    const scale = canvas.width / WORLD_SIZE;
    for (const m of state.motes || []) {
      const [sx, sy] = toScreen(m.x, m.y, canvas.width, canvas.height);
      const dx = sx + scale / 2 - cx;
      const dy = sy + scale / 2 - cy;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < scale * 0.8 && dist < bestDist) {
        bestDist = dist;
        nearest = m.id;
      }
    }
    onSelectMote(nearest);
  };

  const handleMouseMove = (e) => {
    const canvas = canvasRef.current;
    if (!canvas || !state) return;
    const { cx, cy } = canvasToWorld(e);
    const m = getMoteAt(cx, cy);
    if (m) {
      setHoveredMote(m);
      setTooltipPos({ x: e.clientX, y: e.clientY });
      canvas.style.cursor = 'pointer';
    } else {
      setHoveredMote(null);
      canvas.style.cursor = playerMode === 'demonstrate' ? 'crosshair' : playerMode === 'move' ? 'move' : 'default';
    }
  };

  const handleMouseLeave = () => {
    setHoveredMote(null);
  };

  const cursorStyle = playerMode === 'demonstrate' ? 'crosshair' : playerMode === 'move' ? 'move' : 'default';

  return (
    <div ref={containerRef} style={{ width: '100%', height: '100%', position: 'relative' }}>
      <canvas
        ref={canvasRef}
        onClick={handleClick}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        style={{ width: '100%', height: '100%', cursor: hoveredMote ? 'pointer' : cursorStyle }}
      />
      {hoveredMote && (
        <div
          className="tooltip"
          style={{
            left: tooltipPos.x - (containerRef.current?.getBoundingClientRect().left || 0) + 12,
            top: tooltipPos.y - (containerRef.current?.getBoundingClientRect().top || 0) - 10,
          }}
        >
          <div className="tooltip-header">Mote {hoveredMote.id}</div>
          <div className="tooltip-row">Energy: {Math.round(hoveredMote.energy || 0)}</div>
          <div className="tooltip-row">Intent: {hoveredMote.planner?.current_intent || 'idle'}</div>
          {hoveredMote.last_utterance && (
            <div className="tooltip-row">Utterance: "{hoveredMote.last_utterance}"</div>
          )}
          <div className="tooltip-row">Prediction Acc: {Math.round((hoveredMote.metacognition?.prediction_accuracy || 0) * 100)}%</div>
          {hoveredMote.genome?.strengths && (
            <div className="tooltip-row">Strengths: {Object.entries(hoveredMote.genome.strengths).map(([k, v]) => `${k}:${v}`).join(', ')}</div>
          )}
        </div>
      )}
    </div>
  );
}
