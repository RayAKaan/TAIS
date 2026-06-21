import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from tais_core.mote import UniversalMote, CognitiveConfig
from tais_core.llm_grounding import LLMGroundingEngine
from tais_core.domains.registry import load_domain
from tais_core.reality import Entity

app = FastAPI(title="TAIS Command Center")

# Global State
mote = UniversalMote(energy=1000)
mote.enable_cognitive_engines()
grounding = LLMGroundingEngine(provider="ollama")


class CommandRequest(BaseModel):
    command: str
    domain: str = "webnav"


class AgentResponse(BaseModel):
    explanation: str
    mote_id: int
    energy: float
    tick: int
    task_signal: Optional[str]
    graph_summary: Dict[str, Any]
    action_trace: List[Dict[str, Any]]
    graph_data: Dict[str, Any]


@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.post("/chat", response_model=AgentResponse)
async def handle_command(request: CommandRequest):
    global mote
    try:
        grounded_graph = grounding.ground_goal(request.command, domain=request.domain)

        if not grounded_graph.entities():
            return AgentResponse(
                explanation="STATUS: NO_GOAL_DETECTED. REASON: INPUT_NON_STRUCTURAL.",
                mote_id=mote.id, energy=mote.energy, tick=mote.age,
                task_signal=None, graph_summary={}, action_trace=[],
                graph_data={"nodes": [], "links": []}
            )

        world = load_domain(request.domain)
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

        trace = []
        final_cons = None
        for t in range(5):
            current_graph, cons, action = mote.step(world, current_graph, mote_position=pos, tick=mote.age)
            final_cons = cons
            if action:
                trace.append({"tick": mote.age, "action": action.name, "reward": round(cons.net, 2), "op": action.universal_op})
            if cons.task_signal == "TASK_SUCCESS":
                break

        # 4. SLM Narration with Graph Delta
        delta_info = {}
        if final_cons and final_cons.graph_delta:
            d = final_cons.graph_delta
            delta_info = {
                "added": [e.id for e in d.entities_added],
                "removed": list(d.entities_removed),
                "modified": [{"id": pair[1].id, "changes": dict(pair[1].properties)} for pair in d.entities_modified],
            }

        explanation = grounding.explain_consequence({
            "action": trace[-1]["action"] if trace else "none",
            "net": final_cons.net if final_cons else 0,
            "delta": delta_info,
            "success": final_cons.task_signal == "TASK_SUCCESS" if final_cons else False
        })

        nodes = [{"id": e.id, "type": e.etype} for e in current_graph.entities()]
        links = [{"source": r.source, "target": r.target, "type": r.rtype} for r in current_graph.relations()]

        return AgentResponse(
            explanation=explanation,
            mote_id=mote.id, energy=mote.energy, tick=mote.age,
            task_signal=final_cons.task_signal if final_cons else None,
            graph_summary=current_graph.summary(), action_trace=trace,
            graph_data={"nodes": nodes, "links": links}
        )
    except Exception as e:
        print(f"API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
