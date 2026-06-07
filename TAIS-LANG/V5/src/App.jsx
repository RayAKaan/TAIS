import { useCallback, useEffect, useMemo, useRef, useState } from "react";

const SERVER = "http://localhost:5123";
const W = 640;

const C = {
  bg: "#07070c",
  surface: "#111118",
  panel: "#0f0f17",
  border: "#242438",
  muted: "#3a3a55",
  text: "#d2d2ea",
  textDim: "#66668e",
  accent: "#4a9eff",
  accentDim: "#17345f",
  food: "#28d17c",
  water: "#3fa7ff",
  shelter: "#c084fc",
  poison: "#d8f542",
  predator: "#E24B4A",
  player: "#EF9F27",
  speech: "#8a7aff",
  directed: "#4a9eff",
  silence: "#50506d",
  teaching: "#35d399",
  birth: "#1D9E75",
  death: "#ff4a4a",
};

const resourceColor = { food: C.food, water: C.water, shelter: C.shelter, poison: C.poison };

function energyColor(e = 0) {
  if (e > 130) return "#4aff9e";
  if (e > 90) return "#4a9eff";
  if (e > 55) return "#9e7aff";
  if (e > 25) return "#ff9e4a";
  return "#ff4a4a";
}

function eventStyle(ev) {
  if (ev.type === "player") return { color: C.player, prefix: "\u25B6" };
  if (ev.type === "teaching") return { color: C.teaching, prefix: "\u25C6" };
  if (ev.type === "understanding") return { color: ev.semantic_match ? C.teaching : ev.success ? C.accent : C.textDim, prefix: ev.semantic_match ? "\u2713" : ev.success ? "\u21AF" : "?" };
  if (ev.type === "utterance") return { color: ev.target_id ? C.directed : C.speech, prefix: ev.target_id ? "\u2192" : "\u25CC" };
  if (ev.type === "silence") return { color: C.silence, prefix: "\u2205" };
  if (ev.type === "birth") return { color: C.birth, prefix: "\u25C9" };
  if (ev.type === "death") return { color: C.death, prefix: "\u00D7" };
  if (ev.type === "system") return { color: C.textDim, prefix: "\u00B7" };
  return { color: C.text, prefix: "\u00B7" };
}

function Tiny({ children, color = C.textDim }) {
  return <span style={{ fontSize: 11, color }}>{children}</span>;
}

function Stat({ label, value, color }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontSize: 17, fontWeight: 600, color: color || C.text, fontFamily: "monospace" }}>{value}</div>
      <div style={{ fontSize: 10, color: C.textDim, textTransform: "uppercase", letterSpacing: "0.08em" }}>{label}</div>
    </div>
  );
}

function MoteTooltip({ mote }) {
  const lexItems = Object.entries(mote.top_lexicon || {}).slice(0, 8);
  const memItems = (mote.memories || []).slice(0, 5);
  const dirRatio = mote.spoke ? Math.round((mote.directed / mote.spoke) * 100) : 0;
  return (
    <div style={{ position: "absolute", pointerEvents: "none", background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, padding: "10px 12px", fontSize: 12, color: C.text, lineHeight: 1.7, zIndex: 100, whiteSpace: "nowrap", boxShadow: "0 4px 20px rgba(0,0,0,0.65)", minWidth: 260 }}>
      <div style={{ color: C.accent, fontWeight: 600, marginBottom: 4 }}>Mote #{mote.id}</div>
      <div>energy <span style={{ color: energyColor(mote.energy) }}>{mote.energy}</span> &middot; water <span style={{ color: C.water }}>{mote.hydration}</span> &middot; tox <span style={{ color: C.poison }}>{mote.toxicity}</span></div>
      <div>intent <span style={{ color: C.speech }}>{mote.intent}</span> &middot; pred {mote.pred_dist}</div>
      <div>spoke {mote.spoke} &middot; directed <span style={{ color: C.accent }}>{dirRatio}%</span> &middot; silent {mote.silent_choice}/{mote.silent_fear}</div>
      <div>grammar <span style={{ color: C.textDim }}>{mote.genome?.order}</span> &middot; max {mote.genome?.max_len}</div>
      <div>lex updates <span style={{ color: C.teaching }}>{mote.lexicon_updates}</span> &middot; memories {mote.memory_updates}</div>
      {mote.recent_utterances?.length > 0 && <div>recent <span style={{ color: C.speech }}>{mote.recent_utterances.join(" \u00B7 ")}</span></div>}
      {lexItems.length > 0 && <div style={{ marginTop: 5, borderTop: `1px solid ${C.border}`, paddingTop: 4 }}>{lexItems.map(([tok, obj]) => <div key={tok}><span style={{ color: C.teaching }}>{tok}</span> \u2248 {obj.concept} <span style={{ color: C.textDim }}>{obj.weight}</span></div>)}</div>}
      {memItems.length > 0 && <div style={{ marginTop: 5, borderTop: `1px solid ${C.border}`, paddingTop: 4 }}>{memItems.map((m, i) => <div key={i}><span style={{ color: resourceConceptColor(m.concept) }}>{m.concept}</span> ({m.x},{m.y}) c={m.confidence}</div>)}</div>}
    </div>
  );
}

function resourceConceptColor(c) {
  if (c === "FOOD") return C.food;
  if (c === "WATER") return C.water;
  if (c === "SHELTER") return C.shelter;
  if (c === "POISON") return C.poison;
  if (c === "PREDATOR") return C.predator;
  return C.text;
}

function WorldCanvas({ state, playerPos, hoveredMote, setHoveredMote, onGridClick, mode }) {
  const canvasRef = useRef(null);
  const size = state?.world?.size || 32;
  const scale = W / size;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !state) return;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, W, W);
    ctx.fillStyle = C.bg;
    ctx.fillRect(0, 0, W, W);

    const major = Math.max(4, Math.round(size / 8));
    ctx.strokeStyle = C.border;
    ctx.lineWidth = 0.5;
    for (let g = 0; g <= size; g += major) {
      ctx.beginPath(); ctx.moveTo(g * scale, 0); ctx.lineTo(g * scale, W); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, g * scale); ctx.lineTo(W, g * scale); ctx.stroke();
    }

    state.world?.resources?.forEach((r) => {
      const x = r.x * scale, y = r.y * scale, rad = r.radius * scale * 2.2;
      const col = resourceColor[r.kind] || C.text;
      const alpha = r.kind === "poison" ? 0.12 : 0.095;
      const grad = ctx.createRadialGradient(x, y, 0, x, y, rad);
      grad.addColorStop(0, `${col}${Math.round(alpha * 255).toString(16).padStart(2, "0")}`);
      grad.addColorStop(0.65, `${col}18`);
      grad.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = grad;
      ctx.beginPath(); ctx.arc(x, y, rad, 0, Math.PI * 2); ctx.fill();
    });

    state.world?.landmarks?.forEach((lm) => {
      const x = lm.x * scale, y = lm.y * scale;
      ctx.fillStyle = C.textDim;
      ctx.strokeStyle = C.border;
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.rect(x - 4, y - 4, 8, 8); ctx.fill(); ctx.stroke();
      ctx.fillStyle = C.textDim;
      ctx.font = "8px monospace";
      ctx.textAlign = "center";
      ctx.fillText(lm.token, x, y - 7);
    });

    state.recent_utterances?.slice(-50).forEach((u) => {
      if (u.is_player) return;
      const x = u.position[0] * scale, y = u.position[1] * scale;
      ctx.strokeStyle = u.is_broadcast ? "rgba(138,122,255,0.16)" : "rgba(74,158,255,0.22)";
      ctx.lineWidth = u.is_broadcast ? 1.1 : 1.7;
      ctx.beginPath(); ctx.arc(x, y, u.is_broadcast ? 15 : 8, 0, Math.PI * 2); ctx.stroke();
    });

    state.predators?.forEach((p) => {
      const x = p.x * scale, y = p.y * scale, tx = p.target_x * scale, ty = p.target_y * scale;
      ctx.strokeStyle = "rgba(226,75,74,0.18)";
      ctx.setLineDash([4, 4]); ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(tx, ty); ctx.stroke(); ctx.setLineDash([]);
      ctx.strokeStyle = "rgba(226,75,74,0.13)";
      ctx.beginPath(); ctx.arc(x, y, 2.2 * scale, 0, Math.PI * 2); ctx.stroke();
      ctx.fillStyle = C.predator;
      ctx.beginPath(); ctx.moveTo(x, y - 9); ctx.lineTo(x + 8, y + 6); ctx.lineTo(x - 8, y + 6); ctx.closePath(); ctx.fill();
    });

    state.motes?.forEach((m) => {
      const x = m.x * scale, y = m.y * scale;
      const r = Math.max(2.2, Math.min(6.5, 3 + m.energy / 45));
      const col = energyColor(m.energy);
      if (hoveredMote?.id === m.id) {
        ctx.strokeStyle = col; ctx.setLineDash([3, 3]); ctx.beginPath(); ctx.arc(x, y, 4.5 * scale, 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]);
      }
      if (m.intent === "PREDATOR" || m.silent_fear > 0) {
        ctx.strokeStyle = "rgba(226,75,74,0.24)"; ctx.beginPath(); ctx.arc(x, y, r + 6, 0, Math.PI * 2); ctx.stroke();
      }
      ctx.fillStyle = `${col}35`; ctx.beginPath(); ctx.arc(x, y, r + 2, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = col; ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
    });

    const px = playerPos.x * scale, py = playerPos.y * scale;
    ctx.strokeStyle = "rgba(239,159,39,0.25)"; ctx.setLineDash([4, 4]); ctx.beginPath(); ctx.arc(px, py, 6 * scale, 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = C.player; ctx.strokeStyle = C.bg; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(px, py, 8, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.fillStyle = C.bg; ctx.font = "bold 10px monospace"; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(mode === "teach" ? "T" : mode === "speak" ? "S" : "Y", px, py); ctx.textBaseline = "alphabetic";
  }, [state, playerPos, hoveredMote, mode, scale, size]);

  const mouseMove = useCallback((e) => {
    if (!state?.motes) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * size;
    const y = ((e.clientY - rect.top) / rect.height) * size;
    let closest = null, best = 0.75;
    state.motes.forEach((m) => {
      const d = Math.sqrt((m.x - x) ** 2 + (m.y - y) ** 2);
      if (d < best) { best = d; closest = m; }
    });
    setHoveredMote(closest);
  }, [state, size, setHoveredMote]);

  const click = useCallback((e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * size;
    const y = ((e.clientY - rect.top) / rect.height) * size;
    onGridClick(x, y);
  }, [size, onGridClick]);

  return (
    <div style={{ position: "relative" }}>
      <canvas ref={canvasRef} width={W} height={W} onMouseMove={mouseMove} onMouseLeave={() => setHoveredMote(null)} onClick={click} style={{ display: "block", cursor: "crosshair", borderRadius: 4, border: `1px solid ${C.border}` }} />
      {hoveredMote && <div style={{ position: "absolute", left: Math.min((hoveredMote.x * scale) + 12, W - 275), top: Math.max((hoveredMote.y * scale) - 95, 0) }}><MoteTooltip mote={hoveredMote} /></div>}
    </div>
  );
}

function EventRow({ ev }) {
  const st = eventStyle(ev);
  const label = ev.type === "teaching" ? `taught ${ev.text || ev.tokens?.join(" ")} \u2248 ${ev.concept}`
    : ev.type === "understanding" ? `${ev.listener_id} heard "${ev.text}" as ${ev.listener_interpretation} \u2192 ${ev.action}; outcome ${ev.outcome}`
    : ev.type === "silence" ? `[${ev.silence_reason || "silence"}]`
    : ev.text || ev.tokens?.join(" ") || "";
  const concept = ev.type === "understanding" ? ev.speaker_intent : (ev.intended_concept || ev.intent || ev.concept);
  return (
    <div style={{ padding: "7px 10px", borderBottom: `1px solid ${C.border}`, display: "flex", gap: 8, alignItems: "flex-start", opacity: ev.type === "silence" ? 0.55 : 1 }}>
      <span style={{ color: st.color, fontWeight: ev.type === "understanding" ? 600 : 400, flexShrink: 0 }}>{st.prefix}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <span style={{ color: C.textDim, fontSize: 11, marginRight: 6 }}>#{ev.mote_id ?? ev.speaker_id ?? "you"}</span>
        <span style={{ color: st.color, fontSize: 13 }}>{label}</span>
        {concept && <span style={{ color: resourceConceptColor(concept), fontSize: 10, marginLeft: 8 }}>({concept})</span>}
        {ev.target_id && <span style={{ color: C.directed, fontSize: 10, marginLeft: 8 }}>\u2192#{ev.target_id}</span>}
      </div>
      {ev.energy !== undefined && <span style={{ color: energyColor(ev.energy), fontSize: 10, marginTop: 2 }}>{ev.energy}</span>}
    </div>
  );
}

export default function App() {
  const [state, setState] = useState(null);
  const [connected, setConnected] = useState(false);
  const [playerPos, setPlayerPos] = useState({ x: 16, y: 16 });
  const [events, setEvents] = useState([]);
  const [hoveredMote, setHoveredMote] = useState(null);
  const [mode, setMode] = useState("move");
  const [text, setText] = useState("food");
  const [teachWord, setTeachWord] = useState("food");
  const [concept, setConcept] = useState("FOOD");
  const [value, setValue] = useState(8.0);
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
          const newer = data.events.filter((ev) => ev.tick >= data.tick - 1);
          if (newer.length) setEvents((prev) => [...prev, ...newer].slice(-220));
        }
      } catch (err) { console.warn(err); }
    };
    return () => es.close();
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  const worldSize = state?.world?.size || 32;
  const concepts = state?.concepts || ["FOOD", "WATER", "SHELTER", "POISON", "PREDATOR", "SAFE"];
  const stats = state?.stats || {};

  const sendMove = useCallback(async (x, y) => {
    const cx = Math.max(0, Math.min(worldSize, x));
    const cy = Math.max(0, Math.min(worldSize, y));
    setPlayerPos({ x: cx, y: cy });
    await fetch(`${SERVER}/player/move`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ x: cx, y: cy }) });
    setEvents((prev) => [...prev, { type: "player", text: `moved (${cx.toFixed(1)}, ${cy.toFixed(1)})`, tick: state?.tick ?? 0 }]);
  }, [worldSize, state]);

  const sendSpeak = useCallback(async (x = playerPos.x, y = playerPos.y, teaching = false) => {
    await fetch(`${SERVER}/player/speak`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, concept: teaching ? concept : undefined, teaching, value, x, y }) });
    setEvents((prev) => [...prev, { type: "player", text: `${text} [value=${value.toFixed(1)}]`, intended_concept: teaching ? concept : undefined, tick: state?.tick ?? 0 }]);
  }, [text, concept, value, playerPos, state]);

  const sendTeach = useCallback(async () => {
    await fetch(`${SERVER}/player/teach`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ word: teachWord, concept, value }) });
    setEvents((prev) => [...prev, { type: "teaching", text: teachWord, concept, tick: state?.tick ?? 0 }]);
  }, [teachWord, concept, value, state]);

  const onGridClick = useCallback((x, y) => {
    if (mode === "move") sendMove(x, y);
    else if (mode === "speak") sendSpeak(x, y, false);
    else sendMove(x, y);
  }, [mode, sendMove, sendSpeak]);

  const reset = async () => {
    await fetch(`${SERVER}/reset`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
    setEvents([{ type: "system", text: "reset", tick: 0 }]);
  };

  const save = async () => {
    const res = await fetch(`${SERVER}/save`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
    const d = await res.json();
    setEvents((prev) => [...prev, { type: "system", text: `saved ${d.path}`, tick: state?.tick ?? 0 }]);
  };

  const knownWords = useMemo(() => stats.common_tokens || [], [stats]);
  const dirPct = Math.round((stats.directed_ratio || 0) * 100);

  return (
    <div style={{ background: C.bg, height: "100vh", color: C.text, fontFamily: "monospace", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <div style={{ background: C.surface, borderBottom: `1px solid ${C.border}`, padding: "12px 20px", display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0 }}>
        <div><span style={{ color: C.accent, fontWeight: 700, fontSize: 16 }}>TAIS-LANG v5</span><span style={{ color: C.textDim, marginLeft: 10, fontSize: 12 }}>understanding audit &middot; syntax &middot; culture</span></div>
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <span style={{ color: connected ? C.food : C.predator, fontSize: 11 }}>{connected ? "\u25CF LIVE" : "\u25CB OFFLINE"}</span>
          <Tiny>tick {state?.tick ?? 0} &middot; pop {state?.population ?? 0}</Tiny>
          <button onClick={save} style={buttonStyle(false)}>save</button>
          <button onClick={reset} style={buttonStyle(false)}>reset</button>
        </div>
      </div>

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <div style={{ flexShrink: 0, width: W + 32, padding: 16, display: "flex", flexDirection: "column", gap: 10, overflowY: "auto" }}>
          <WorldCanvas state={state} playerPos={playerPos} hoveredMote={hoveredMote} setHoveredMote={setHoveredMote} onGridClick={onGridClick} mode={mode} />

          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 6 }}>{["move", "speak", "teach"].map((m) => <button key={m} onClick={() => setMode(m)} style={buttonStyle(mode === m, true)}>{m}</button>)}</div>

          <div style={panelStyle}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 7 }}>
              <Tiny color={C.player}>speak sound/word</Tiny>
              <input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && sendSpeak()} style={inputStyle} />
              <button onClick={() => sendSpeak()} style={buttonStyle(false)}>send</button>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Tiny>advertised value</Tiny>
              <input type="range" min="0" max="15" step="0.5" value={value} onChange={(e) => setValue(parseFloat(e.target.value))} style={{ flex: 1 }} />
              <span style={{ color: C.food, width: 32, fontSize: 12 }}>{value.toFixed(1)}</span>
            </div>
          </div>

          <div style={panelStyle}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Tiny color={C.teaching}>teach</Tiny>
              <input value={teachWord} onChange={(e) => setTeachWord(e.target.value)} style={{ ...inputStyle, flex: 0.8 }} />
              <select value={concept} onChange={(e) => setConcept(e.target.value)} style={selectStyle}>{concepts.map((c) => <option key={c}>{c}</option>)}</select>
              <button onClick={sendTeach} style={buttonStyle(false)}>ground</button>
            </div>
            <div style={{ marginTop: 7, color: C.textDim, fontSize: 11 }}>Ground your word in nearby motes' lexicons and maps at your current position.</div>
          </div>

          <div style={{ ...panelStyle, display: "grid", gridTemplateColumns: "repeat(8, 1fr)", gap: 7 }}>
            <Stat label="direct" value={`${dirPct}%`} color={C.directed} />
            <Stat label="spoke" value={stats.spoke || 0} color={C.speech} />
            <Stat label="sem" value={`${Math.round((stats.semantic_rate || 0) * 100)}%`} color={C.teaching} />
            <Stat label="util" value={`${Math.round((stats.utility_rate || 0) * 100)}%`} color={C.accent} />
            <Stat label="silent" value={stats.choice_silence || 0} color={C.silence} />
            <Stat label="fear\u2205" value={stats.fear_silence || 0} color={C.predator} />
            <Stat label="lex" value={stats.lexicon_updates || 0} color={C.teaching} />
            <Stat label="mem" value={stats.memory_updates || 0} color={C.food} />
          </div>

          <div style={{ ...panelStyle, display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 6, fontSize: 11 }}>
            <span style={{ color: C.food }}>\u25CF food</span><span style={{ color: C.water }}>\u25CF water</span><span style={{ color: C.shelter }}>\u25CF shelter</span><span style={{ color: C.poison }}>\u25CF poison</span>
          </div>

          <div style={panelStyle}>
            <div style={{ color: C.textDim, fontSize: 11, marginBottom: 5 }}>common grounded tokens</div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {knownWords.length === 0 && <Tiny>none yet \u2014 teach or let culture evolve</Tiny>}
              {knownWords.map((w) => <span key={`${w.token}-${w.concept}`} style={{ color: resourceConceptColor(w.concept), border: `1px solid ${C.border}`, padding: "2px 6px", borderRadius: 3, fontSize: 11 }}>{w.token}\u2248{w.concept}\u00D7{w.count}</span>)}
            </div>
          </div>
        </div>

        <div style={{ flex: 1, display: "flex", flexDirection: "column", borderLeft: `1px solid ${C.border}`, overflow: "hidden", minWidth: 320 }}>
          <div style={{ background: C.surface, borderBottom: `1px solid ${C.border}`, padding: "10px 14px", display: "flex", justifyContent: "space-between", flexShrink: 0 }}>
            <Tiny>conversation stream &middot; utterances, teaching, chosen silence</Tiny>
            <Tiny color={C.player}>you ({playerPos.x.toFixed(1)}, {playerPos.y.toFixed(1)}) &middot; local value {state?.player?.fitness?.toFixed?.(2) ?? "\u2013"}</Tiny>
          </div>
          <div ref={scrollRef} style={{ flex: 1, overflowY: "auto" }}>
            {events.length === 0 && <div style={{ padding: 30, textAlign: "center", color: C.textDim, fontSize: 12 }}>No speech yet. Move, teach, or send a sound.</div>}
            {events.map((ev, i) => <EventRow key={`${ev.tick}-${ev.type}-${ev.mote_id || ev.speaker_id}-${i}`} ev={ev} />)}
          </div>
          <div style={{ borderTop: `1px solid ${C.border}`, padding: "7px 12px", background: C.surface, display: "flex", gap: 14, fontSize: 10, color: C.textDim, flexShrink: 0 }}>
            <span>\u25CC broadcast</span><span>\u2192 directed</span><span style={{ color: C.teaching }}>\u2713 understood</span><span style={{ color: C.accent }}>\u21AF useful</span><span>\u2205 silence</span><span>\u25C6 teaching</span>
          </div>
        </div>
      </div>

      {!connected && <div style={{ color: C.predator, background: "rgba(226,75,74,0.1)", borderTop: `1px solid ${C.predator}`, padding: 8, textAlign: "center", fontSize: 11, flexShrink: 0 }}>not connected &middot; run: python3 swarm_v5.py</div>}
    </div>
  );
}

const panelStyle = { background: C.surface, border: `1px solid ${C.border}`, borderRadius: 4, padding: "10px 12px" };
const inputStyle = { flex: 1, background: C.bg, border: `1px solid ${C.border}`, borderRadius: 4, padding: "7px 10px", color: C.text, fontFamily: "monospace", outline: "none", fontSize: 13 };
const selectStyle = { background: C.bg, border: `1px solid ${C.border}`, borderRadius: 4, padding: "7px 10px", color: C.text, fontFamily: "monospace", outline: "none", fontSize: 12, maxWidth: 130 };
function buttonStyle(active, big) { return { background: active ? C.accentDim : "transparent", border: `1px solid ${active ? C.accent : C.muted}`, color: active ? C.accent : C.textDim, padding: big ? "7px 0" : "6px 12px", borderRadius: 4, cursor: "pointer", fontFamily: "monospace", fontSize: big ? 13 : 12, fontWeight: active ? 600 : 400 }; }
