# Changelog

## 2026-06-22: Structural Transfer v2 — Blocker Removal & Cleanup

### Breaking Changes
- **Removed `role_hint` from all 38 Transformations** across 10 domain files (negosim, webnav, codesynt, sciex, hazard, logic, math_world, python_ast, code_repair, elementary_science). The role_hint field remains on the `Transformation` dataclass for backward compatibility but is no longer set by any domain.
- **Removed `_DISCOVERED_MAPPING` JSON override** from `memory.py`. The hand-crafted mapping file (`discovered_role_mapping.json`) is deleted.
- **Removed `continuity_boost = 10.0`** from `mote.py` — this +10.0 repeat-last-action bias drowned all transfer signals.
- **Removed `analogy_bias * 0.35` damping** on structural v2 boosts — structural signal now enters score at full strength.

### New: Structural Transfer v2 (Genuine Topology-Based Transfer)
- `tais_core/role_discovery.py` — Role Discovery Engine: clusters (structural_key, outcome_valence) triples without role labels.
- `tais_core/structural_similarity.py` — Weisfeiler-Lehman graph kernel with degree-based tie-breaking for surface-invariant similarity.
- `tais_core/domains/procedural.py` — ProceduralDomainFactory: generates domain pairs with controllable overlap/complexity/surface distance.
- `tais_core/analogy_engine.py` — StructuralAnalogyEngine: subgraph matching via neighborhood hash fingerprints and structural role signatures.
- `tais_core/policy_transfer.py` — CompositionalPolicy + HierarchicalPlannerV2: multi-step planning over transferred action sequences.
- Integrated into `tais_core/mote.py` via `enable_structural_transfer()` — opt-in, does not affect legacy behavior.
- Updated `tais_core/__init__.py` exports.

### Fixes
- **Policy extraction bug**: `learn_from_episodes()` received 1 episode per call, so `len(seq) >= 2` could never trigger. Added internal episode buffer with sliding window; lowered `min_sequence_reward` from 3.0 to 1.0 for practical reward scales. Policy sequences now extract correctly (101 in validation, up from 0).
- **WL kernel variable-shadowing**: self-similarity used leaked hash accumulator from outer loop. Similarity now correctly computes per-iteration.

### Cleanup
- Deleted `discovered_role_mapping.json` (unused after _DISCOVERED_MAPPING removal).
- Removed `ACTION_ROLES` list from `memory.py` (dead code).
- Removed `import os` from `memory.py` (only used by deleted _MAPPING_FILE loading).
- Updated `tests/transfer/test_cross_domain_transfer.py` to use `enable_structural_transfer()` instead of legacy `transfer_prior_uses` checks.
- Added `tests/core/test_structural_transfer_v2.py` — 27 tests covering all v2 components plus acid test for surface independence.
- Added `scripts/validate_structural_transfer.py` — 4 experiment runners for zero-annotation transfer, surface independence, overlap scaling, and cross-domain analytics.

### Validation Results
- **Zero-annotation transfer advantage**: +3.00 (pretrained 7.13 vs fresh 4.13)
- **Surface independence**: 8.0% difference between low-surface and high-surface variants
- **Scaling with overlap**: peaks at +9.45 advantage at 0.7 overlap
- **All 396 tests pass** (369 original + 27 new) — zero regressions
