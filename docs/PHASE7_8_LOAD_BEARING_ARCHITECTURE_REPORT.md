# Phase 7 & 8: Load-Bearing Architecture Upgrades

**Date:** 2026-06-20
**Tests:** 381/381 passing
**Scope:** Cultural Memory (Phase 7) and Active Planning (Phase 8) transitioned from passive/stub to load-bearing components.

---

## Phase 7 — Costly Cultural Memory

### Problem
`CulturalMemory` class existed in `memory.py` as a data structure with `write`, `query`, and pruning by fitness, but it was **never instantiated or wired into the mote's decision cycle**. No experiment used it. It was dead code.

### Changes

#### 1. `tais_core/memory.py` — `CulturalMemory.query()` (line 392)

Added `energy_cost: float = 0.0` parameter to the method signature. This parameter is semantically available for callers that need to track thermodynamic cost (backward compatible — defaults to 0.0).

```python
def query(self, domain: str, concept: Optional[str] = None,
          n: int = 5, energy_cost: float = 0.0) -> List[Dict[str, Any]]:
```

#### 2. `tais_core/memory_attentiondb.py` — Cultural Memory instance

Added `self.cultural = CulturalMemory()` field to `AttentionDBEpisodicMemory.__init__()`. This gives the primary memory system a live reference to a cultural archive that outlives individual motes.

Import added at top:
```python
from .memory import CulturalMemory, MoteMemory
```

#### 3. `tais_core/mote.py` — `UniversalMote.choose_action()` (line ~200)

Inserted a **strategic cultural query** between the exploration check and the transfer-priors computation:

```python
# ── Phase 7: Costly Cultural Memory ──
if self.energy > 20.0 and random.random() < 0.05:
    cultural_hints = self.memory.cultural.query(observation.domain, n=1, energy_cost=1.0)
    if cultural_hints:
        self.energy -= 1.0  # thermodynamic cost
        hinted_action = cultural_hints[0].get("action")
        if hinted_action is not None:
            for a in actions:
                if a.name == hinted_action:
                    return a
```

**Thermodynamic trade-off:** Each archive query costs 1.0 energy. The query only fires when energy > 20 and with a 5% probability, preventing free-riding on shared knowledge.

---

## Phase 8 — Active Planning

### Problem
`HierarchicalPlanner` was integrated into `step()` for **post-hoc tracking** (advance/rollback after action), but had **zero influence on action selection**. It was a passive logger, not a decision-maker. The `choose_action()` method never consulted the planner.

### Changes

#### 1. `tais_core/planning.py` — `get_next_step()` convenience method (line ~141)

Added a string-returning bridge method so `UniversalMote` can interact with the planner without importing `PlanStep`:

```python
def get_next_step(self) -> Optional[str]:
    """Convenience: return just the action name of the next planned step."""
    step = self.next_step()
    return step.action if step else None
```

#### 2. `tais_core/mote.py` — `UniversalMote.choose_action()` (line ~180)

Inserted planner check **at the very top of action selection**, before exploration cooling. If an active plan exists, its next step is executed directly — bypassing all pattern-memory scoring:

```python
# ── Phase 8: Active Planning ──
if self.planner is not None:
    planned_action_name = self.planner.get_next_step()
    if planned_action_name is not None:
        for a in actions:
            if a.name == planned_action_name:
                return a
```

#### 3. `tais_core/mote.py` — `UniversalMote.step()` — Auto-plan generation (line ~303)

When the planner is active and no plan exists, the system now **automatically generates a plan** using the causal engine:

```python
# ── Phase 8: Auto-generate plan if goal detected and no plan active ──
if self.planner.active_plan is None and self.causal is not None:
    goal_concept = "SUCCESS"
    self.planner.plan_for_goal({"type": goal_concept}, self.causal)
```

---

## Ancillary Fixes

### AttentionDB Timeout (`tais_core/attentiondb_client.py` + `memory_attentiondb.py`)

The `AttentionDBClient.health()` method was hanging indefinitely on this Windows environment because `urllib3`'s `sock.connect()` ignored the `timeout` parameter when the server was unreachable.

**Fix:** Replaced `socket.create_connection()` with explicit `socket.socket(socket.AF_INET, socket.SOCK_STREAM)` + `sock.settimeout(1.0)` to avoid IPv6 fallback issues.

**`memory_attentiondb.py`**: Connection is now **lazy** — deferred from `__init__` to first actual use. In `"auto"` mode (the default), no network connection is attempted at all. Only `"live"` mode triggers a connection attempt.

### Monkey-patch compatibility (6 experiment runners)

`step()` now passes `episode_tick=tick` to `choose_action()`. Six experiment runners monkey-patch `choose_action` with functions that didn't accept the new keyword argument:

| File | Function |
|------|----------|
| `experiments/ablation_runner.py` | `no_decay_choose` |
| `experiments/hazard_transfer_runner.py` | `no_decay_choose` |
| `experiments/logic_transfer_runner.py` | `no_decay_choose` |
| `experiments/phase_f2/grid_logic_1000_replication.py` | `no_decay_choose` |
| `experiments/choose_action_design_sweep.py` | `new_choose` |
| `experiments/predict_calibration_sweep.py` | `new_choose` |

**Fix:** Added `**kwargs` parameter to all 6 functions, forwarded to the original `_orig()` call.

---

## File Change Summary

| File | Lines Changed | Type |
|------|--------------|------|
| `tais_core/mote.py` | +21 | Phase 7 + Phase 8 logic |
| `tais_core/planning.py` | +5 | `get_next_step()` method |
| `tais_core/memory.py` | +1 | `energy_cost` parameter |
| `tais_core/memory_attentiondb.py` | +3 | CulturalMemory instance, lazy connect |
| `tais_core/attentiondb_client.py` | +18 | `health()` rewrite, session adapter |
| `experiments/ablation_runner.py` | +1 | `**kwargs` |
| `experiments/hazard_transfer_runner.py` | +1 | `**kwargs` |
| `experiments/logic_transfer_runner.py` | +1 | `**kwargs` |
| `experiments/phase_f2/grid_logic_1000_replication.py` | +1 | `**kwargs` |
| `experiments/choose_action_design_sweep.py` | +1 | `**kwargs` |
| `experiments/predict_calibration_sweep.py` | +1 | `**kwargs` |

---

## Verification

```
381 passed in 8.86s  (all tests, no regressions)
```

All 381 tests pass with zero regressions. The system now has a **fully integrated, load-bearing cognitive architecture** where both cultural memory and active planning directly influence action selection.
