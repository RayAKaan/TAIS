# Global Fix Verification Report

**Date:** 2026-06-20  
**Commit:** `b5071f4` + local changes

---

## Summary

| Metric | Value |
|---|---|
| Unit tests | **381 passed, 0 failed** |
| Benchmark — Coding Refactor | **SUCCESS** (t=46) |
| Benchmark — Scientific Verification | **SUCCESS** (t=18) |
| Benchmark — Web Extraction | FAILED (t=100 horizon) |
| Pre-existing failures | None |

---

## Fixes Applied

### 1. Domain-Isolated Stats (`EpisodicMemory`)
- `_action_stats` keys changed from `name` to `(domain, name)` — prevents cross-domain action-value leakage.
- `action_value(name, domain)` and `action_risk(name, domain)` return domain-scoped values.
- `best_actions()`/`worst_actions()` handle tuple keys without crashing.
- `best_action_from_history()` passes `domain` to the lookup.

### 2. Evidence-Based Transfer Gating (`choose_action`)
- `gating_factor = exp(historical)` applied when `historical < -0.1`.
- Negative local experience suppresses the transfer boost for an action.
- Positive/neutral experience leaves gating at 1.0.
- Verified: gating correctly steers selection away from negatively experienced actions toward positive ones.

### 3. Pattern Recording Threshold
- Threshold lowered from 1.0 to **0.4** for real-world domains (`codesynt`, `webnav`, `negosim`, `sciex`) to capture patterns from smaller reward signals.
- Grid/rules keep 1.0 threshold.

### 4. Fail-Forward Exploration
- Exploration rate scales with prediction error: `uncertainty = min(0.2, err × 0.05)`.
- Capped at 50% max explore probability to prevent excessive random-walk.
- Helps escape local plateaus when the scoring system is stuck.

### 5. NegoSim Simulated Proposals Removed
- Removed 30%-random simulated proposals that caused flaky accept/reject tests.
- All multi-agent actions now work on explicitly created proposals.

### 6. Other Fixes
- `test_core.py`: Fixed pattern IDs in `test_pattern_matching` (unique IDs), removed `RealityGraph.validate()` test (API removed), fixed `test_compose_receive_audit_cycle` (uses `stats()` instead of removed `audit_utterance()`).
- `test_global_fix.py`: Added `_graph_fp()` helper (RealityGraph has no `.fingerprint()`), used `hashlib.md5(graph.summary())`.
- Integration tests: Added pretrain seeds for deterministic mote solve tests.

---

## Changset

```
 tais_core/domains/negosim.py |   9 +-   # removed simulated proposals
 tais_core/memory.py          |   9 +-   # domain thresholds + exploration
 tests/test_core.py           | 243 +++++ # rewrite with full coverage
 tests/test_global_fix.py     | 161 ++++ # new: domain stats + gating tests
 tests/test_codesynt.py       |  90 ++++ # new: CodeSynt domain tests
 tests/test_sciex.py          |  95 ++++ # new: SciEx domain tests
 tests/test_negosim.py        |  82 ++++ # new: NegoSim domain tests
 tests/test_webnav.py         | 103 ++++ # new: WebNav domain tests
```
