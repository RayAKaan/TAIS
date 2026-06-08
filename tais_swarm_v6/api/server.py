"""
FastAPI + WebSocket server for TAIS Swarm V6.

No LLM routes. Raw state endpoints for metacognition, causal, and
planning introspection. /player/demonstrate for grounded teaching.
"""

from __future__ import annotations

import json
import time
import asyncio
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse
except ImportError:
    FastAPI = None




class SwarmServer:
    def __init__(self, swarm, host: str = "127.0.0.1", port: int = 8612):
        self.swarm = swarm
        self.host = host
        self.port = port
        self._websockets: List[WebSocket] = []
        self._running = False

        if FastAPI is None:
            raise ImportError("FastAPI is required for SwarmServer. Install with: pip install fastapi uvicorn")

        self.app = FastAPI(title="TAIS Swarm V6", version="6.0.0")
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self._setup_routes()
        self._tick_task: Optional[asyncio.Task] = None

        @self.app.on_event("startup")
        async def _start_background_tick():
            self._tick_task = asyncio.create_task(self._run_ticks())

        @self.app.on_event("shutdown")
        async def _stop_background_tick():
            if self._tick_task:
                self._tick_task.cancel()
                try:
                    await self._tick_task
                except asyncio.CancelledError:
                    pass
                self._tick_task = None

    def _fresh_swarm(self):
        from tais_swarm_v6.engine.config import SwarmConfig
        from tais_swarm_v6.engine.core import SwarmV6
        s = SwarmV6(config=SwarmConfig(), seed=0)
        s.init_population(20)
        return s

    # ── helpers ──────────────────────────────────────────────

    def _build_snapshot(self) -> dict:
        """Full state snapshot consumed by SSE /stream and the WebSocket."""
        swarm = self.swarm
        motes = [m.to_dict() for m in swarm.motes]

        # Gather resources from ecosystem cells (sample ~200 richest cells)
        ec = swarm.world.ecosystem
        resources = []
        scored = []
        for (gx, gy), cell in ec.cells.items():
            best = max(cell.food, cell.water, cell.shelter_quality * 0.5)
            scored.append((best, gx, gy, cell))
        scored.sort(reverse=True)
        for best, gx, gy, cell in scored[:200]:
            if best < 0.4:
                break
            resources.append({
                "x": float(gx),
                "y": float(gy),
                "type": "FOOD" if cell.food > cell.water else "WATER",
                "amount": max(cell.food, cell.water),
                "shelter_quality": cell.shelter_quality,
            })

        # Count grammar rules across all motes (stored in genome.rules)
        all_rules = []
        for m in swarm.motes:
            if hasattr(m, 'genome') and hasattr(m.genome, 'rules'):
                for r in m.genome.rules:
                    all_rules.append(str(r.pattern))

        return {
            "tick": swarm.tick,
            "population": sum(1 for m in swarm.motes if m.alive),
            "motes": motes,
            "resources": resources,
            "predators": [],
            "predator_count": 0,
            "grammar_rules": list(set(all_rules)),
        }

    def _nearest_mote(self, x: float, y: float) -> object:
        best = None
        best_d = float("inf")
        for m in self.swarm.motes:
            if not m.alive:
                continue
            d = (m.x - x) ** 2 + (m.y - y) ** 2
            if d < best_d:
                best_d = d
                best = m
        return best

    # ── routes ───────────────────────────────────────────────

    def _setup_routes(self):
        app = self.app

        @app.get("/status")
        async def get_status():
            snap = self._build_snapshot()
            return {
                "version": "6.0.0",
                "tick": snap["tick"],
                "population": snap["population"],
                "motes_alive": snap["population"],
                "motes_total": len(self.swarm.motes),
                "predator_count": snap["predator_count"],
                "grammar_rules": snap["grammar_rules"],
                "running": self._running,
            }

        @app.get("/motes")
        async def list_motes():
            return [m.to_dict() for m in self.swarm.motes]

        @app.get("/motes/{mote_id}")
        async def get_mote(mote_id: int):
            for mote in self.swarm.motes:
                if mote.id == mote_id:
                    return mote.to_dict()
            raise HTTPException(status_code=404, detail="Mote not found")

        @app.get("/motes/{mote_id}/metacognition")
        async def get_mote_metacognition(mote_id: int):
            for mote in self.swarm.motes:
                if mote.id == mote_id:
                    return mote.metacog.to_dict()
            raise HTTPException(status_code=404, detail="Mote not found")

        @app.get("/motes/{mote_id}/causal")
        async def get_mote_causal(mote_id: int):
            for mote in self.swarm.motes:
                if mote.id == mote_id:
                    return mote.causal.to_dict()
            raise HTTPException(status_code=404, detail="Mote not found")

        @app.get("/motes/{mote_id}/planning")
        async def get_mote_planning(mote_id: int):
            for mote in self.swarm.motes:
                if mote.id == mote_id:
                    return mote.planner.to_dict()
            raise HTTPException(status_code=404, detail="Mote not found")

        @app.post("/player/demonstrate")
        async def player_demonstrate(request: Request):
            """
            Grounded teaching: click on the canvas at (x, y) to
            demonstrate *concept* via *channel*.
            The nearest mote picks up the demonstration.
            """
            data = await request.json()
            concept = data.get("concept", "FOOD")
            x = data.get("x", 32.0)
            y = data.get("y", 32.0)
            channel = data.get("channel", "SPEAK")
            tick = self.swarm.tick

            mote = self._nearest_mote(x, y)
            if mote is None:
                raise HTTPException(status_code=404, detail="No alive mote nearby")

            # Record causal link
            action = f"demonstrate_{concept.lower()}"
            if mote.causal is not None:
                mote.causal.record_action(tick, action, concept, True)
                mote.causal.compute_counterfactual(action, concept, tick)

            # Inject into metacognition as high-confidence observation
            if mote.metacog is not None:
                mote.metacog.record_outcome(
                    "demonstration",
                    prediction={"action": action, "concept": concept},
                    outcome={"result": "positive"},
                    correct=True,
                    tick=tick,
                )

            return {
                "status": "recorded",
                "mote_id": mote.id,
                "concept": concept,
                "x": x,
                "y": y,
                "channel": channel,
            }

        @app.post("/player/inject_concept")
        async def player_inject_concept(request: Request):
            """Directly inject a concept into a mote's causal model."""
            data = await request.json()
            mote_id = data.get("mote_id")
            concept = data.get("concept", "FOOD")
            mote = None
            for m in self.swarm.motes:
                if m.id == mote_id:
                    mote = m
                    break
            if mote is None:
                raise HTTPException(status_code=404, detail="Mote not found")

            if mote.causal is not None:
                mote.causal.record_action(
                    self.swarm.tick, "injected", concept, True
                )

            return {"status": "injected", "mote_id": mote_id, "concept": concept}

        @app.post("/player/query")
        async def player_query(request: Request):
            """Query a mote's causal belief about a concept."""
            data = await request.json()
            mote_id = data.get("mote_id")
            concept = data.get("concept", "FOOD")
            mote = None
            for m in self.swarm.motes:
                if m.id == mote_id:
                    mote = m
                    break
            if mote is None:
                raise HTTPException(status_code=404, detail="Mote not found")

            belief = None
            if mote.causal is not None:
                belief = mote.causal.get_causal_strength("injected", concept)

            return {
                "mote_id": mote_id,
                "concept": concept,
                "causal_strength": belief,
                "metacognition_confidence": mote.metacog.get_confidence() if mote.metacog is not None else None,
            }

        @app.post("/save")
        async def save_colony():
            snap = self._build_snapshot()
            self.swarm.persistence.save_colony("autosave", self.swarm.tick, snap)
            return {"status": "saved", "tick": self.swarm.tick}

        @app.post("/reset")
        async def reset_colony():
            self.swarm = self._fresh_swarm()
            return {"status": "reset", "tick": self.swarm.tick}

        @app.get("/events")
        async def get_events(
            event_type: Optional[str] = None,
            tick_start: Optional[int] = None,
            tick_end: Optional[int] = None,
            mote_id: Optional[int] = None,
            limit: int = 100,
        ):
            event_types = [event_type] if event_type else None
            events = self.swarm.event_bus.get_history(
                event_types=event_types,
                tick_start=tick_start,
                tick_end=tick_end,
                mote_id=mote_id,
                limit=limit,
            )
            return [e.to_dict() for e in events]

        @app.get("/stream")
        async def stream_events():
            """Server-Sent Events endpoint — emits a full state snapshot every tick."""
            async def event_generator():
                last_tick = -1
                while True:
                    current_tick = self.swarm.tick
                    if current_tick != last_tick:
                        snap = self._build_snapshot()
                        yield f"data: {json.dumps(snap)}\n\n"
                        last_tick = current_tick
                    await asyncio.sleep(0.25)

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self._websockets.append(websocket)
            try:
                while True:
                    data = await websocket.receive_text()
                    msg = json.loads(data)
                    cmd = msg.get("cmd", "")
                    if cmd == "ping":
                        await websocket.send_json({"type": "pong", "tick": self.swarm.tick})
                    elif cmd == "get_snapshot":
                        await websocket.send_json({"type": "snapshot", "data": self._build_snapshot()})
                    elif cmd == "get_mote":
                        mote_id = msg.get("mote_id")
                        for mote in self.swarm.motes:
                            if mote.id == mote_id:
                                await websocket.send_json({"type": "mote", "data": mote.to_dict()})
                                break
                    elif cmd == "step":
                        self.swarm.step()
                        await websocket.send_json({"type": "step_done", "tick": self.swarm.tick})
                    elif cmd == "subscribe_events":
                        await self._stream_events(websocket)
            except WebSocketDisconnect:
                if websocket in self._websockets:
                    self._websockets.remove(websocket)

        async def _stream_events(websocket: WebSocket):
            last_tick = self.swarm.tick
            try:
                while True:
                    events = self.swarm.event_bus.get_history(tick_start=last_tick + 1)
                    for event in events:
                        await websocket.send_json({"type": "event", "data": event.to_dict()})
                    if events:
                        last_tick = events[-1].tick
                    await asyncio.sleep(0.1)
            except WebSocketDisconnect:
                pass

        @app.get("/world")
        async def get_world():
            return self.swarm.world.to_dict()

        @app.get("/config")
        async def get_config():
            return self.swarm.config.to_dict()

    async def _run_ticks(self):
        while True:
            await asyncio.sleep(0.5)
            if self.swarm:
                try:
                    self.swarm.step()
                except Exception:
                    pass

    async def broadcast_event(self, event_json: str):
        dead = []
        for ws in self._websockets:
            try:
                await ws.send_text(event_json)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._websockets.remove(ws)

    def start(self):
        import uvicorn
        self._running = True
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")

    async def start_async(self):
        import uvicorn
        self._running = True
        config = uvicorn.Config(self.app, host=self.host, port=self.port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
