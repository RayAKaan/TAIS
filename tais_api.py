import json
import asyncio
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from tais_core.mote import UniversalMote
from tais_core.llm_grounding import LLMGroundingEngine
from tais_core.domains.registry import load_domain
from tais_core.reality import Entity
from tais_core.event_bus import EventBus, Event, EventType

app = FastAPI(title="TAIS Command Center")

app.mount("/v6", StaticFiles(directory="frontend/dist", html=True), name="v6_frontend")

grounding = LLMGroundingEngine(provider="ollama")

# ── Persistent mote (cross-request memory) ──
_mote_lock = asyncio.Lock()
_mote = UniversalMote(energy=1000)
_mote.enable_cognitive_engines()
_mote.enable_learned_role_compatibility()
event_bus = EventBus()
_websockets: List[WebSocket] = []


async def _broadcast_event(event: Event):
    dead: List[WebSocket] = []
    for ws in _websockets:
        try:
            await ws.send_json(event.to_dict())
        except Exception:
            dead.append(ws)
    for ws in dead:
        _websockets.remove(ws)


class CommandRequest(BaseModel):
    command: str
    domain: str = "webnav"
    source_code: Optional[str] = None
    target_code: Optional[str] = None
    expression: Optional[str] = None
    max_ticks: int = 10


class AgentResponse(BaseModel):
    explanation: str
    mote_id: int
    energy: float
    tick: int
    task_signal: Optional[str]
    graph_summary: Dict[str, Any]
    action_trace: List[Dict[str, Any]]
    graph_data: Dict[str, Any]
    patches: List[Dict[str, Any]] = []
    fixed_code: Optional[str] = None
    answer: Optional[Any] = None


@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/status")
async def get_status():
    async with _mote_lock:
        return {
            "ok": True,
            "version": "1.0.0",
            "mote_age": _mote.age,
            "mote_alive": _mote.alive,
            "mote_energy": _mote.energy,
            "patterns": len(_mote.memory.patterns),
            "episodes": len(_mote.memory.episodic),
        }


@app.post("/mote/reset")
async def reset_mote():
    global _mote
    async with _mote_lock:
        _mote = UniversalMote(energy=1000)
        _mote.enable_cognitive_engines()
        _mote.enable_learned_role_compatibility()
        return {"ok": True, "message": "Mote reset", "new_id": _mote.id}


@app.post("/chat", response_model=AgentResponse)
async def handle_command(request: CommandRequest):
    async with _mote_lock:
        mote = _mote
        try:
            grounded_graph = grounding.ground_goal(request.command, domain=request.domain)

            # ----- Build world -----
            if request.domain == "math":
                from tais_core.domains.math_world import MathWorld
                expr = request.expression or request.command
                world = MathWorld(expression_str=expr)
            elif request.source_code:
                from tais_core.domains.codesynt import CustomCodeWorld
                world = CustomCodeWorld(
                    source_code=request.source_code,
                    target_code=request.target_code or "",
                )
            else:
                world = load_domain(request.domain)

            current_graph = world.initial_graph()

            # ----- Merge grounded entities -----
            for ent in grounded_graph.entities():
                if ent.id not in [e.id for e in current_graph.entities()]:
                    current_graph.add_entity(ent)
            for rel in grounded_graph.relations():
                current_graph.add_relation(rel)

            all_ids = [e.id for e in current_graph.entities()]
            pos = "mote" if "mote" in all_ids else (
                  "nav" if "nav" in all_ids else (
                  "hyp1" if "hyp1" in all_ids else (
                  all_ids[0] if all_ids else "root")))

            trace: List[Dict[str, Any]] = []
            final_cons = None
            max_ticks = request.max_ticks

            for t in range(max_ticks):
                current_graph, cons, action = mote.step(
                    world, current_graph, mote_position=pos, tick=t)
                final_cons = cons
                if action:
                    trace.append({
                        "tick": t,
                        "action": action.name,
                        "reward": round(cons.net, 2),
                        "op": action.universal_op,
                    })
                    event_bus.emit(Event(EventType.ACTION_TAKEN, t, mote.id, {
                        "action": action.name, "reward": cons.net, "op": action.universal_op,
                    }))
                if cons.task_signal == "TASK_SUCCESS":
                    event_bus.emit(Event(EventType.TASK_SUCCESS, t, mote.id, {
                        "task_signal": cons.task_signal, "ticks": t + 1,
                    }))
                    break

            # ----- Build explanation -----
            delta_info = {}
            if final_cons and final_cons.graph_delta:
                d = final_cons.graph_delta
                delta_info = {
                    "added": [e.id for e in d.entities_added],
                    "removed": list(d.entities_removed),
                    "modified": [
                        {"id": pair[1].id, "changes": dict(pair[1].properties)}
                        for pair in d.entities_modified
                    ],
                }

            explanation = grounding.explain_consequence({
                "action": trace[-1]["action"] if trace else "none",
                "net": final_cons.net if final_cons else 0,
                "delta": delta_info,
                "success": final_cons.task_signal == "TASK_SUCCESS" if final_cons else False,
            })

            nodes = [{"id": e.id, "type": e.etype} for e in current_graph.entities()]
            links = [
                {"source": r.source, "target": r.target, "type": r.rtype}
                for r in current_graph.relations()
            ]

            patch_list: List[Dict[str, Any]] = []
            fixed_code: Optional[str] = None
            answer: Optional[Any] = None
            if hasattr(world, "patches") and world.patches:
                for p in world.patches:
                    patch_list.append(p.to_dict())
            if hasattr(world, "fixed_source") and world.fixed_source:
                fixed_code = world.fixed_source
            if hasattr(world, "answer") and world.answer is not None:
                answer = world.answer

            return AgentResponse(
                explanation=explanation,
                mote_id=mote.id,
                energy=mote.energy,
                tick=mote.age,
                task_signal=final_cons.task_signal if final_cons else None,
                graph_summary=current_graph.summary(),
                action_trace=trace,
                graph_data={"nodes": nodes, "links": links},
                patches=patch_list,
                fixed_code=fixed_code,
                answer=answer,
            )
        except Exception as e:
            print(f"API Error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Streaming endpoint (NDJSON) — real-time graph + action visualization
# ---------------------------------------------------------------------------
def _build_world(request: CommandRequest):
    """Shared world factory for /chat and /chat/stream."""
    if request.domain == "math":
        from tais_core.domains.math_world import MathWorld
        expr = request.expression or request.command
        return MathWorld(expression_str=expr)
    if request.source_code:
        from tais_core.domains.codesynt import CustomCodeWorld
        return CustomCodeWorld(
            source_code=request.source_code,
            target_code=request.target_code or "",
        )
    return load_domain(request.domain)


@app.post("/chat/stream")
async def handle_command_stream(request: CommandRequest):
    mote = _mote
    try:
        grounded_graph = grounding.ground_goal(request.command, domain=request.domain)
        world = _build_world(request)
        current_graph = world.initial_graph()

        for ent in grounded_graph.entities():
            if ent.id not in [e.id for e in current_graph.entities()]:
                current_graph.add_entity(ent)
        for rel in grounded_graph.relations():
            current_graph.add_relation(rel)

        all_ids = [e.id for e in current_graph.entities()]
        pos = "mote" if "mote" in all_ids else (
              "nav" if "nav" in all_ids else (
              "hyp1" if "hyp1" in all_ids else (
              all_ids[0] if all_ids else "root")))

        async def event_stream():
            nonlocal current_graph
            trace: List[Dict[str, Any]] = []
            final_cons = None
            max_ticks = request.max_ticks

            # yield initial state (tick 0)
            yield _tick_event(0, None, current_graph, mote, world)

            for t in range(max_ticks):
                async with _mote_lock:
                    current_graph, cons, action = mote.step(
                        world, current_graph, mote_position=pos, tick=t)
                final_cons = cons
                if action:
                    entry = {
                        "tick": t,
                        "action": action.name,
                        "reward": round(cons.net, 2),
                        "op": action.universal_op,
                    }
                    trace.append(entry)
                    event_bus.emit(Event(EventType.ACTION_TAKEN, t, mote.id, entry))

                yield _tick_event(t, action, current_graph, mote, world,
                                  trace=trace, task_signal=cons.task_signal)

                if cons.task_signal == "TASK_SUCCESS":
                    event_bus.emit(Event(EventType.TASK_SUCCESS, t, mote.id, {
                        "task_signal": cons.task_signal, "ticks": t + 1,
                    }))
                    break

                await asyncio.sleep(0.3)

            # ---- final event ----
            delta_info = {}
            if final_cons and final_cons.graph_delta:
                d = final_cons.graph_delta
                delta_info = {
                    "added": [e.id for e in d.entities_added],
                    "removed": list(d.entities_removed),
                    "modified": [
                        {"id": pair[1].id, "changes": dict(pair[1].properties)}
                        for pair in d.entities_modified
                    ],
                }
            explanation = grounding.explain_consequence({
                "action": trace[-1]["action"] if trace else "none",
                "net": final_cons.net if final_cons else 0,
                "delta": delta_info,
                "success": final_cons.task_signal == "TASK_SUCCESS" if final_cons else False,
            })

            patch_list: List[Dict[str, Any]] = []
            fixed_code: Optional[str] = None
            answer: Optional[Any] = None
            if hasattr(world, "patches") and world.patches:
                for p in world.patches:
                    patch_list.append(p.to_dict())
            if hasattr(world, "fixed_source") and world.fixed_source:
                fixed_code = world.fixed_source
            if hasattr(world, "answer") and world.answer is not None:
                answer = world.answer

            yield json.dumps({
                "type": "complete",
                "explanation": explanation,
                "mote_id": mote.id,
                "energy": mote.energy,
                "tick": mote.age,
                "task_signal": final_cons.task_signal if final_cons else None,
                "graph_summary": current_graph.summary(),
                "action_trace": trace,
                "graph_data": _graph_data(current_graph),
                "patches": patch_list,
                "fixed_code": fixed_code,
                "answer": answer,
            }) + "\n"

        return StreamingResponse(event_stream(), media_type="application/x-ndjson")

    except Exception as e:
        print(f"API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _graph_data(graph):
    return {
        "nodes": [{"id": e.id, "type": e.etype} for e in graph.entities()],
        "links": [
            {"source": r.source, "target": r.target, "type": r.rtype}
            for r in graph.relations()
        ],
    }


def _tick_event(tick, action, graph, mote, world, trace=None, task_signal=None):
    ev = {
        "type": "tick",
        "tick": tick,
        "graph_data": _graph_data(graph),
        "telemetry": {"energy": mote.energy, "age": mote.age, "id": mote.id},
    }
    if action:
        ev["action"] = {
            "name": action.name,
            "op": action.universal_op,
        }
    if trace:
        ev["action_trace"] = trace
    if task_signal:
        ev["task_signal"] = task_signal
    return json.dumps(ev) + "\n"


# ---------------------------------------------------------------------------
# V6-inspired endpoints — mote inspection, teaching, WebSocket, SSE
# ---------------------------------------------------------------------------

@app.get("/motes")
async def list_motes():
    async with _mote_lock:
        return [_mote.metrics()]


@app.get("/motes/{mote_id}")
async def get_mote(mote_id: int):
    async with _mote_lock:
        if _mote.id != mote_id:
            raise HTTPException(status_code=404, detail="Mote not found")
        return _mote.metrics()


@app.get("/motes/{mote_id}/metacognition")
async def get_mote_metacognition(mote_id: int):
    async with _mote_lock:
        if _mote.id != mote_id:
            raise HTTPException(status_code=404, detail="Mote not found")
        if _mote.metacog is None:
            raise HTTPException(status_code=404, detail="Metacognition not enabled")
        return _mote.metacog.to_dict()


@app.get("/motes/{mote_id}/causal")
async def get_mote_causal(mote_id: int):
    async with _mote_lock:
        if _mote.id != mote_id:
            raise HTTPException(status_code=404, detail="Mote not found")
        if _mote.causal is None:
            raise HTTPException(status_code=404, detail="Causal engine not enabled")
        return _mote.causal.to_dict()


@app.get("/motes/{mote_id}/planning")
async def get_mote_planning(mote_id: int):
    async with _mote_lock:
        if _mote.id != mote_id:
            raise HTTPException(status_code=404, detail="Mote not found")
        if _mote.planner is None:
            raise HTTPException(status_code=404, detail="Planner not enabled")
        return _mote.planner.to_dict()


@app.get("/events")
async def get_events(
    event_type: Optional[str] = None,
    tick_start: Optional[int] = None,
    tick_end: Optional[int] = None,
    mote_id: Optional[int] = None,
    limit: int = 100,
):
    et = [EventType[event_type]] if event_type else None
    events = event_bus.get_history(
        event_types=et,
        tick_start=tick_start,
        tick_end=tick_end,
        mote_id=mote_id,
        limit=limit,
    )
    return [e.to_dict() for e in events]


@app.post("/player/demonstrate")
async def player_demonstrate(request: Request):
    """Grounded teaching: demonstrate a concept to the mote."""
    data = await request.json()
    concept = data.get("concept", "GOOD")
    tick = _mote.age

    async with _mote_lock:
        if _mote.causal is not None:
            action = f"demonstrate_{concept.lower()}"
            _mote.causal.record_action(tick, action, concept, True)
            _mote.causal.compute_counterfactual(action, concept, tick)

        if _mote.metacog is not None:
            _mote.metacog.record_outcome(
                "demonstration",
                prediction={"action": "demonstrate", "concept": concept},
                outcome={"result": "positive"},
                correct=True,
                tick=tick,
            )

    event_bus.emit(Event(EventType.TEACHING, tick, _mote.id, {
        "concept": concept, "type": "demonstrate",
    }))

    return {"status": "recorded", "mote_id": _mote.id, "concept": concept}


@app.post("/player/inject_concept")
async def player_inject_concept(request: Request):
    """Directly inject a concept into the mote's causal model."""
    data = await request.json()
    concept = data.get("concept", "GOOD")
    async with _mote_lock:
        if _mote.causal is not None:
            _mote.causal.record_action(_mote.age, "injected", concept, True)
        return {"status": "injected", "mote_id": _mote.id, "concept": concept}


@app.post("/player/query")
async def player_query(request: Request):
    """Query the mote's causal belief about a concept."""
    data = await request.json()
    concept = data.get("concept", "SUCCESS")
    async with _mote_lock:
        belief = None
        if _mote.causal is not None:
            belief = _mote.causal.get_max_causal_strength(concept)
        return {
            "mote_id": _mote.id,
            "concept": concept,
            "causal_strength": belief,
            "metacognition_confidence": _mote.metacog.get_confidence() if _mote.metacog is not None else None,
        }


@app.get("/stream")
async def stream_events():
    """SSE endpoint — emits full mote snapshot on each tick."""
    async def event_generator():
        last_tick = -1
        while True:
            async with _mote_lock:
                current_tick = _mote.age
            if current_tick != last_tick:
                async with _mote_lock:
                    snap = {
                        "type": "snapshot",
                        "data": _mote.metrics(),
                    }
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
    _websockets.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            cmd = msg.get("cmd", "")
            if cmd == "ping":
                await websocket.send_json({"type": "pong", "tick": _mote.age})
            elif cmd == "get_snapshot":
                async with _mote_lock:
                    snap = {
                        "tick": _mote.age,
                        "energy": _mote.energy,
                        "alive": _mote.alive,
                        "memory": _mote.memory.summary(),
                        "metrics": _mote.metrics(),
                    }
                await websocket.send_json({"type": "snapshot", "data": snap})
            elif cmd == "get_mote":
                async with _mote_lock:
                    await websocket.send_json({"type": "mote", "data": _mote.metrics()})
            elif cmd == "step":
                raise HTTPException(status_code=400, detail="Use POST /chat for mote steps")
    except WebSocketDisconnect:
        if websocket in _websockets:
            _websockets.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
