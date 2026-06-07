"""Rule-satisfaction validation domain (Phase 2 hardened).

Phase 2 changes vs the v1 RuleWorld (Phase 0 baseline):

1.  An explicit ``TARGET`` entity is added so ``evaluate()`` and the new
    ``task_signal`` channel measure *task completion*, not "any positive
    consequence". This was the metric-leak that made the original ablation
    table read ``no_pattern_transfer`` as identical to ``full``.

2.  Reward structure is sharpened so the only way to score the headline
    reward is to actually derive the target fact:

        apply_implication   = +4.0   on first successful derivation
        apply_implication   = +0.05  on re-application (small, near-neutral)
        verify_rule         = +0.10  small bookkeeping reward (was +1.5!)
        verify_rule (bad)   = -1.0   smaller penalty than v1
        random_assert       = -3.0   unchanged
        invalid             = -1.0   unchanged

3.  Every ``act()`` return value carries a ``task_signal``:

        TASK_SUCCESS  — the target fact has just been derived (first time)
        TASK_PROGRESS — verify confirmed a relevant rule
        TASK_FAILURE  — random_assert or invalid op
        None          — verify on irrelevant rule

    Runners use ``cons.task_signal == "TASK_SUCCESS"`` for the strict
    ``first_apply_implication_tick`` metric without needing to know the action
    name.  This is the substrate used by the Phase 1 ablation v2 runner.

4.  Three new graph variants are exported alongside the original:

        make_rule_graph         — the legacy single-implication graph (kept for
                                  backwards compatibility with v1 tests)
        make_rule_graph_easy    — same as legacy but with the explicit TARGET
        make_rule_graph_chain   — A -> B -> C; success requires two derivations
        make_rule_graph_distractor — one true implication + 4 irrelevant rules
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..reality import (
    Consequence,
    Entity,
    RealityGraph,
    Relation,
    Transformation,
    WorldInterface,
)


# ─── GRAPH BUILDERS ──────────────────────────────────────────────────────────

def _add_target_marker(g: RealityGraph, target_id: str) -> RealityGraph:
    """Mark which fact id the world wants the mote to derive."""
    g.add_entity(Entity("TARGET", "TARGET", {"derive_id": target_id}))
    return g


def make_rule_graph() -> RealityGraph:
    """Legacy v1 single-implication graph plus explicit target marker.

    Kept callable with the original name so existing tests/experiments still
    work; new code should prefer the named variants below.
    """
    g = RealityGraph("rules", "modus_ponens_toy")
    g.add_entity(Entity("fact_a", "FACT", {"truth": True}))
    g.add_entity(Entity("fact_b", "FACT", {"truth": True}))
    g.add_entity(Entity("rule_ab", "RULE", {"kind": "implies"}))
    g.add_relation(Relation("fact_a", "SATISFIES", "rule_ab"))
    g.add_relation(Relation("rule_ab", "IMPLIES", "fact_b"))
    return _add_target_marker(g, "fact_b_known")


def make_rule_graph_easy() -> RealityGraph:
    """Alias for the single-implication graph used by RuleWorldEasy."""
    return make_rule_graph()


def make_rule_graph_chain() -> RealityGraph:
    """A → B → C. Target: derive ``fact_c_known``.

    Used by RuleWorldChain. A mote that only ever fires one apply_implication
    can never complete this task; the chain explicitly tests multi-step credit
    assignment.
    """
    g = RealityGraph("rules", "modus_ponens_chain")
    g.add_entity(Entity("fact_a", "FACT", {"truth": True}))
    g.add_entity(Entity("fact_b", "FACT", {"truth": True}))
    g.add_entity(Entity("fact_c", "FACT", {"truth": True}))
    g.add_entity(Entity("rule_ab", "RULE", {"kind": "implies"}))
    g.add_entity(Entity("rule_bc", "RULE", {"kind": "implies"}))
    g.add_relation(Relation("fact_a", "SATISFIES", "rule_ab"))
    g.add_relation(Relation("rule_ab", "IMPLIES", "fact_b"))
    g.add_relation(Relation("fact_b", "SATISFIES", "rule_bc"))
    g.add_relation(Relation("rule_bc", "IMPLIES", "fact_c"))
    return _add_target_marker(g, "fact_c_known")


def make_rule_graph_distractor() -> RealityGraph:
    """One satisfied implication plus four irrelevant rules.

    Tests whether the mote can locate the right rule among distractors. The
    target is the same (``fact_b_known``) as the easy graph.
    """
    g = RealityGraph("rules", "modus_ponens_distractor")
    g.add_entity(Entity("fact_a", "FACT", {"truth": True}))
    g.add_entity(Entity("fact_b", "FACT", {"truth": True}))
    g.add_entity(Entity("rule_ab", "RULE", {"kind": "implies"}))
    g.add_relation(Relation("fact_a", "SATISFIES", "rule_ab"))
    g.add_relation(Relation("rule_ab", "IMPLIES", "fact_b"))
    # distractors: rules whose antecedents are not satisfied
    for i, (ant, cons) in enumerate([("x", "y"), ("p", "q"), ("m", "n"), ("u", "v")]):
        g.add_entity(Entity(f"fact_{ant}", "FACT", {"truth": False}))
        g.add_entity(Entity(f"fact_{cons}", "FACT", {"truth": True}))
        g.add_entity(Entity(f"rule_{ant}{cons}", "RULE", {"kind": "implies"}))
        g.add_relation(Relation(f"rule_{ant}{cons}", "IMPLIES", f"fact_{cons}"))
        # NB: no SATISFIES edge — antecedent is not satisfied
    return _add_target_marker(g, "fact_b_known")


# ─── WORLD ───────────────────────────────────────────────────────────────────

# Phase 2 reward constants — pulled out so ablation/sensitivity studies can
# sweep them without editing the act() body.
APPLY_REWARD_FIRST = 4.0     # first successful derivation of the target
APPLY_REWARD_REPEAT = 0.05   # re-applying after success: near-neutral
VERIFY_REWARD = 0.02         # was 1.5 in v1; the metric-leak source.
                             # Set so 100 verifies (any plausible horizon)
                             # still pay less than one true apply_implication.
VERIFY_PENALTY = 1.0         # smaller than v1's 2.0
RANDOM_ASSERT_PENALTY = 3.0
INVALID_PENALTY = 1.0


class RuleWorld(WorldInterface):
    """Single-implication RuleWorld with the Phase 2 hardened reward + target.

    Backwards compatible: defaults to the legacy graph shape, but ``evaluate``
    and ``act`` now consult an optional TARGET entity. If a graph has no
    TARGET marker (very old callers), behavior degrades to "derive
    fact_b_known", same as v1.
    """

    domain_name = "rules"

    def _target_id(self, graph: RealityGraph) -> str:
        tgt = graph.get_entity("TARGET")
        if tgt is None:
            return "fact_b_known"
        return tgt.get("derive_id", "fact_b_known")

    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        # Position is a rule entity id; widen to 2 hops so chains/distractors
        # at least surface the antecedents/consequents.
        if mote_position and graph.get_entity(mote_position) is not None:
            return graph.neighborhood(mote_position, hops=2)
        return graph

    def valid_actions(self, graph: RealityGraph, mote_state: Dict) -> List[Transformation]:
        return [
            Transformation("apply_implication", self.domain_name, "TRANSFORM", base_cost=0.4),
            Transformation("verify_rule", self.domain_name, "VERIFY", base_cost=0.2),
            Transformation("random_assert", self.domain_name, "MUTATE", base_cost=0.5),
        ]

    # ── internals ────────────────────────────────────────────────────────────

    def _try_derive(self, graph: RealityGraph) -> Tuple[Optional[RealityGraph], Optional[str]]:
        """Derive any inferrable fact_*_known. Returns (new_graph, derived_id)
        or (None, None) if nothing new could be derived this step. Supports
        chained graphs: derives the first IMPLIES whose antecedent has a
        SATISFIES edge and whose consequent does not yet have a _known form.
        """
        for rel in graph.relations("IMPLIES"):
            rule_id, fact_id = rel.source, rel.target
            # require the rule to be satisfied
            satisfied = any(
                r.rtype == "SATISFIES" and r.target == rule_id
                for r in graph.relations("SATISFIES")
            )
            if not satisfied:
                continue
            known_id = f"{fact_id}_known"
            if graph.get_entity(known_id):
                continue  # already derived
            after = graph.snapshot()
            after.add_entity(Entity(known_id, "FACT", {"truth": True, "derived": True}))
            after.add_relation(Relation(fact_id, "SUPPORTS", known_id))
            # If we just derived something whose entity id appears as the
            # antecedent of another rule, also add the SATISFIES edge from
            # the derived fact so chains can progress next tick.
            for next_rel in after.relations("IMPLIES"):
                next_rule = next_rel.source
                # Is `fact_id` the named antecedent of next_rule? Check via
                # an existing SATISFIES edge keyed to fact_id; if absent but
                # the rule conceptually points to fact_id's downstream chain,
                # the chain builder already added the right SATISFIES edges.
                _ = next_rule  # no-op; chain SATISFIES edges are pre-built
            return after, known_id
        return None, None

    # ── main act ─────────────────────────────────────────────────────────────

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict) -> Tuple[RealityGraph, Consequence]:
        target_id = self._target_id(graph)

        if transformation.name == "apply_implication":
            new_graph, derived_id = self._try_derive(graph)
            if new_graph is None:
                # Nothing new to derive — already complete or no satisfied rule.
                if graph.get_entity(target_id):
                    return graph, Consequence(
                        reward=APPLY_REWARD_REPEAT,
                        valid=True,
                        concept_signals={"CONFIRM": 0.3},
                        explanation={"why": "target already derived; nothing new to apply"},
                        task_signal=None,
                    )
                return graph, Consequence(
                    penalty=INVALID_PENALTY,
                    valid=False,
                    concept_signals={"BAD": 0.6},
                    explanation={"why": "no satisfied implication available"},
                    task_signal="TASK_FAILURE",
                )
            # We derived a new fact. Was it the *target*?
            if derived_id == target_id:
                return new_graph, Consequence(
                    reward=APPLY_REWARD_FIRST,
                    valid=True,
                    concept_signals={"GOOD": 1.0, "TRUST": 0.6, "CONFIRM": 0.6},
                    explanation={"why": f"target {target_id} derived"},
                    graph_delta=graph.diff(new_graph),
                    task_signal="TASK_SUCCESS",
                )
            # Useful intermediate step in a chain.
            return new_graph, Consequence(
                reward=APPLY_REWARD_REPEAT * 4,  # small but >0 to encourage chain progress
                valid=True,
                concept_signals={"GOOD": 0.4, "CONFIRM": 0.3},
                explanation={"why": f"intermediate fact {derived_id} derived"},
                graph_delta=graph.diff(new_graph),
                task_signal="TASK_PROGRESS",
            )

        if transformation.name == "verify_rule":
            ok = bool(graph.get_relation("rule_ab", "IMPLIES", "fact_b")) or any(
                r.rtype == "IMPLIES" for r in graph.relations("IMPLIES")
            )
            return graph, Consequence(
                reward=VERIFY_REWARD if ok else 0.0,
                penalty=0.0 if ok else VERIFY_PENALTY,
                valid=ok,
                concept_signals={"CONFIRM": 0.5 if ok else 0.0, "BAD": 0.6 if not ok else 0.0},
                explanation={"why": "rule checked", "valid": ok},
                task_signal=None,
            )

        if transformation.name == "random_assert":
            return graph, Consequence(
                penalty=RANDOM_ASSERT_PENALTY,
                valid=False,
                concept_signals={"BAD": 1.0, "DENY": 0.6},
                explanation={"why": "unsupported assertion"},
                task_signal="TASK_FAILURE",
            )

        return graph, Consequence(
            penalty=INVALID_PENALTY,
            valid=False,
            concept_signals={"BAD": 1.0},
            task_signal="TASK_FAILURE",
        )

    def evaluate(self, graph: RealityGraph, mote_state: Dict) -> float:
        return 10.0 if graph.get_entity(self._target_id(graph)) else 0.0

    def concepts(self) -> List[str]:
        return ["GOOD", "BAD", "TRUST", "CONFIRM", "DENY"]


class RuleWorldEasy(RuleWorld):
    """Alias; same semantics as ``RuleWorld`` but explicit naming for paper tables."""
    domain_name = "rules_easy"


class RuleWorldChain(RuleWorld):
    """A→B→C variant. Use with ``make_rule_graph_chain``."""
    domain_name = "rules_chain"


class RuleWorldDistractor(RuleWorld):
    """One satisfied implication plus 4 unsatisfied distractors. Use with
    ``make_rule_graph_distractor``.
    """
    domain_name = "rules_distractor"


__all__ = [
    "RuleWorld",
    "RuleWorldEasy",
    "RuleWorldChain",
    "RuleWorldDistractor",
    "make_rule_graph",
    "make_rule_graph_easy",
    "make_rule_graph_chain",
    "make_rule_graph_distractor",
    "APPLY_REWARD_FIRST",
    "APPLY_REWARD_REPEAT",
    "VERIFY_REWARD",
    "VERIFY_PENALTY",
    "RANDOM_ASSERT_PENALTY",
    "INVALID_PENALTY",
]
