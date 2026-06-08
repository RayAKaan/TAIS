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
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
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
        self._setup_routes()

    def _setup_routes(self):
        app = self.app

        @app.get("/status")
        async def get_status():
            return {
                "version": "6.0.0",
                "tick": self.swarm.tick,
                "motes_alive": sum(1 for m in self.swarm.motes if m.alive),
                "motes_total": len(self.swarm.motes),
                "population": len(self.swarm.motes),
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
        async def player_demonstrate(data: dict):
            mote_id = data.get("mote_id")
            action = data.get("action", "move")
            concept = data.get("concept", "FOOD")
            outcome = data.get("outcome", "positive")
            tick = self.swarm.tick

            mote = None
            for m in self.swarm.motes:
                if m.id == mote_id:
                    mote = m
                    break
            if mote is None:
                raise HTTPException(status_code=404, detail="Mote not found")

            # Record the demonstration in the mote's causal engine
            positive = outcome == "positive"
            mote.causal.record_action(tick, action, concept, positive)
            mote.causal.compute_counterfactual(action, concept, tick)

            # Also record in metacognition as a high-confidence observation
            mote.metacog.record_outcome(
                "demonstration",
                prediction={"action": action, "concept": concept},
                outcome={"result": outcome},
                correct=positive,
                tick=tick,
            )

            return {
                "status": "recorded",
                "mote_id": mote_id,
                "action": action,
                "concept": concept,
                "outcome": outcome,
            }

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
