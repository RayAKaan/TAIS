import { useCallback, useEffect, useMemo, useRef, useState } from "react";

const SERVER = "http://localhost:5124";
const GRID = 8;
const CELL = 96;
const W = GRID * CELL;

const C = {
  bg: "#08080d",
  surface: "#111118",
  panel: "#0f0f17",
  border: "#242438",
  muted: "#3a3a55",
  text: "#d0d0e8",
  textDim: "#66668e",
  accent: "#4a9eff",
  accentDim: "#17345f",
  peak: "#1D9E75",
  predator: "#E24B4A",
  player: "#EF9F27",
  speech: "#8a7aff",
  directed: "#4a9eff",
  silence: "#50506d",
  teaching: "#35d399",
  birth: "#1D9E75",
  death: "#ff4a4a",
  stone: "#b8860b",
  stoneDim: "#5c4420",
};

function energyColor(e = 0) {
  if (e > 120) return "#4aff9e";
  if (e > 80) return "#4a9eff";
  if (e > 50) return "#9e7aff";
  if (e > 25) return "#ff9e4a";
  return "#ff4a4a";
}

function eventStyle(type, ev = {}) {
  if (type === "player") return { color: C.player, prefix: "\u25B6" };
  if (type === "teaching") return { color: C.teaching, prefix: "\u25C6" };
  if (type === "utterance") return { color: ev.target_id ? C.directed : C.speech, prefix: ev.target_id ? "\u2192" : "\u25CC" };
  if (type === "silence") return { color: C.silence, prefix: "\u2205" };
  if (type === "birth") return { color: C.birth, prefix: "\u25C9" };
  if (type === "death") return { color: C.death, prefix: "\u00D7" };
  if (type === "stone_drop") return { color: C.stone, prefix: "\u25C8" };
  if (type === "stone_read") return { color: C.stone, prefix: "\u2606" };
  if (type === "system") return { color: C.textDim, prefix: "\u00B7" };
  return { color: C.text, prefix: "\u00B7" };
}

function Tiny({ children, color = C.textDim }) {
  return <span style={{ fontSize: 11, color }}>{children}</span>;
}

function Stat({ label, value, color }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontSize: 20, fontWeight: 600, color: color || C.text, fontFamily: "monospace" }}>{value}</div>
      <div style={{ fontSize: 10, color: C.textDim, textTransform: "uppercase", letterSpacing: "0.08em" }}>{label}</div>
    </div>
  );
}

function MoteTooltip({ mote }) {
  const lex = mote.top_lexicon || {};
  const lexItems = Object.entries(lex).slice(0, 6);
  const dirRatio = mote.spoke ? Math.round((mote.directed / mote.spoke) * 100) : 0;
  return (
    <div
      style={{
        position: "absolute",
        pointerEvents: "none",
        background: C.surface,
        border: `1px solid ${C.border}`,
        borderRadius: 6,
        padding: "10px 12px",
        fontSize: 12,
        color: C.text,
        lineHeight: 1.7,
        zIndex: 100,
        whiteSpace: "nowrap",
        boxShadow: "0 4px 20px rgba(0,0,0,0.65)",
        minWidth: 220,
      }}
    >
      <div style={{ color: C.accent, fontWeight: 600, marginBottom: 4 }}>Mote #{mote.id}</div>
      <div>energy <span style={{ color: energyColor(mote.energy) }}>{mote.energy}</span> &middot; fitness <span style={{ color: C.peak }}>{mote.fitness}</span></div>
      <div>intent <span style={{ color: C.speech }}>{mote.last_intent}</span> &middot; predator {mote.pred_dist}</div>
      <div>spoke {mote.spoke} &middot; directed <span style={{ color: C.accent }}>{dirRatio}%</span> &middot; broadcast {mote.broadcast}</div>
      <div>silence choice {mote.silent_choice} &middot; fear <span style={{ color: C.predator }}>{mote.silent_fear}</span></div>
      <div>grammar <span style={{ color: C.textDim }}>{mote.genome?.order}</span> &middot; max {mote.genome?.max_len}</div>
      <div>updates <span style={{ color: C.teaching }}>{mote.lexicon_updates}</span></div>
      <div>memory <span style={{ color: C.stone }}>{mote.memory_size} entries</span></div>
      {mote.recent_utterances?.length > 0 && (
        <div style={{ marginTop: 4 }}>
          recent: <span style={{ color: C.speech }}>{mote.recent_utterances.join(" \u00B7 ")}</span>
        </div>
      )}
      {lexItems.length > 0 && (
        <div style={{ marginTop: 5, borderTop: `1px solid ${C.border}`, paddingTop: 4 }}>
          {lexItems.map(([tok, obj]) => (
            <div key={tok}><span style={{ color: C.teaching }}>{tok}</span> &asymp; {obj.concept} <span style={{ color: C.textDim }}>{obj.weight}</span></div>
          ))}
        </div>
      )}
    </div>
  );
}

function SwarmGrid({ state, playerPos, hoveredMote, setHoveredMote, onGridClick, mode }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !state) return;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, W, W);
    ctx.fillStyle = C.bg;
    ctx.fillRect(0, 0, W, W);

    ctx.strokeStyle = C.border;
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= GRID; i++) {
      ctx.beginPath(); ctx.moveTo(i * CELL, 0); ctx.lineTo(i * CELL, W); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, i * CELL); ctx.lineTo(W, i * CELL); ctx.stroke();
    }

    if (state.peaks) {
      state.peaks.forEach((peak) => {
        const gx = (peak.x / GRID) * W;
        const gy = (peak.y / GRID) * W;
        const r = (peak.s / 10) * CELL * 2.2;
        const grad = ctx.createRadialGradient(gx, gy, 0, gx, gy, r);
        grad.addColorStop(0, "rgba(29,158,117,0.14)");
        grad.addColorStop(0.55, "rgba(29,158,117,0.045)");
        grad.addColorStop(1, "rgba(0,0,0,0)");
        ctx.fillStyle = grad;
        ctx.beginPath(); ctx.arc(gx, gy, r, 0, Math.PI * 2); ctx.fill();
      });
    }

    if (state.stones) {
      state.stones.forEach((stone) => {
        const sx = (stone.x / GRID) * W;
        const sy = (stone.y / GRID) * W;
        ctx.fillStyle = C.stoneDim;
        ctx.beginPath();
        const s = 4;
        ctx.moveTo(sx, sy - s);
        ctx.lineTo(sx + s * 1.2, sy + s * 0.6);
        ctx.lineTo(sx, sy + s * 1.2);
        ctx.lineTo(sx - s * 1.2, sy + s * 0.6);
        ctx.closePath(); ctx.fill();
        ctx.fillStyle = C.stone;
        ctx.beginPath();
        ctx.arc(sx, sy - s * 0.3, 2.5, 0, Math.PI * 2);
        ctx.fill();
      });
    }

    if (state.recent_utterances) {
      state.recent_utterances.slice(-25).forEach((u) => {
        if (u.is_player) return;
        const x = (u.position[0] / GRID) * W;
        const y = (u.position[1] / GRID) * W;
        ctx.strokeStyle = u.is_broadcast ? "rgba(138,122,255,0.16)" : "rgba(74,158,255,0.20)";
        ctx.lineWidth = u.is_broadcast ? 1.2 : 1.8;
        ctx.beginPath();
        ctx.arc(x, y, u.is_broadcast ? 18 : 10, 0, Math.PI * 2);
        ctx.stroke();
      });
    }

    if (state.predators) {
      state.predators.forEach((p) => {
        const px = (p.x / GRID) * W;
        const py = (p.y / GRID) * W;
        const tx = (p.target_x / GRID) * W;
        const ty = (p.target_y / GRID) * W;
        ctx.strokeStyle = "rgba(226,75,74,0.18)";
        ctx.setLineDash([4, 4]);
        ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(tx, ty); ctx.stroke();
        ctx.setLineDash([]);
        ctx.strokeStyle = "rgba(226,75,74,0.13)";
        ctx.lineWidth = 1;
        ctx.beginPath(); ctx.arc(px, py, (2.2 / GRID) * W, 0, Math.PI * 2); ctx.stroke();
        ctx.fillStyle = C.predator;
        ctx.beginPath();
        ctx.moveTo(px, py - 10);
        ctx.lineTo(px + 9, py + 7);
        ctx.lineTo(px - 9, py + 7);
        ctx.closePath(); ctx.fill();
      });
    }

    if (state.motes) {
      state.motes.forEach((m) => {
        const mx = (m.x / GRID) * W;
        const my = (m.y / GRID) * W;
        const r = Math.max(3, Math.min(8, 4 + m.energy / 55));
        const col = energyColor(m.energy);
        if (hoveredMote?.id === m.id) {
          ctx.strokeStyle = col;
          ctx.setLineDash([3, 3]);
          ctx.beginPath(); ctx.arc(mx, my, (2.8 / GRID) * W, 0, Math.PI * 2); ctx.stroke();
          ctx.setLineDash([]);
        }
        if (m.last_intent === "PREDATOR" || m.silent_fear > 0) {
          ctx.strokeStyle = "rgba(226,75,74,0.22)";
          ctx.beginPath(); ctx.arc(mx, my, r + 7, 0, Math.PI * 2); ctx.stroke();
        }
        ctx.fillStyle = col + "33";
        ctx.beginPath(); ctx.arc(mx, my, r + 2, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = col;
        ctx.beginPath(); ctx.arc(mx, my, r, 0, Math.PI * 2); ctx.fill();
        if ((m.recent_utterances || []).length > 0) {
          ctx.fillStyle = C.textDim;
          ctx.font = "10px monospace";
          ctx.textAlign = "center";
          ctx.fillText(m.recent_utterances.at(-1), mx, my - r - 4);
        }
      });
    }

    const ppx = (playerPos.x / GRID) * W;
    const ppy = (playerPos.y / GRID) * W;
    ctx.strokeStyle = "rgba(239,159,39,0.24)";
    ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.arc(ppx, ppy, (3.2 / GRID) * W, 0, Math.PI * 2); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = C.player;
    ctx.strokeStyle = C.bg;
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(ppx, ppy, 10, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.fillStyle = C.bg;
    ctx.font = "bold 10px monospace";
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText(mode === "teach" ? "T" : mode === "speak" ? "S" : "Y", ppx, ppy);
    ctx.textBaseline = "alphabetic";
  }, [state, playerPos, hoveredMote, mode]);

  const mouseMove = useCallback((e) => {
    if (!state?.motes) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * GRID;
    const y = ((e.clientY - rect.top) / rect.height) * GRID;
    let closest = null;
    let best = 0.45;
    state.motes.forEach((m) => {
      const d = Math.sqrt((m.x - x) ** 2 + (m.y - y) ** 2);
      if (d < best) { best = d; closest = m; }
    });
    setHoveredMote(closest);
  }, [state, setHoveredMote]);

  const click = useCallback((e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * GRID;
    const y = ((e.clientY - rect.top) / rect.height) * GRID;
    onGridClick(x, y);
  }, [onGridClick]);

  return (
    <div style={{ position: "relative" }}>
      <canvas ref={canvasRef} width={W} height={W} onMouseMove={mouseMove} onMouseLeave={() => setHoveredMote(null)} onClick={click}
        style={{ display: "block", cursor: "crosshair", borderRadius: 4, border: `1px solid ${C.border}` }} />
      {hoveredMote && (
        <div style={{ position: "absolute", left: Math.min((hoveredMote.x / GRID) * W + 12, W - 250), top: Math.max((hoveredMote.y / GRID) * W - 95, 0) }}>
          <MoteTooltip mote={hoveredMote} />
        </div>
      )}
    </div>
  );
}

function EventRow({ ev }) {
  const st = eventStyle(ev.type, ev);
  const isSilence = ev.type === "silence";
  const label = ev.type === "teaching" ? `taught ${ev.text || ev.tokens?.join(" ")} \u2248 ${ev.concept}`
    : ev.type === "stone_drop" ? `stone at (${ev.x}, ${ev.y})`
    : ev.type === "stone_read" ? `read stone, +${ev.learned} words`
    : isSilence ? `[${ev.silence_reason || "silence"}]`
    : ev.text || ev.tokens?.join(" ") || "";
  return (
    <div style={{ padding: "7px 10px", borderBottom: `1px solid ${C.border}`, display: "flex", gap: 8, alignItems: "flex-start", opacity: isSilence ? 0.55 : 1 }}>
      <span style={{ color: st.color, fontSize: 13, flexShrink: 0 }}>{st.prefix}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <span style={{ color: C.textDim, fontSize: 11, marginRight: 6 }}>#{ev.mote_id ?? "you"}</span>
        <span style={{ color: st.color, fontSize: 13 }}>{label}</span>
        {ev.intent && ev.type !== "teaching" && <span style={{ color: C.textDim, fontSize: 10, marginLeft: 8 }}>({ev.intent})</span>}
        {ev.target_id && <span style={{ color: C.directed, fontSize: 10, marginLeft: 8 }}>\u2192#{ev.target_id}</span>}
      </div>
      {ev.energy !== undefined && <span style={{ color: energyColor(ev.energy), fontSize: 10, marginTop: 2 }}>{ev.energy}</span>}
    </div>
  );
}

export default function App() {
  const [state, setState] = useState(null);
  const [connected, setConnected] = useState(false);
  const [playerPos, setPlayerPos] = useState({ x: 4, y: 4 });
  const [events, setEvents] = useState([]);
  const [hoveredMote, setHoveredMote] = useState(null);
  const [mode, setMode] = useState("move");
  const [text, setText] = useState("lum");
  const [teachWord, setTeachWord] = useState("food");
  const [concept, setConcept] = useState("FOOD_HIGH");
  const [claimFitness, setClaimFitness] = useState(8.0);
  const lastTick = useRef(-1);
  const scrollRef = useRef(null);

  useEffect(() => {
    const es = new EventSource(`${SERVER}/stream`);
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        setState(data);
        if (data.player) setPlayerPos({ x: data.player.x, y: data.player.y });
        if (data.events && data.tick !== lastTick.current) {
          lastTick.current = data.tick;
          const newEvents = data.events.filter((ev) => ev.tick >= data.tick - 1);
          if (newEvents.length) setEvents((prev) => [...prev, ...newEvents].slice(-180));
        }
      } catch (err) {
        console.warn(err);
      }
    };
    return () => es.close();
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  const sendMove = useCallback(async (x, y) => {
    const cx = Math.max(0, Math.min(GRID, x));
    const cy = Math.max(0, Math.min(GRID, y));
    setPlayerPos({ x: cx, y: cy });
    await fetch(`${SERVER}/player/move`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ x: cx, y: cy }) });
    setEvents((prev) => [...prev, { type: "player", mote_id: null, text: `moved (${cx.toFixed(1)}, ${cy.toFixed(1)})`, tick: state?.tick ?? 0 }]);
  }, [state]);

  const sendSpeak = useCallback(async (x = playerPos.x, y = playerPos.y, teaching = false) => {
    const body = { text, concept: teaching ? concept : undefined, teaching, fitness: claimFitness, x, y };
    await fetch(`${SERVER}/player/speak`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    setEvents((prev) => [...prev, { type: "player", mote_id: null, text: `${text} [fit=${claimFitness.toFixed(1)}]`, intent: teaching ? concept : undefined, tick: state?.tick ?? 0 }]);
  }, [text, concept, claimFitness, playerPos, state]);

  const sendTeach = useCallback(async () => {
    await fetch(`${SERVER}/player/teach`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ word: teachWord, concept }) });
    setEvents((prev) => [...prev, { type: "teaching", mote_id: null, text: teachWord, concept, tick: state?.tick ?? 0 }]);
  }, [teachWord, concept, state]);

  const onGridClick = useCallback((x, y) => {
    if (mode === "move") sendMove(x, y);
    else if (mode === "speak") sendSpeak(Math.max(0, Math.min(GRID, x)), Math.max(0, Math.min(GRID, y)), false);
    else sendMove(x, y);
  }, [mode, sendMove, sendSpeak]);

  const reset = async () => {
    await fetch(`${SERVER}/reset`, { method: "POST" });
    setEvents([{ type: "system", text: "reset", tick: 0 }]);
  };

  const concepts = state?.concepts || ["FOOD_HIGH", "PREDATOR", "SAFE", "SHELTER", "WATER"];
  const stats = state?.stats || {};
  const dirPct = Math.round((stats.directed_ratio || 0) * 100);
  const totalLex = stats.lexicon_updates || 0;
  const stones = state?.stones || [];

  const knownWords = useMemo(() => {
    const counts = {};
    state?.motes?.forEach((m) => Object.keys(m.top_lexicon || {}).forEach((t) => counts[t] = (counts[t] || 0) + 1));
    return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 10);
  }, [state]);

  return (
    <div style={{ background: C.bg, height: "100vh", color: C.text, fontFamily: "monospace", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <div style={{ background: C.surface, borderBottom: `1px solid ${C.border}`, padding: "12px 20px", display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0 }}>
        <div>
          <span style={{ color: C.accent, fontWeight: 700, fontSize: 16 }}>TAIS-LANG v4</span>
          <span style={{ color: C.textDim, marginLeft: 10, fontSize: 12 }}>world &middot; memory &middot; reference</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <span style={{ color: connected ? C.peak : C.predator, fontSize: 11 }}>{connected ? "\u25CF LIVE" : "\u25CB OFFLINE"}</span>
          <Tiny>tick {state?.tick ?? 0} &middot; pop {state?.population ?? 0} &middot; stones {stones.length}</Tiny>
          <button onClick={reset} style={buttonStyle(false)}>reset</button>
        </div>
      </div>

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <div style={{ flexShrink: 0, padding: 16, display: "flex", flexDirection: "column", gap: 10, overflowY: "auto" }}>
          <SwarmGrid state={state} playerPos={playerPos} hoveredMote={hoveredMote} setHoveredMote={setHoveredMote} onGridClick={onGridClick} mode={mode} />

          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
            {["move", "speak", "teach"].map((m) => <button key={m} onClick={() => setMode(m)} style={buttonStyle(mode === m, true)}>{m}</button>)}
          </div>

          <div style={panelStyle}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <Tiny color={C.player}>speak</Tiny>
              <input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && sendSpeak()} style={inputStyle} />
              <button onClick={() => sendSpeak()} style={buttonStyle(false)}>send</button>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <Tiny>fitness</Tiny>
              <input type="range" min="0" max="12" step="0.5" value={claimFitness} onChange={(e) => setClaimFitness(parseFloat(e.target.value))} style={{ flex: 1 }} />
              <span style={{ color: C.peak, width: 30, fontSize: 12 }}>{claimFitness.toFixed(1)}</span>
            </div>
          </div>

          <div style={panelStyle}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Tiny color={C.teaching}>teach</Tiny>
              <input value={teachWord} onChange={(e) => setTeachWord(e.target.value)} style={{ ...inputStyle, flex: 0.8 }} />
              <select value={concept} onChange={(e) => setConcept(e.target.value)} style={selectStyle}>
                {concepts.map((c) => <option key={c}>{c}</option>)}
              </select>
              <button onClick={sendTeach} style={buttonStyle(false)}>ground</button>
            </div>
            <div style={{ marginTop: 7, color: C.textDim, fontSize: 11 }}>Grounds your word in nearby motes' private lexicons.</div>
          </div>

          <div style={{ ...panelStyle, display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8 }}>
            <Stat label="direct" value={`${dirPct}%`} color={C.directed} />
            <Stat label="spoke" value={stats.spoke || 0} color={C.speech} />
            <Stat label="silent" value={stats.choice_silence || 0} color={C.silence} />
            <Stat label="fear\u2205" value={stats.fear_silence || 0} color={C.predator} />
            <Stat label="lex" value={totalLex} color={C.teaching} />
          </div>

          <div style={panelStyle}>
            <div style={{ color: C.textDim, fontSize: 11, marginBottom: 5 }}>common grounded tokens</div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {knownWords.length === 0 && <Tiny>none yet \u2014 teach or wait</Tiny>}
              {knownWords.map(([tok, n]) => <span key={tok} style={{ color: C.teaching, border: `1px solid ${C.border}`, padding: "2px 6px", borderRadius: 3, fontSize: 11 }}>{tok}\u00D7{n}</span>)}
            </div>
          </div>

          <div style={{ ...panelStyle, color: C.textDim, fontSize: 11, lineHeight: 1.6 }}>
            Motes remember events, inherit memories, drop stone markers, and read stones to learn.
          </div>
        </div>

        <div style={{ flex: 1, display: "flex", flexDirection: "column", borderLeft: `1px solid ${C.border}`, overflow: "hidden", minWidth: 320 }}>
          <div style={{ background: C.surface, borderBottom: `1px solid ${C.border}`, padding: "10px 14px", display: "flex", justifyContent: "space-between", flexShrink: 0 }}>
            <Tiny>conversation stream &middot; speech, stones, memory</Tiny>
            <Tiny color={C.player}>({playerPos.x.toFixed(1)}, {playerPos.y.toFixed(1)}) fit {state?.player?.fitness?.toFixed?.(2) ?? "\u2013"}</Tiny>
          </div>
          <div ref={scrollRef} style={{ flex: 1, overflowY: "auto" }}>
            {events.length === 0 && <div style={{ padding: 30, textAlign: "center", color: C.textDim, fontSize: 12 }}>No speech yet. Move near motes, teach a word, or send a sound.</div>}
            {events.map((ev, i) => <EventRow key={`${ev.tick}-${ev.type}-${ev.mote_id}-${i}`} ev={ev} />)}
          </div>
          <div style={{ borderTop: `1px solid ${C.border}`, padding: "7px 12px", background: C.surface, display: "flex", gap: 16, fontSize: 10, color: C.textDim, flexShrink: 0 }}>
            <span>\u25CC broadcast</span><span>\u2192 directed</span><span>\u2205 silence</span><span>\u25C6 teaching</span><span style={{ color: C.stone }}>\u25C8 stone</span>
          </div>
        </div>
      </div>

      {!connected && <div style={{ color: C.predator, background: "rgba(226,75,74,0.1)", borderTop: `1px solid ${C.predator}`, padding: 8, textAlign: "center", fontSize: 11, flexShrink: 0 }}>not connected &middot; run: python3 swarm_v4.py</div>}
    </div>
  );
}

const panelStyle = {
  background: C.surface,
  border: `1px solid ${C.border}`,
  borderRadius: 4,
  padding: "10px 12px",
};

const inputStyle = {
  flex: 1,
  background: C.bg,
  border: `1px solid ${C.border}`,
  borderRadius: 4,
  padding: "7px 10px",
  color: C.text,
  fontFamily: "monospace",
  outline: "none",
  fontSize: 13,
};

const selectStyle = {
  background: C.bg,
  border: `1px solid ${C.border}`,
  borderRadius: 4,
  padding: "7px 10px",
  color: C.text,
  fontFamily: "monospace",
  outline: "none",
  fontSize: 12,
  maxWidth: 140,
};

function buttonStyle(active, big) {
  return {
    background: active ? C.accentDim : "transparent",
    border: `1px solid ${active ? C.accent : C.muted}`,
    color: active ? C.accent : C.textDim,
    padding: big ? "7px 0" : "6px 12px",
    borderRadius: 4,
    cursor: "pointer",
    fontFamily: "monospace",
    fontSize: big ? 13 : 12,
    fontWeight: active ? 600 : 400,
  };
}
