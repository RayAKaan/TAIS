import { useState, useEffect, useRef, useCallback } from "react";

const SERVER = "http://localhost:5123";
const GRID = 8;
const CELL = 96;
const W = GRID * CELL;

const C = {
  bg: "#0a0a0f",
  surface: "#111118",
  border: "#1e1e2e",
  muted: "#3a3a55",
  text: "#c8c8e0",
  textDim: "#5a5a80",
  accent: "#4a9eff",
  accentDim: "#1a3a6a",
  peak: "#1D9E75",
  predator: "#E24B4A",
  player: "#EF9F27",
  moteHi: "#7a6fff",
  moteLo: "#2a2a50",
  silence: "#3a3a55",
  birth: "#1D9E75",
  ambient: "#4a4a70",
  response: "#6a9fff",
  warning: "#E24B4A",
};

function energyColor(e = 0) {
  if (e > 120) return "#4aff9e";
  if (e > 80) return "#4a9eff";
  if (e > 50) return "#9e7aff";
  if (e > 25) return "#ff9e4a";
  return "#ff4a4a";
}

function msgStyle(type) {
  if (type === "response") return { color: C.response, prefix: "\u2192" };
  if (type === "silence") return { color: C.silence, prefix: "\u2205" };
  if (type === "birth") return { color: C.birth, prefix: "\u25C9" };
  if (type === "ambient") return { color: C.ambient, prefix: "\u25CC" };
  if (type === "player") return { color: C.player, prefix: "\u25B6" };
  if (type === "system") return { color: C.muted, prefix: "\u00B7" };
  return { color: C.text, prefix: "\u00B7" };
}

function MoteTooltip({ mote }) {
  const dirRatio = mote.spoke > 0 ? Math.round((mote.directed / mote.spoke) * 100) : 0;
  return (
    <div
      style={{
        position: "absolute",
        pointerEvents: "none",
        background: C.surface,
        border: `1px solid ${C.border}`,
        borderRadius: 6,
        padding: "8px 10px",
        fontSize: 11,
        color: C.text,
        lineHeight: 1.7,
        zIndex: 100,
        whiteSpace: "nowrap",
        boxShadow: "0 4px 20px rgba(0,0,0,0.6)",
      }}
    >
      <div style={{ color: C.accent, fontWeight: 500, marginBottom: 3 }}>Mote #{mote.id}</div>
      <div>
        energy <span style={{ color: energyColor(mote.energy) }}>{mote.energy}</span>
      </div>
      <div>
        fitness <span style={{ color: C.peak }}>{mote.fitness}</span>
      </div>
      <div>
        age <span style={{ color: C.textDim }}>{mote.age}</span>
      </div>
      <div>
        spoke <span style={{ color: C.moteHi }}>{mote.spoke}</span> &middot; directed{" "}
        <span style={{ color: C.accent }}>{dirRatio}%</span>
      </div>
      <div>
        silent (choice) <span style={{ color: C.silence }}>{mote.silent}</span>
      </div>
      <div>
        silent (fear) <span style={{ color: C.predator }}>{mote.silent_pred}</span>
      </div>
      <div>
        threshold <span style={{ color: C.textDim }}>{mote.threshold}</span>
      </div>
      <div>
        predator dist <span style={{ color: C.textDim }}>{mote.pred_dist}</span>
      </div>
    </div>
  );
}

function SwarmGrid({ state, playerPos, onGridClick, hoveredMote, setHoveredMote }) {
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
      ctx.beginPath();
      ctx.moveTo(i * CELL, 0);
      ctx.lineTo(i * CELL, W);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, i * CELL);
      ctx.lineTo(W, i * CELL);
      ctx.stroke();
    }

    if (state.peaks) {
      state.peaks.forEach((peak) => {
        const gx = (peak.x / GRID) * W;
        const gy = (peak.y / GRID) * W;
        const r = (peak.s / 10) * CELL * 2.2;
        const grad = ctx.createRadialGradient(gx, gy, 0, gx, gy, r);
        grad.addColorStop(0, "rgba(29,158,117,0.12)");
        grad.addColorStop(0.5, "rgba(29,158,117,0.04)");
        grad.addColorStop(1, "rgba(0,0,0,0)");
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(gx, gy, r, 0, Math.PI * 2);
        ctx.fill();
      });
    }

    if (state.signals) {
      state.signals.slice(-20).forEach((sig) => {
        const sx = (sig.position[0] / GRID) * W;
        const sy = (sig.position[1] / GRID) * W;
        ctx.strokeStyle = sig.is_broadcast ? "rgba(122,111,255,0.16)" : "rgba(74,158,255,0.16)";
        ctx.lineWidth = sig.is_broadcast ? 1.5 : 1;
        ctx.beginPath();
        ctx.arc(sx, sy, sig.is_broadcast ? 18 : 10, 0, Math.PI * 2);
        ctx.stroke();
      });
    }

    if (state.predators) {
      state.predators.forEach((pred) => {
        const px = (pred.x / GRID) * W;
        const py = (pred.y / GRID) * W;

        if (pred.target_x !== undefined) {
          const tx = (pred.target_x / GRID) * W;
          const ty = (pred.target_y / GRID) * W;
          ctx.strokeStyle = "rgba(226,75,74,0.18)";
          ctx.setLineDash([3, 4]);
          ctx.beginPath();
          ctx.moveTo(px, py);
          ctx.lineTo(tx, ty);
          ctx.stroke();
          ctx.setLineDash([]);
        }

        ctx.strokeStyle = "rgba(226,75,74,0.15)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(px, py, (2.5 / GRID) * W, 0, Math.PI * 2);
        ctx.stroke();

        ctx.fillStyle = C.predator;
        ctx.beginPath();
        ctx.moveTo(px, py - 9);
        ctx.lineTo(px + 8, py + 6);
        ctx.lineTo(px - 8, py + 6);
        ctx.closePath();
        ctx.fill();
      });
    }

    if (state.motes) {
      state.motes.forEach((mote) => {
        const mx = (mote.x / GRID) * W;
        const my = (mote.y / GRID) * W;
        const r = Math.max(3, Math.min(8, 4 + mote.energy / 50));
        const col = energyColor(mote.energy);

        if (hoveredMote && hoveredMote.id === mote.id) {
          ctx.strokeStyle = col;
          ctx.lineWidth = 1.5;
          ctx.setLineDash([3, 3]);
          ctx.beginPath();
          ctx.arc(mx, my, (2.8 / GRID) * W, 0, Math.PI * 2);
          ctx.stroke();
          ctx.setLineDash([]);
        }

        if (mote.silent_pred > 0) {
          ctx.strokeStyle = "rgba(226,75,74,0.18)";
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.arc(mx, my, r + 6, 0, Math.PI * 2);
          ctx.stroke();
        }

        ctx.fillStyle = col + "30";
        ctx.beginPath();
        ctx.arc(mx, my, r + 2, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = col;
        ctx.beginPath();
        ctx.arc(mx, my, r, 0, Math.PI * 2);
        ctx.fill();

        if (state.motes.length < 25) {
          ctx.fillStyle = C.textDim;
          ctx.font = "10px monospace";
          ctx.textAlign = "center";
          ctx.fillText(mote.id, mx, my - r - 3);
        }
      });
    }

    const ppx = (playerPos.x / GRID) * W;
    const ppy = (playerPos.y / GRID) * W;

    ctx.strokeStyle = "rgba(239,159,39,0.2)";
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.arc(ppx, ppy, (3.0 / GRID) * W, 0, Math.PI * 2);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.fillStyle = C.player;
    ctx.strokeStyle = C.bg;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(ppx, ppy, 9, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = C.bg;
    ctx.font = "bold 10px monospace";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("Y", ppx, ppy);
    ctx.textBaseline = "alphabetic";
  }, [state, playerPos, hoveredMote]);

  const handleMouseMove = useCallback(
    (e) => {
      if (!state?.motes) return;
      const rect = canvasRef.current.getBoundingClientRect();
      const mx = ((e.clientX - rect.left) / rect.width) * GRID;
      const my = ((e.clientY - rect.top) / rect.height) * GRID;
      let closest = null;
      let minD = 0.5;
      state.motes.forEach((m) => {
        const d = Math.sqrt((m.x - mx) ** 2 + (m.y - my) ** 2);
        if (d < minD) {
          minD = d;
          closest = m;
        }
      });
      setHoveredMote(closest);
    },
    [state, setHoveredMote]
  );

  const handleClick = useCallback(
    (e) => {
      const rect = canvasRef.current.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * GRID;
      const y = ((e.clientY - rect.top) / rect.height) * GRID;
      onGridClick(x, y);
    },
    [onGridClick]
  );

  return (
    <div style={{ position: "relative" }}>
      <canvas
        ref={canvasRef}
        width={W}
        height={W}
        style={{
          cursor: "crosshair",
          display: "block",
          borderRadius: 4,
          border: `1px solid ${C.border}`,
        }}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoveredMote(null)}
        onClick={handleClick}
      />
      {hoveredMote && (
        <div
          style={{
            position: "absolute",
            left: Math.min((hoveredMote.x / GRID) * W + 12, W - 160),
            top: Math.max((hoveredMote.y / GRID) * W - 80, 0),
          }}
        >
          <MoteTooltip mote={hoveredMote} />
        </div>
      )}
    </div>
  );
}

function VoiceRow({ msg }) {
  const s = msgStyle(msg.type);
  const isSilence = msg.type === "silence";
  return (
    <div
      style={{
        padding: "6px 10px",
        borderBottom: `1px solid ${C.border}`,
        display: "flex",
        gap: 8,
        alignItems: "flex-start",
        opacity: isSilence ? 0.5 : 1,
        fontFamily: "monospace",
      }}
    >
      <span style={{ color: s.color, fontSize: 13, marginTop: 1, flexShrink: 0 }}>{s.prefix}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <span style={{ color: C.textDim, fontSize: 11, marginRight: 6 }}>#{msg.mote_id ?? "you"}</span>
        {isSilence ? (
          <span style={{ color: C.silence, fontSize: 12, fontStyle: "italic" }}>
            [{msg.silence_reason === "predator" ? "silenced by fear" : msg.silence_reason === "no_info" ? "nothing to say" : "silence"}]
          </span>
        ) : (
          <span style={{ color: s.color, fontSize: 13 }}>{msg.text}</span>
        )}
      </div>
      {msg.energy !== undefined && (
        <span style={{ fontSize: 10, color: energyColor(msg.energy), flexShrink: 0, marginTop: 2 }}>{msg.energy}</span>
      )}
    </div>
  );
}

function Stat({ label, value, color }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontSize: 20, fontWeight: 500, color: color || C.text, fontFamily: "monospace" }}>{value}</div>
      <div style={{ fontSize: 10, color: C.textDim, textTransform: "uppercase", letterSpacing: "0.08em" }}>{label}</div>
    </div>
  );
}

export default function App() {
  const [state, setState] = useState(null);
  const [playerPos, setPlayerPos] = useState({ x: 4.0, y: 4.0 });
  const [voices, setVoices] = useState([]);
  const [input, setInput] = useState("");
  const [connected, setConnected] = useState(false);
  const [hoveredMote, setHoveredMote] = useState(null);
  const [claimFitness, setClaimFitness] = useState(5.0);
  const [mode, setMode] = useState("move");
  const voiceLogRef = useRef(null);
  const lastVoiceTick = useRef(-1);

  useEffect(() => {
    const es = new EventSource(`${SERVER}/stream`);
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        setState(data);
        if (data.player) setPlayerPos({ x: data.player.x, y: data.player.y });

        if (data.voices && data.tick > lastVoiceTick.current) {
          lastVoiceTick.current = data.tick;
          const newV = data.voices.filter(
            (v) => v.tick >= data.tick - 1 && (v.type !== "ambient" || Math.random() < 0.4)
          );
          if (newV.length > 0) {
            setVoices((prev) => [...prev, ...newV].slice(-120));
          }
        }
      } catch (err) {
        console.warn("bad SSE payload", err);
      }
    };
    return () => es.close();
  }, []);

  useEffect(() => {
    if (voiceLogRef.current) {
      voiceLogRef.current.scrollTop = voiceLogRef.current.scrollHeight;
    }
  }, [voices]);

  const handleGridClick = useCallback(
    async (x, y) => {
      const cx = Math.max(0, Math.min(GRID, x));
      const cy = Math.max(0, Math.min(GRID, y));

      if (mode === "move") {
        setPlayerPos({ x: cx, y: cy });
        await fetch(`${SERVER}/player/move`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ x: cx, y: cy }),
        });
        setVoices((prev) => [
          ...prev,
          {
            mote_id: null,
            text: `Moved to (${cx.toFixed(1)}, ${cy.toFixed(1)})`,
            type: "player",
            tick: state?.tick ?? 0,
          },
        ]);
      } else {
        await fetch(`${SERVER}/player/speak`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ x: cx, y: cy, fitness: claimFitness, message: input }),
        });
        setVoices((prev) => [
          ...prev,
          {
            mote_id: null,
            text: `[signal \u2192 (${cx.toFixed(1)}, ${cy.toFixed(1)}) fitness=${claimFitness.toFixed(1)}]`,
            type: "player",
            tick: state?.tick ?? 0,
          },
        ]);
        setInput("");
      }
    },
    [mode, state, claimFitness, input]
  );

  const handleSend = useCallback(async () => {
    if (!input.trim()) return;
    const px = playerPos.x;
    const py = playerPos.y;
    await fetch(`${SERVER}/player/speak`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ x: px, y: py, fitness: claimFitness, message: input }),
    });
    setVoices((prev) => [
      ...prev,
      {
        mote_id: null,
        text: `"${input}" [fitness claim: ${claimFitness.toFixed(1)}]`,
        type: "player",
        tick: state?.tick ?? 0,
      },
    ]);
    setInput("");
  }, [input, playerPos, claimFitness, state]);

  const handleReset = async () => {
    await fetch(`${SERVER}/reset`, { method: "POST" });
    setVoices([{ mote_id: null, text: "Swarm reset.", type: "system", tick: 0 }]);
  };

  const handleListen = async () => {
    const res = await fetch(`${SERVER}/player/listen`);
    const data = await res.json();
    setVoices((prev) => [
      ...prev,
      {
        mote_id: null,
        text: `[listening \u2014 ${data.count} voices nearby]`,
        type: "system",
        tick: state?.tick ?? 0,
      },
      ...data.voices,
    ]);
  };

  const totalSpoke = state?.motes?.reduce((s, m) => s + m.spoke, 0) ?? 0;
  const totalSilent = state?.motes?.reduce((s, m) => s + m.silent, 0) ?? 0;
  const totalFear = state?.motes?.reduce((s, m) => s + m.silent_pred, 0) ?? 0;
  const totalDir = state?.motes?.reduce((s, m) => s + m.directed, 0) ?? 0;
  const totalBrd = state?.motes?.reduce((s, m) => s + m.broadcast, 0) ?? 0;
  const dirRatio = totalSpoke > 0 ? Math.round((totalDir / totalSpoke) * 100) : 0;

  return (
    <div
      style={{
        background: C.bg,
        height: "100vh",
        color: C.text,
        fontFamily: "monospace",
        fontSize: 13,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          background: C.surface,
          borderBottom: `1px solid ${C.border}`,
          padding: "12px 20px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexShrink: 0,
        }}
      >
        <div>
          <span style={{ color: C.accent, fontWeight: 600, fontSize: 16 }}>TAIS-LANG</span>
          <span style={{ color: C.textDim, marginLeft: 10, fontSize: 12 }}>thermodynamic swarm &middot; emergent communication</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <span style={{ fontSize: 11, color: connected ? C.peak : C.predator }}>
            {connected ? "\u25CF LIVE" : "\u25CB OFFLINE"}
          </span>
          <span style={{ color: C.textDim, fontSize: 11 }}>
            tick {state?.tick ?? 0} &middot; {state?.population ?? 0} motes
          </span>
          <button
            onClick={handleReset}
            style={{
              background: "transparent",
              border: `1px solid ${C.muted}`,
              color: C.textDim,
              padding: "4px 12px",
              borderRadius: 3,
              cursor: "pointer",
              fontSize: 11,
            }}
          >
            reset
          </button>
        </div>
      </div>

      {/* Main layout */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Left: Grid + controls */}
        <div
          style={{
            flexShrink: 0,
            padding: 16,
            display: "flex",
            flexDirection: "column",
            gap: 12,
            overflowY: "auto",
          }}
        >
          <SwarmGrid
            state={state}
            playerPos={playerPos}
            onGridClick={handleGridClick}
            hoveredMote={hoveredMote}
            setHoveredMote={setHoveredMote}
          />

          {/* Mode toggle */}
          <div style={{ display: "flex", gap: 8 }}>
            {["move", "speak"].map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                style={{
                  flex: 1,
                  padding: "7px 0",
                  borderRadius: 3,
                  cursor: "pointer",
                  fontSize: 12,
                  fontFamily: "monospace",
                  fontWeight: mode === m ? 600 : 400,
                  background: mode === m ? C.accentDim : "transparent",
                  border: `1px solid ${mode === m ? C.accent : C.border}`,
                  color: mode === m ? C.accent : C.textDim,
                }}
              >
                {m === "move" ? "click \u2192 move" : "click \u2192 speak"}
              </button>
            ))}
          </div>

          {/* Fitness claim slider */}
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 11, color: C.textDim, width: 100, flexShrink: 0 }}>signal fitness</span>
            <input
              type="range"
              min="0"
              max="12"
              step="0.5"
              value={claimFitness}
              onChange={(e) => setClaimFitness(parseFloat(e.target.value))}
              style={{ flex: 1 }}
            />
            <span style={{ fontSize: 12, color: C.peak, width: 30, textAlign: "right" }}>{claimFitness.toFixed(1)}</span>
          </div>

          {/* Legend */}
          <div
            style={{
              background: C.surface,
              border: `1px solid ${C.border}`,
              borderRadius: 4,
              padding: "10px 12px",
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "6px 16px",
              fontSize: 11,
              color: C.textDim,
            }}
          >
            <span>{"\u25B6"} <span style={{ color: C.player }}>you</span></span>
            <span>{"\u25B2"} <span style={{ color: C.predator }}>predator</span></span>
            <span>{"\u25CF"} <span style={{ color: "#4aff9e" }}>high energy</span></span>
            <span>{"\u25CF"} <span style={{ color: "#ff4a4a" }}>dying</span></span>
            <span style={{ gridColumn: "1/-1", color: C.textDim, marginTop: 4 }}>click grid to {mode}</span>
          </div>

          {/* Stats */}
          <div
            style={{
              background: C.surface,
              border: `1px solid ${C.border}`,
              borderRadius: 4,
              padding: "12px",
              display: "grid",
              gridTemplateColumns: "repeat(5,1fr)",
              gap: 8,
            }}
          >
            <Stat label="directed" value={`${dirRatio}%`} color={C.accent} />
            <Stat label="spoke" value={totalSpoke} color={C.moteHi} />
            <Stat label="brd" value={totalBrd} color={C.player} />
            <Stat label="chose\u2205" value={totalSilent} color={C.silence} />
            <Stat label="feared\u2205" value={totalFear} color={C.predator} />
          </div>

          {/* Player info */}
          <div
            style={{
              background: C.surface,
              border: `1px solid ${C.border}`,
              borderRadius: 4,
              padding: "10px 12px",
              fontSize: 11,
              color: C.textDim,
            }}
          >
            <span style={{ color: C.player }}>you</span> at ({playerPos.x.toFixed(1)}, {playerPos.y.toFixed(1)}) &middot; fitness{" "}
            <span style={{ color: C.peak }}>{state?.player?.fitness?.toFixed?.(2) ?? "\u2013"}</span>
          </div>
        </div>

        {/* Right: Conversation panel */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            borderLeft: `1px solid ${C.border}`,
            overflow: "hidden",
            minWidth: 320,
          }}
        >
          {/* Conversation header */}
          <div
            style={{
              background: C.surface,
              padding: "10px 14px",
              borderBottom: `1px solid ${C.border}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexShrink: 0,
            }}
          >
            <span style={{ fontSize: 12, color: C.textDim }}>conversation</span>
            <button
              onClick={handleListen}
              style={{
                background: "transparent",
                border: `1px solid ${C.muted}`,
                color: C.textDim,
                padding: "3px 10px",
                borderRadius: 3,
                cursor: "pointer",
                fontSize: 11,
              }}
            >
              listen
            </button>
          </div>

          {/* Voice log */}
          <div
            ref={voiceLogRef}
            style={{
              flex: 1,
              overflowY: "auto",
              padding: 0,
            }}
          >
            {voices.length === 0 && (
              <div style={{ padding: 24, color: C.textDim, fontSize: 12, textAlign: "center", marginTop: 60 }}>
                <div style={{ marginBottom: 10 }}>No voices yet.</div>
                <div>Click the grid to move into range of motes.</div>
                <div>Click <em>speak</em> mode to send a signal.</div>
              </div>
            )}
            {voices.map((v, i) => (
              <VoiceRow key={`${v.tick}-${v.mote_id}-${i}`} msg={v} />
            ))}
          </div>

          {/* Legend for voice types */}
          <div
            style={{
              background: C.surface,
              borderTop: `1px solid ${C.border}`,
              borderBottom: `1px solid ${C.border}`,
              padding: "5px 12px",
              display: "flex",
              gap: 16,
              fontSize: 10,
              color: C.textDim,
              flexShrink: 0,
            }}
          >
            <span>{"\u2192"} <span style={{ color: C.response }}>response</span></span>
            <span>{"\u25CC"} <span style={{ color: C.ambient }}>ambient</span></span>
            <span>{"\u2205"} silence</span>
            <span>{"\u25C9"} <span style={{ color: C.birth }}>birth</span></span>
            <span>{"\u25B6"} <span style={{ color: C.player }}>you</span></span>
          </div>

          {/* Input */}
          <div
            style={{
              background: C.surface,
              padding: "10px 14px",
              display: "flex",
              gap: 8,
              flexShrink: 0,
            }}
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="send a signal\u2026 (enter)"
              style={{
                flex: 1,
                background: C.bg,
                border: `1px solid ${C.border}`,
                borderRadius: 4,
                padding: "8px 12px",
                color: C.text,
                fontSize: 13,
                fontFamily: "monospace",
                outline: "none",
              }}
            />
            <button
              onClick={handleSend}
              style={{
                background: C.accentDim,
                border: `1px solid ${C.accent}`,
                color: C.accent,
                padding: "8px 18px",
                borderRadius: 4,
                cursor: "pointer",
                fontSize: 13,
                fontFamily: "monospace",
                fontWeight: 600,
              }}
            >
              send
            </button>
          </div>
        </div>
      </div>

      {/* Bottom hint */}
      {!connected && (
        <div
          style={{
            background: "rgba(226,75,74,0.1)",
            borderTop: `1px solid ${C.predator}`,
            padding: "8px 16px",
            fontSize: 11,
            color: C.predator,
            textAlign: "center",
            flexShrink: 0,
          }}
        >
          not connected &middot; start the server: <code>python3 swarm_server.py</code>
        </div>
      )}
    </div>
  );
}
