"""LogicWorld — propositional constraint-satisfaction validation domain.

Roadmap Phase 5. The third structurally-distinct target domain for the
cross-domain action-role transfer claim. Specifically chosen over the
roadmap's originally-suggested ChemistryLite because:

1. LogicWorld has objective, defensible rewards (clause satisfaction is
   a binary truth, not a domain-expert judgement call).
2. The action-role mapping is unambiguous:
       APPROACH_GOOD = assert literals that satisfy more clauses
       AVOID_BAD     = avoid assertions that create contradictions
       VERIFY_UNCERTAIN = check_consistency (cheap probe)
3. It is structurally different from the existing three domains:
       Grid/Hazard     = spatial/graph navigation, immediate consequence
       Rule            = single-step modus ponens derivation
       LogicWorld      = multi-clause constraint satisfaction with search
4. Reviewers cannot attack the domain on validity grounds (SAT is a
   century-old well-understood formalism).

Entities:
    VARIABLE        — x1, x2, ... with current_value: bool | None (unassigned)
    LITERAL         — positive or negative occurrence of a variable inside a clause
    CLAUSE          — disjunction of literals; satisfied? property
    ASSIGNMENT      — the current truth assignment summary entity
    TARGET          — marker pointing at the formula id (mirrors RuleWorld/Hazard)

Relations:
    OCCURS_IN       — variable_id  -> clause_id   (variable appears in clause)
    POSITIVE_IN     — variable_id  -> clause_id   (variable appears positively in clause)
    NEGATIVE_IN     — variable_id  -> clause_id   (variable appears negatively in clause)
    SATISFIED_BY    — clause_id    -> ASSIGNMENT  (clause satisfied under current assignment)

Actions (4):
    assert_literal      — set a variable's value to True or False
    retract_literal     — undo the last assertion (for recovery from contradiction)
    check_consistency   — passive probe, tiny reward
    random_assert       — assign a random unassigned variable (MUTATE, usually bad)

Rewards (Phase 2 scale, comparable across domains):

    assert that completes SAT:               +4.0   TASK_SUCCESS
    assert that increases satisfied count:   +0.5   TASK_PROGRESS
    assert that creates contradiction:       -3.0   TASK_FAILURE
    assert that is a no-op (already done):   +0.05  None
    retract after contradiction:             +0.10  None  (recovery)
    retract when not needed:                 -0.5   None
    check_consistency:                       +0.02  None
    random_assert:                           -1.0   None  (lower-cost mistake than direct contradiction)
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

from ..reality import (
    Consequence,
    Entity,
    RealityGraph,
    Relation,
    Transformation,
    WorldInterface,
)


# ─── REWARD CONSTANTS ────────────────────────────────────────────────────────
# Pulled out for sensitivity sweeps and Phase 2 RuleWorld-scale comparability.

SAT_REWARD                   = 4.0   # all clauses satisfied for the first time
PROGRESS_REWARD              = 0.5   # an assert that strictly increased satisfied count
CONTRADICTION_PENALTY        = 3.0
ASSERT_NOOP_REWARD           = 0.05  # asserting same value again
RETRACT_RECOVERY_REWARD      = 0.10  # retracting after a contradiction is helpful
RETRACT_WASTE_PENALTY        = 0.5   # retracting when there was no contradiction
CHECK_CONSISTENCY_REWARD     = 0.02
RANDOM_ASSERT_PENALTY        = 1.0
INVALID_PENALTY              = 1.0


# ─── GRAPH BUILDERS ──────────────────────────────────────────────────────────

def _make_assignment_entity(g: RealityGraph) -> None:
    """Add the ASSIGNMENT bookkeeping entity. We store the current
    variable -> bool map in the entity's properties so a snapshot/diff
    captures the full state without separate edges per variable."""
    g.add_entity(Entity("ASSIGN", "ASSIGNMENT", {
        "values": {},       # var_id -> bool
        "contradictions": 0,
        "last_assert": None,  # (var_id, value) for the most recent assertion
        "solved": False,
    }))


def _add_target(g: RealityGraph, formula_id: str) -> None:
    g.add_entity(Entity("TARGET", "TARGET", {"derive_id": formula_id}))


def _add_clause(g: RealityGraph, clause_id: str, positive: List[str], negative: List[str]) -> None:
    """Add a CLAUSE plus OCCURS_IN / POSITIVE_IN / NEGATIVE_IN edges.

    positive: variable ids that appear positively (as `x`)
    negative: variable ids that appear negatively (as `¬x`)
    """
    g.add_entity(Entity(clause_id, "CLAUSE", {"satisfied": False}))
    for v in positive:
        g.add_relation(Relation(v, "OCCURS_IN",   clause_id))
        g.add_relation(Relation(v, "POSITIVE_IN", clause_id))
    for v in negative:
        g.add_relation(Relation(v, "OCCURS_IN",   clause_id))
        g.add_relation(Relation(v, "NEGATIVE_IN", clause_id))


def _ensure_variables(g: RealityGraph, var_ids: List[str]) -> None:
    for v in var_ids:
        if g.get_entity(v) is None:
            g.add_entity(Entity(v, "VARIABLE", {}))


def make_logic_graph_easy() -> RealityGraph:
    """3 variables, 3 clauses, satisfying assignment exists.

    Formula:
        C1: (x1 ∨ x2)
        C2: (¬x1 ∨ x3)
        C3: (x2 ∨ ¬x3)

    One satisfying assignment: x1=False, x2=True, x3=False. Two more exist.
    A mote that just asserts x2=True solves C1 and C3 in one go; then
    x1=False or x3=True closes C2.
    """
    g = RealityGraph("logic", "logic_easy")
    _ensure_variables(g, ["x1", "x2", "x3"])
    _add_clause(g, "C1", positive=["x1", "x2"], negative=[])
    _add_clause(g, "C2", positive=["x3"],       negative=["x1"])
    _add_clause(g, "C3", positive=["x2"],       negative=["x3"])
    _make_assignment_entity(g)
    _add_target(g, "formula_easy")
    return g


def make_logic_graph_chain() -> RealityGraph:
    """4 variables, 4 clauses; requires a 2-step assertion chain to satisfy.

    Formula:
        C1: (x1)            — forces x1=True
        C2: (¬x1 ∨ x2)      — forces x2=True given x1=True
        C3: (¬x2 ∨ x3)      — forces x3=True given x2=True
        C4: (x3 ∨ x4)       — satisfied when x3=True

    Satisfying assignment: x1=x2=x3=True, x4 free.
    A mote needs at least 3 correct assertions to satisfy everything; tests
    multi-step credit assignment under contradiction-avoidance.
    """
    g = RealityGraph("logic", "logic_chain")
    _ensure_variables(g, ["x1", "x2", "x3", "x4"])
    _add_clause(g, "C1", positive=["x1"],       negative=[])
    _add_clause(g, "C2", positive=["x2"],       negative=["x1"])
    _add_clause(g, "C3", positive=["x3"],       negative=["x2"])
    _add_clause(g, "C4", positive=["x3", "x4"], negative=[])
    _make_assignment_entity(g)
    _add_target(g, "formula_chain")
    return g


def make_logic_graph_unsat() -> RealityGraph:
    """Unsatisfiable formula — used as a control. TASK_SUCCESS is impossible;
    any policy here can only minimise contradictions / TASK_FAILUREs.

    Formula: (x) ∧ (¬x)
    """
    g = RealityGraph("logic", "logic_unsat")
    _ensure_variables(g, ["x1"])
    _add_clause(g, "C1", positive=["x1"], negative=[])
    _add_clause(g, "C2", positive=[],     negative=["x1"])
    _make_assignment_entity(g)
    _add_target(g, "formula_unsat")
    return g


# ─── WORLD ───────────────────────────────────────────────────────────────────

class LogicWorld(WorldInterface):
    """Propositional satisfaction.

    State lives in the ASSIGNMENT entity's properties (current values per
    variable, plus contradiction count and a `last_assert` for retract).
    Clause satisfaction is recomputed on every step from current values
    and the POSITIVE_IN / NEGATIVE_IN edges; this keeps act() pure-ish
    and lets snapshot/diff capture the whole state via the ASSIGNMENT
    entity properties.

    Position parameter (mote_position) is ignored — there's nothing
    spatial here. The mote chooses a variable to assert via the action's
    `target_var` extra; if not present, the world picks the first
    unassigned variable (so the mote can navigate purely via action types).
    """

    domain_name = "logic"

    # ── helpers ──────────────────────────────────────────────────────────────

    def _target_id(self, graph: RealityGraph) -> str:
        tgt = graph.get_entity("TARGET")
        return tgt.get("derive_id", "formula") if tgt else "formula"

    def _values(self, graph: RealityGraph) -> Dict[str, bool]:
        a = graph.get_entity("ASSIGN")
        return dict(a.get("values", {})) if a else {}

    def _variables(self, graph: RealityGraph) -> List[str]:
        return [e.id for e in graph.entities("VARIABLE")]

    def _unassigned(self, graph: RealityGraph) -> List[str]:
        values = self._values(graph)
        return [v for v in self._variables(graph) if v not in values]

    def _clause_satisfied(self, graph: RealityGraph, clause_id: str, values: Dict[str, bool]) -> bool:
        # A clause is satisfied if any positive literal evaluates True
        # OR any negative literal evaluates False.
        for rel in graph.relations("POSITIVE_IN"):
            if rel.target == clause_id and values.get(rel.source) is True:
                return True
        for rel in graph.relations("NEGATIVE_IN"):
            if rel.target == clause_id and values.get(rel.source) is False:
                return True
        return False

    def _all_clauses(self, graph: RealityGraph) -> List[str]:
        return [c.id for c in graph.entities("CLAUSE")]

    def _satisfied_count(self, graph: RealityGraph, values: Optional[Dict[str, bool]] = None) -> int:
        values = values if values is not None else self._values(graph)
        return sum(1 for c in self._all_clauses(graph) if self._clause_satisfied(graph, c, values))

    def _is_contradicted(self, graph: RealityGraph, values: Optional[Dict[str, bool]] = None) -> bool:
        """A *current* contradiction means some clause is now unsatisfiable
        under any extension of the partial assignment — equivalently, the
        clause has all-false literals among already-assigned variables."""
        values = values if values is not None else self._values(graph)
        for c in self._all_clauses(graph):
            # check if every literal in c is already assigned and false
            literals_evaluated = []
            for rel in graph.relations("POSITIVE_IN"):
                if rel.target == c and rel.source in values:
                    literals_evaluated.append(values[rel.source])         # True if lit satisfied
            for rel in graph.relations("NEGATIVE_IN"):
                if rel.target == c and rel.source in values:
                    literals_evaluated.append(not values[rel.source])
            # We also need to know if the clause has any unassigned literal —
            # if it does, the clause can still be saved.
            total_literals = (
                sum(1 for r in graph.relations("POSITIVE_IN") if r.target == c)
                + sum(1 for r in graph.relations("NEGATIVE_IN") if r.target == c)
            )
            if len(literals_evaluated) == total_literals and not any(literals_evaluated):
                return True
        return False

    def _pick_target_variable(self, graph: RealityGraph, mote_state: Dict) -> Optional[str]:
        """Choose which variable an assert/retract acts on.

        Default policy: prefer a variable whose assertion would satisfy the
        most currently-unsatisfied clauses. Ties broken by variable id for
        determinism. This makes the action "assert_literal" *meaningful*
        without expanding the action space combinatorially (we keep the
        action set at 4 to match the other domains' shape).
        """
        unassigned = self._unassigned(graph)
        if not unassigned:
            return None
        values = self._values(graph)
        best_v, best_score = None, -1
        for v in unassigned:
            # Try assigning True; count how many new clauses get satisfied.
            score = 0
            for c in self._all_clauses(graph):
                if self._clause_satisfied(graph, c, values):
                    continue
                hypothetical = dict(values); hypothetical[v] = True
                if self._clause_satisfied(graph, c, hypothetical):
                    score += 1
            if score > best_score or (score == best_score and (best_v is None or v < best_v)):
                best_v, best_score = v, score
        return best_v

    def _pick_assert_value(self, graph: RealityGraph, var_id: str) -> bool:
        """Greedy: pick True if it satisfies more new clauses than False."""
        values = self._values(graph)
        true_gain  = sum(1 for c in self._all_clauses(graph)
                         if not self._clause_satisfied(graph, c, values)
                         and self._clause_satisfied(graph, c, {**values, var_id: True}))
        false_gain = sum(1 for c in self._all_clauses(graph)
                         if not self._clause_satisfied(graph, c, values)
                         and self._clause_satisfied(graph, c, {**values, var_id: False}))
        return true_gain >= false_gain   # tie -> True for determinism

    def _apply_assignment(self, graph: RealityGraph, var_id: str, value: bool) -> RealityGraph:
        g = graph.snapshot()
        a = g.get_entity("ASSIGN")
        new_values = dict(a.get("values", {}))
        new_values[var_id] = value
        g.update_entity("ASSIGN",
                        values=new_values,
                        last_assert=(var_id, value),
                        solved=a.get("solved", False))
        # Recompute clause SATISFIED edges and entity flag.
        existing = {(r.source, r.target) for r in g.relations("SATISFIES")}
        for c in self._all_clauses(g):
            sat = self._clause_satisfied(g, c, new_values)
            g.update_entity(c, satisfied=sat)
            edge = ("ASSIGN", c)
            has = edge in existing
            if sat and not has:
                g.add_relation(Relation("ASSIGN", "SATISFIES", c))
            elif not sat and has:
                g.remove_relation("ASSIGN", "SATISFIES", c)
        if self._satisfied_count(g, new_values) == len(self._all_clauses(g)):
            cur = g.get_entity("ASSIGN")
            g.update_entity("ASSIGN", solved=True, values=cur.get("values"),
                            last_assert=cur.get("last_assert"))
        return g

    def _retract(self, graph: RealityGraph) -> RealityGraph:
        a = graph.get_entity("ASSIGN")
        last = a.get("last_assert") if a else None
        if not last:
            return graph
        var_id, _value = last
        g = graph.snapshot()
        cur = g.get_entity("ASSIGN")
        new_values = dict(cur.get("values", {}))
        new_values.pop(var_id, None)
        g.update_entity("ASSIGN", values=new_values, last_assert=None,
                        solved=cur.get("solved", False))
        # Re-derive SATISFIES.
        existing = {(r.source, r.target) for r in g.relations("SATISFIES")}
        for c in self._all_clauses(g):
            sat = self._clause_satisfied(g, c, new_values)
            g.update_entity(c, satisfied=sat)
            edge = ("ASSIGN", c)
            if sat and edge not in existing:
                g.add_relation(Relation("ASSIGN", "SATISFIES", c))
            elif not sat and edge in existing:
                g.remove_relation("ASSIGN", "SATISFIES", c)
        return g

    # ── universal contract ──────────────────────────────────────────────────

    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        # Logic has no spatial position; the mote sees everything.
        # Keep observation = full graph so analogy_engine matches on the
        # whole structure. Reasonable for a small SAT formula.
        return graph

    def valid_actions(self, graph: RealityGraph, mote_state: Dict) -> List[Transformation]:
        return [
            Transformation("assert_literal",    self.domain_name, "TRANSFORM", base_cost=0.3,
                           role_hint="APPROACH_GOOD"),
            Transformation("retract_literal",   self.domain_name, "MUTATE",    base_cost=0.3,
                           role_hint="REPAIR_MISMATCH"),
            Transformation("check_consistency", self.domain_name, "VERIFY",    base_cost=0.2,
                           role_hint="VERIFY_UNCERTAIN"),
            Transformation("random_assert",     self.domain_name, "MUTATE",    base_cost=0.3),
        ]

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict) -> Tuple[RealityGraph, Consequence]:
        a = graph.get_entity("ASSIGN")
        already_solved = bool(a and a.get("solved"))
        sat_before = self._satisfied_count(graph)
        n_clauses = len(self._all_clauses(graph))

        # ── check_consistency ──────────────────────────────────────────
        if transformation.name == "check_consistency":
            return graph, Consequence(
                reward=CHECK_CONSISTENCY_REWARD,
                valid=True,
                concept_signals={"CONFIRM": 0.4},
                explanation={"why": "consistency checked",
                             "satisfied": sat_before, "total": n_clauses},
                task_signal=None,
            )

        # ── retract_literal ──────────────────────────────────────────────
        if transformation.name == "retract_literal":
            if not a or not a.get("last_assert"):
                return graph, Consequence(
                    penalty=RETRACT_WASTE_PENALTY,
                    valid=False,
                    concept_signals={"BAD": 0.4},
                    explanation={"why": "nothing to retract"},
                    task_signal=None,
                )
            new_graph = self._retract(graph)
            sat_after = self._satisfied_count(new_graph)
            had_contradiction = self._is_contradicted(graph)
            if had_contradiction and not self._is_contradicted(new_graph):
                return new_graph, Consequence(
                    reward=RETRACT_RECOVERY_REWARD,
                    valid=True,
                    concept_signals={"SAFE": 0.5, "CONFIRM": 0.2},
                    explanation={"why": "retracted contradictory assertion"},
                    graph_delta=graph.diff(new_graph),
                    task_signal=None,
                )
            # Retracting when not contradicted is wasted progress.
            return new_graph, Consequence(
                penalty=RETRACT_WASTE_PENALTY,
                valid=True,
                concept_signals={"BAD": 0.3},
                explanation={"why": "retracted without benefit",
                             "satisfied_before": sat_before, "after": sat_after},
                graph_delta=graph.diff(new_graph),
                task_signal=None,
            )

        # ── random_assert ────────────────────────────────────────────────
        if transformation.name == "random_assert":
            unassigned = self._unassigned(graph)
            if not unassigned:
                return graph, Consequence(
                    penalty=INVALID_PENALTY,
                    valid=False,
                    concept_signals={"VOID": 0.5},
                    explanation={"why": "no unassigned variables left"},
                    task_signal=None,
                )
            var = random.choice(unassigned)
            value = random.random() < 0.5
            new_graph = self._apply_assignment(graph, var, value)
            return new_graph, Consequence(
                penalty=RANDOM_ASSERT_PENALTY,
                valid=False,
                concept_signals={"BAD": 0.6, "DOUBT": 0.5},
                explanation={"why": f"random assert {var}={value}"},
                graph_delta=graph.diff(new_graph),
                task_signal="TASK_FAILURE",
            )

        # ── assert_literal (the workhorse) ───────────────────────────────
        if transformation.name == "assert_literal":
            if already_solved:
                return graph, Consequence(
                    reward=ASSERT_NOOP_REWARD,
                    valid=True,
                    concept_signals={"CONFIRM": 0.2},
                    explanation={"why": "formula already satisfied"},
                    task_signal=None,
                )
            var = self._pick_target_variable(graph, mote_state)
            if var is None:
                # All variables assigned but formula not solved => stuck.
                return graph, Consequence(
                    penalty=INVALID_PENALTY,
                    valid=False,
                    concept_signals={"VOID": 0.5, "DOUBT": 0.4},
                    explanation={"why": "no unassigned variable; assignment cannot satisfy formula"},
                    task_signal="TASK_FAILURE",
                )
            value = self._pick_assert_value(graph, var)
            new_graph = self._apply_assignment(graph, var, value)
            sat_after = self._satisfied_count(new_graph)
            contradicted = self._is_contradicted(new_graph)
            now_solved = bool(new_graph.get_entity("ASSIGN").get("solved"))

            if contradicted:
                return new_graph, Consequence(
                    penalty=CONTRADICTION_PENALTY,
                    valid=False,
                    concept_signals={"DANGER": 1.0, "BAD": 0.8, "DOUBT": 0.6},
                    explanation={"why": f"asserting {var}={value} created contradiction"},
                    graph_delta=graph.diff(new_graph),
                    task_signal="TASK_FAILURE",
                )
            if now_solved and not already_solved:
                return new_graph, Consequence(
                    reward=SAT_REWARD,
                    valid=True,
                    concept_signals={"GOOD": 1.0, "CONFIRM": 0.8, "TRUST": 0.6},
                    explanation={"why": f"asserting {var}={value} satisfied formula",
                                 "satisfied": sat_after, "total": n_clauses},
                    graph_delta=graph.diff(new_graph),
                    task_signal="TASK_SUCCESS",
                )
            if sat_after > sat_before:
                return new_graph, Consequence(
                    reward=PROGRESS_REWARD,
                    valid=True,
                    concept_signals={"GOOD": 0.4, "CONFIRM": 0.3},
                    explanation={"why": f"asserting {var}={value} satisfied more clauses",
                                 "before": sat_before, "after": sat_after},
                    graph_delta=graph.diff(new_graph),
                    task_signal="TASK_PROGRESS",
                )
            # No-op (assertion didn't change satisfied count and no contradiction).
            return new_graph, Consequence(
                reward=ASSERT_NOOP_REWARD,
                valid=True,
                concept_signals={"CONFIRM": 0.2},
                explanation={"why": f"asserting {var}={value} did not change progress",
                             "satisfied": sat_after},
                graph_delta=graph.diff(new_graph),
                task_signal=None,
            )

        return graph, Consequence(
            penalty=INVALID_PENALTY,
            valid=False,
            concept_signals={"BAD": 1.0},
            task_signal="TASK_FAILURE",
        )

    def evaluate(self, graph: RealityGraph, mote_state: Dict) -> float:
        """Higher = better. 10 if formula satisfied; otherwise the fraction
        of satisfied clauses scaled to [-1, 5] (−1 if contradicted)."""
        a = graph.get_entity("ASSIGN")
        if a and a.get("solved"):
            return 10.0
        if self._is_contradicted(graph):
            return -1.0
        total = max(1, len(self._all_clauses(graph)))
        return 5.0 * self._satisfied_count(graph) / total

    def concepts(self) -> List[str]:
        return ["GOOD", "BAD", "DANGER", "SAFE", "CONFIRM", "DOUBT", "TRUST", "VOID"]


class LogicWorldChain(LogicWorld):
    """Multi-clause chain variant; use with ``make_logic_graph_chain``."""
    domain_name = "logic_chain"


class LogicWorldUnsat(LogicWorld):
    """Unsatisfiable control; use with ``make_logic_graph_unsat``.
    TASK_SUCCESS is impossible by construction; only TASK_FAILURE / progress."""
    domain_name = "logic_unsat"


class LogicWorldLarge(LogicWorld):
    """Large propositional satisfaction variant; use with ``make_logic_graph_large``."""
    domain_name = "logic_large"


def make_logic_graph_large(seed: int = 0, n_vars: int = 6, n_clauses: int = 12) -> RealityGraph:
    """Generates a larger satisfiable SAT formula. Deterministic from seed.

    Construction:
      1. Generate a hidden satisfying assignment via seeded RNG.
      2. For each clause, pick 2-3 random variables and assign literal signs
         such that the clause is guaranteed satisfied by the hidden assignment.
      3. This guarantees satisfiability by construction.

    Compatible with existing LogicWorld.act() — same entity types, same action set.
    """
    rng = random.Random(seed)

    var_ids = [f"x{i}" for i in range(1, n_vars + 1)]
    hidden = {v: rng.choice([True, False]) for v in var_ids}

    g = RealityGraph("logic", "logic_large")
    _ensure_variables(g, var_ids)
    _make_assignment_entity(g)

    for ci in range(1, n_clauses + 1):
        cid = f"C{ci}"
        n_lits = rng.randint(2, 3)
        lit_vars = rng.sample(var_ids, min(n_lits, len(var_ids)))
        pos, neg = [], []
        for v in lit_vars:
            if hidden[v]:
                pos.append(v)
            else:
                neg.append(v)
        if not pos and not neg:
            pos.append(rng.choice(lit_vars))
        _add_clause(g, cid, positive=pos, negative=neg)

    _add_target(g, "formula_large")
    return g


__all__ = [
    "LogicWorld", "LogicWorldChain", "LogicWorldUnsat", "LogicWorldLarge",
    "make_logic_graph_easy", "make_logic_graph_chain", "make_logic_graph_unsat",
    "make_logic_graph_large",
    "SAT_REWARD", "PROGRESS_REWARD", "CONTRADICTION_PENALTY",
    "ASSERT_NOOP_REWARD", "RETRACT_RECOVERY_REWARD", "RETRACT_WASTE_PENALTY",
    "CHECK_CONSISTENCY_REWARD", "RANDOM_ASSERT_PENALTY", "INVALID_PENALTY",
]
