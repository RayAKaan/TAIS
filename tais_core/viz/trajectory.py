from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from tais_core import Consequence, RealityGraph, Transformation, UniversalMote, WorldInterface


def graph_snapshot_dict(graph: RealityGraph) -> dict:
    entities = []
    for e in graph.entities():
        entities.append({"id": e.id, "type": e.etype, "properties": dict(e.properties)})
    relations = []
    for r in graph.relations():
        relations.append({
            "source": r.source,
            "type": r.rtype,
            "target": r.target,
            "properties": dict(r.properties),
            "directed": r.directed,
        })
    return {"entities": entities, "relations": relations}


def record_mote_trajectory(
    world: WorldInterface,
    graph: RealityGraph,
    mote: UniversalMote,
    mote_position: Any = None,
    ticks: int = 10,
) -> list[dict]:
    records: list[dict] = []
    g = graph
    for tick in range(ticks):
        g, cons, action = mote.step(world, g, mote_position=mote_position, tick=tick)
        record = {
            "tick": tick,
            "action": action.name if action else None,
            "net": cons.net,
            "reward": cons.reward,
            "penalty": cons.penalty,
            "valid": cons.valid,
            "task_signal": cons.task_signal,
            "concept_signals": dict(cons.concept_signals),
            "prediction_error": cons.prediction_error,
            "energy": mote.energy,
            "alive": mote.alive,
            "graph": graph_snapshot_dict(g),
        }
        records.append(record)
    return records


def save_trajectory_json(records: list[dict], path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, default=str)
    return p


def save_trajectory_html(records: list[dict], path: str | Path, title: str = "TAIS Mote Trajectory") -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    json_str = json.dumps(records, indent=2, default=str)
    html = _build_html_viewer(json_str, title)
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)
    return p


def _build_html_viewer(json_data: str, title: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; padding: 20px; }}
h1 {{ font-size: 1.4em; margin-bottom: 12px; }}
#controls {{ display: flex; align-items: center; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }}
#controls button {{ padding: 6px 16px; font-size: 1em; cursor: pointer; }}
#controls span {{ font-weight: bold; }}
#tick-info {{ background: #fff; border-radius: 8px; padding: 16px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.12); }}
#tick-info h2 {{ font-size: 1.1em; margin-bottom: 8px; }}
#tick-info table {{ width: 100%; border-collapse: collapse; }}
#tick-info td, #tick-info th {{ text-align: left; padding: 4px 8px; border-bottom: 1px solid #eee; font-size: 0.85em; }}
#tick-info th {{ width: 140px; color: #666; }}
#graph-view {{ background: #fff; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.12); }}
#graph-view h2 {{ font-size: 1.1em; margin-bottom: 8px; }}
#graph-view h3 {{ font-size: 0.95em; margin: 8px 0 4px; color: #555; }}
#graph-view ul {{ list-style: none; font-size: 0.82em; font-family: monospace; }}
#graph-view li {{ padding: 2px 0; }}
.good {{ color: #2e7d32; }}
.bad {{ color: #c62828; }}
.neutral {{ color: #555; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div id="controls">
  <button id="prev-btn">&larr; Prev</button>
  <span id="tick-label">Tick 0 / {_count_records(json_data)}</span>
  <button id="next-btn">Next &rarr;</button>
</div>
<div id="tick-info"></div>
<div id="graph-view"></div>
<script>
var data = {json_data};
var current = 0;

function render(idx) {{
  var rec = data[idx];
  if (!rec) return;
  document.getElementById('tick-label').textContent = 'Tick ' + idx + ' / ' + (data.length - 1);
  var info = document.getElementById('tick-info');
  var action = rec.action || '(none)';
  var valence = rec.net > 0.5 ? 'good' : (rec.net < -0.5 ? 'bad' : 'neutral');
  info.innerHTML = '<h2>Tick ' + idx + '</h2>' +
    '<table>' +
    '<tr><th>Action</th><td>' + action + '</td></tr>' +
    '<tr><th>Net</th><td class="' + valence + '">' + rec.net.toFixed(3) + '</td></tr>' +
    '<tr><th>Reward</th><td>' + rec.reward.toFixed(3) + '</td></tr>' +
    '<tr><th>Penalty</th><td>' + rec.penalty.toFixed(3) + '</td></tr>' +
    '<tr><th>Energy</th><td>' + rec.energy.toFixed(2) + '</td></tr>' +
    '<tr><th>Alive</th><td>' + rec.alive + '</td></tr>' +
    '<tr><th>Task Signal</th><td>' + (rec.task_signal || '(none)') + '</td></tr>' +
    '<tr><th>Prediction Error</th><td>' + rec.prediction_error.toFixed(4) + '</td></tr>' +
    '<tr><th>Concepts</th><td>' + JSON.stringify(rec.concept_signals) + '</td></tr>' +
    '</table>';
  var gv = document.getElementById('graph-view');
  var ents = rec.graph.entities || [];
  var rels = rec.graph.relations || [];
  var el = '<h2>Graph Snapshot</h2>';
  el += '<h3>Entities (' + ents.length + ')</h3><ul>';
  for (var i = 0; i < ents.length; i++) {{
    var e = ents[i];
    el += '<li>' + e.id + ' [' + e.type + '] ' + JSON.stringify(e.properties) + '</li>';
  }}
  el += '</ul><h3>Relations (' + rels.length + ')</h3><ul>';
  for (var j = 0; j < rels.length; j++) {{
    var r = rels[j];
    el += '<li>' + r.source + ' --[' + r.type + ']--> ' + r.target + ' ' + JSON.stringify(r.properties) + '</li>';
  }}
  el += '</ul>';
  gv.innerHTML = el;
}}

document.getElementById('prev-btn').addEventListener('click', function() {{
  if (current > 0) {{ current--; render(current); }}
}});
document.getElementById('next-btn').addEventListener('click', function() {{
  if (current < data.length - 1) {{ current++; render(current); }}
}});

render(0);
</script>
</body>
</html>"""


def _count_records(json_data: str) -> int:
    try:
        arr = json.loads(json_data)
        return len(arr) - 1 if arr else 0
    except Exception:
        return 0
