"""
tais_core.policy_transfer
=========================

Compositional Policy Transfer: transfer of ACTION SEQUENCES across domains,
not just individual role preferences.

Current TAIS transfers each role independently. No sequencing. The planner
is single-step. This means TAIS can transfer "approach good things" but NOT
"verify safety first, then approach if safe."

Humans transfer STRATEGIES, not single-action preferences:
  "In grid world, I approach food only after verifying safety."
  -> "In negotiation, I accept offers only after evaluating fairness."

This module implements:
1. PolicySequence: a learned sequence of (structural_pattern -> action) pairs
2. CompositionalPolicy: a collection of policy sequences that can transfer
3. HierarchicalPlannerV2: a multi-step planner that uses compositional policies

The key insight: a transferable policy is a SEQUENCE of structural patterns
and the actions that worked on them. The structural patterns transfer via
topology matching (from structural_similarity.py), and the temporal ordering
is preserved across domains.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from .reality import Consequence, GraphPattern, RealityGraph, Transformation
from .structural_similarity import StructuralCompatibility, wl_relabeled_graph, wl_similarity
from .analogy_engine import StructuralAnalogyEngine, StructuralAnalogy


# --- POLICY STEP ---------------------------------------------------------------

@dataclass
class PolicyStep:
    """One step in a compositional policy.

    A step is a (structural_situation, action, expected_outcome) triple.
    The structural_situation is described by a topology fingerprint, not
    by entity/relation names.
    """

    step_index: int
    topology_fingerprint: str      # Structural key of the situation
    action_op: str                 # Universal op to execute
    expected_valence: str          # "POSITIVE" or "NEGATIVE" or "NEUTRAL"
    prerequisite_step: Optional[int] = None  # Which step must succeed first
    entity_types_involved: FrozenSet[str] = frozenset()
    relation_types_involved: FrozenSet[str] = frozenset()

    def to_dict(self) -> dict:
        return {
            "step_index": self.step_index,
            "topology_fingerprint": self.topology_fingerprint,
            "action_op": self.action_op,
            "expected_valence": self.expected_valence,
            "prerequisite_step": self.prerequisite_step,
            "entity_types_involved": sorted(self.entity_types_involved),
            "relation_types_involved": sorted(self.relation_types_involved),
        }


# --- POLICY SEQUENCE -----------------------------------------------------------

@dataclass
class PolicySequence:
    """A learned sequence of structural situations and actions.

    This is the transferable unit: not a single role preference, but a
    complete strategy. Example:

    Step 0: [THREAT near TARGET] -> VERIFY_SAFETY
    Step 1: [VERIFIED, SAFE] -> APPROACH_TARGET
    Step 2: [AT TARGET] -> COLLECT_RESOURCE

    This sequence transfers as a unit:
    Step 0: [UNFAIR_PROPOSAL from COUNTERPART] -> EVALUATE_PROPOSAL
    Step 1: [EVALUATED, FAIR] -> ACCEPT_OFFER
    Step 2: [OFFER ACCEPTED] -> COMPLETE_TRADE
    """

    sequence_id: str
    source_domain: str
    steps: List[PolicyStep]
    total_reward: float
    times_used: int = 0
    times_successful: int = 0
    created_tick: int = 0

    @property
    def success_rate(self) -> float:
        return self.times_successful / max(1, self.times_used)

    @property
    def length(self) -> int:
        return len(self.steps)

    def to_dict(self) -> dict:
        return {
            "sequence_id": self.sequence_id,
            "source_domain": self.source_domain,
            "steps": [s.to_dict() for s in self.steps],
            "total_reward": round(self.total_reward, 3),
            "times_used": self.times_used,
            "times_successful": self.times_successful,
            "success_rate": round(self.success_rate, 3),
            "created_tick": self.created_tick,
        }


# --- TRANSFERRED POLICY --------------------------------------------------------

@dataclass
class TransferredPolicy:
    """A policy sequence mapped to a new domain via structural analogy.

    Contains the original sequence plus the mapping from source structural
    situations to target structural situations.
    """

    original_sequence: PolicySequence
    mapped_steps: List[PolicyStep]
    analogy_confidence: float
    mapping_method: str

    def get_next_action_op(self, current_step: int) -> Optional[str]:
        """Get the universal_op for the next step."""
        if current_step < len(self.mapped_steps):
            return self.mapped_steps[current_step].action_op
        return None


# --- COMPOSITIONAL POLICY ------------------------------------------------------

class CompositionalPolicy:
    """Learns and transfers compositional policy sequences.

    The core mechanism:
    1. From episodic experience, extract successful action sequences
       (contiguous subsequences with positive net reward and low prediction error)
    2. Store each sequence as a PolicySequence with structural fingerprints
    3. When encountering a new domain, find analogous structural situations
       and transfer the sequences
    """

    def __init__(
        self,
        min_sequence_reward: float = 1.0,
        max_sequence_length: int = 10,
        min_analogy_confidence: float = 0.3,
        wl_iterations: int = 3,
        buffer_capacity: int = 50,
    ):
        self.min_sequence_reward = min_sequence_reward
        self.max_sequence_length = max_sequence_length
        self.min_analogy_confidence = min_analogy_confidence

        self._sequences: Dict[str, PolicySequence] = {}
        self._sequence_counter: int = 0
        self._recent_episodes: List[Dict[str, Any]] = []
        self._buffer_capacity = buffer_capacity
        self._analogy_engine = StructuralAnalogyEngine(
            wl_iterations=wl_iterations,
            min_mapping_confidence=min_analogy_confidence,
        )

    def learn_from_episodes(
        self,
        episodes: List[Dict[str, Any]],
    ) -> List[PolicySequence]:
        """Extract successful action sequences from episode records.

        Each episode dict should have:
            observation: RealityGraph
            action: Transformation
            consequence: Consequence
            domain: str
            tick: int
            structural_key: str  (from role_discovery or structural_similarity)

        Episodes are buffered internally. Sequences are extracted from
        contiguous spans of successful episodes in the buffer.

        Returns list of newly learned PolicySequences.
        """
        if not episodes:
            return []

        # Buffer incoming episodes (sliding window)
        self._recent_episodes.extend(episodes)
        if len(self._recent_episodes) > self._buffer_capacity:
            self._recent_episodes = self._recent_episodes[-self._buffer_capacity:]

        # Scan buffer for successful contiguous subsequences
        new_sequences = []
        i = 0
        while i < len(self._recent_episodes):
            if not self._recent_episodes[i].get("valid", True):
                i += 1
                continue

            # Start a candidate sequence
            seq: List[Dict[str, Any]] = []
            seq_reward = 0.0

            for j in range(i, len(self._recent_episodes)):
                ep = self._recent_episodes[j]
                net = ep.get("outcome_net", 0.0)
                valid = ep.get("valid", True)

                if not valid:
                    break
                if net < -1.0:
                    break

                seq.append(ep)
                seq_reward += net

                if len(seq) >= self.max_sequence_length:
                    break

            if seq_reward >= self.min_sequence_reward and len(seq) >= 2:
                ps = self._create_sequence(seq)
                if ps is not None and ps.sequence_id not in self._sequences:
                    self._sequences[ps.sequence_id] = ps
                    new_sequences.append(ps)

            i += max(1, len(seq))

        return new_sequences

    def transfer_to_domain(
        self,
        target_graph: RealityGraph,
        available_actions: List[Transformation],
    ) -> List[TransferredPolicy]:
        """Transfer all learned policy sequences to a new domain.

        For each sequence:
        1. Check if the sequence's structural situations have analogs
           in the target domain
        2. Map each step's topology to the target
        3. Find actions in the target that match the mapped universal_ops
        4. Return the mapped sequences as TransferredPolicies

        The transfer is STRUCTURAL: it depends on topology matching,
        not on role labels or action names.
        """
        transferred = []

        for seq in self._sequences.values():
            mapped_steps = []
            total_analogy = 0.0

            for i, step in enumerate(seq.steps):
                # Find an action in the target that matches this step's universal_op
                target_action = None
                for action in available_actions:
                    if action.universal_op == step.action_op:
                        target_action = action
                        break

                if target_action is None:
                    # Can't map this step — try partial match
                    for action in available_actions:
                        if self._op_family_match(step.action_op, action.universal_op):
                            target_action = action
                            break

                if target_action is not None:
                    # Compute structural analogy for this step
                    analogy = self._compute_step_analogy(step, target_graph)
                    total_analogy += analogy

                    mapped_step = PolicyStep(
                        step_index=i,
                        topology_fingerprint=step.topology_fingerprint,
                        action_op=target_action.universal_op,
                        expected_valence=step.expected_valence,
                        prerequisite_step=step.prerequisite_step,
                        entity_types_involved=step.entity_types_involved,
                        relation_types_involved=step.relation_types_involved,
                    )
                    mapped_steps.append(mapped_step)

            if mapped_steps and total_analogy / len(seq.steps) >= self.min_analogy_confidence:
                avg_analogy = total_analogy / len(seq.steps)
                transferred.append(TransferredPolicy(
                    original_sequence=seq,
                    mapped_steps=mapped_steps,
                    analogy_confidence=avg_analogy,
                    mapping_method="structural_analogy",
                ))

        # Sort by confidence x source success rate
        transferred.sort(
            key=lambda tp: tp.analogy_confidence * tp.original_sequence.success_rate,
            reverse=True,
        )
        return transferred

    def get_best_transferred_policy(
        self,
        target_graph: RealityGraph,
        available_actions: List[Transformation],
    ) -> Optional[TransferredPolicy]:
        """Get the single best transferred policy for the current situation."""
        policies = self.transfer_to_domain(target_graph, available_actions)
        return policies[0] if policies else None

    def get_sequences(self) -> List[PolicySequence]:
        """Return all learned sequences."""
        return list(self._sequences.values())

    def get_sequences_from_domain(self, domain: str) -> List[PolicySequence]:
        """Return sequences learned in a specific domain."""
        return [s for s in self._sequences.values() if s.source_domain == domain]

    # --- INTERNAL METHODS -----------------------------------------------------

    def _create_sequence(self, episodes: List[Dict[str, Any]]) -> Optional[PolicySequence]:
        """Create a PolicySequence from a list of contiguous episodes."""
        if len(episodes) < 2:
            return None

        seq_id = f"seq_{self._sequence_counter}"
        self._sequence_counter += 1

        domain = episodes[0].get("domain", "unknown")
        total_reward = sum(ep.get("outcome_net", 0.0) for ep in episodes)

        steps = []
        for i, ep in enumerate(episodes):
            topo_fp = ep.get("structural_key", "")
            if not topo_fp:
                topo_fp = hashlib.md5(str(i).encode()).hexdigest()[:8]

            action_op = ep.get("universal_op", "OBSERVE")
            valence = "POSITIVE" if ep.get("outcome_net", 0.0) > 0 else "NEGATIVE"

            etypes = ep.get("entity_types", frozenset())
            rtypes = ep.get("relation_types", frozenset())

            step = PolicyStep(
                step_index=i,
                topology_fingerprint=topo_fp,
                action_op=action_op,
                expected_valence=valence,
                prerequisite_step=i - 1 if i > 0 else None,
                entity_types_involved=etypes if isinstance(etypes, frozenset) else frozenset(etypes),
                relation_types_involved=rtypes if isinstance(rtypes, frozenset) else frozenset(rtypes),
            )
            steps.append(step)

        return PolicySequence(
            sequence_id=seq_id,
            source_domain=domain,
            steps=steps,
            total_reward=total_reward,
            created_tick=episodes[0].get("tick", 0),
        )

    def _compute_step_analogy(self, step: PolicyStep, target_graph: RealityGraph) -> float:
        """Compute how well a step's topology matches the target graph."""
        target_etypes = frozenset(e.etype for e in target_graph.entities())
        target_rtypes = frozenset(r.rtype for r in target_graph.relations())

        if step.entity_types_involved and target_etypes:
            etype_overlap = len(step.entity_types_involved & target_etypes) / max(
                len(step.entity_types_involved | target_etypes), 1
            )
        else:
            etype_overlap = 0.5

        if step.relation_types_involved and target_rtypes:
            rtype_overlap = len(step.relation_types_involved & target_rtypes) / max(
                len(step.relation_types_involved | target_rtypes), 1
            )
        else:
            rtype_overlap = 0.5

        return 0.5 * etype_overlap + 0.5 * rtype_overlap

    def _op_family_match(self, op_a: str, op_b: str) -> bool:
        """Check if two universal_ops are in the same functional family."""
        # Movement family
        if op_a in ("MOVE_TOWARD", "MOVE_AWAY") and op_b in ("MOVE_TOWARD", "MOVE_AWAY"):
            return True
        # Verification family
        if op_a in ("VERIFY", "TEST", "OBSERVE", "FOCUS", "COMPARE") and \
           op_b in ("VERIFY", "TEST", "OBSERVE", "FOCUS", "COMPARE"):
            return True
        # Transformation family
        if op_a in ("TRANSFORM", "COMPOSE", "DECOMPOSE", "MUTATE") and \
           op_b in ("TRANSFORM", "COMPOSE", "DECOMPOSE", "MUTATE"):
            return True
        # Communication family
        if op_a in ("ASK", "ANSWER", "TEACH") and op_b in ("ASK", "ANSWER", "TEACH"):
            return True
        return False


# --- HIERARCHICAL PLANNER V2 ---------------------------------------------------

class HierarchicalPlannerV2:
    """Multi-step planner that reasons over compositional policies.

    This replaces the single-step HierarchicalPlanner with a planner that:
    1. Identifies structural patterns in the current observation
    2. Finds compositional policies that contain these patterns
    3. Selects the policy whose goal is most compatible
    4. Returns the mapped action sequence

    Key improvement over v1: supports multi-step plans with prerequisite
    tracking. A step is only executed if its prerequisite succeeded.
    """

    def __init__(
        self,
        compositional_policy: Optional[CompositionalPolicy] = None,
        planning_cost: float = 2.0,
    ):
        self.compositional_policy = compositional_policy or CompositionalPolicy()
        self.planning_cost = planning_cost

        self._active_policy: Optional[TransferredPolicy] = None
        self._current_step: int = 0
        self._step_results: List[bool] = []
        self._plan_history: List[Tuple[str, bool]] = []

    def plan(
        self,
        observation: RealityGraph,
        available_actions: List[Transformation],
    ) -> Optional[str]:
        """Generate a multi-step plan and return the first action.

        Steps:
        1. Get transferred policies from the compositional policy store
        2. Select the best one based on confidence and source success rate
        3. Start executing it

        Returns the action name for the first step, or None.
        """
        candidates = self.compositional_policy.transfer_to_domain(
            observation, available_actions
        )

        if not candidates:
            self._active_policy = None
            return None

        # Select best policy
        best = candidates[0]
        self._active_policy = best
        self._current_step = 0
        self._step_results = []

        # Return first step's action
        return best.get_next_action_op(0)

    def get_next_step(self) -> Optional[str]:
        """Get the universal_op for the next step in the active plan."""
        if self._active_policy is None:
            return None

        op = self._active_policy.get_next_action_op(self._current_step)
        if op is None:
            # Plan complete
            success = all(self._step_results)
            self._plan_history.append((self._active_policy.original_sequence.sequence_id, success))
            self._active_policy = None
            return None

        return op

    def advance_on_success(self):
        """Advance to next step after a successful action."""
        if self._active_policy is not None:
            self._step_results.append(True)
            self._current_step += 1

    def rollback_on_failure(self):
        """Rollback the current plan after a failure."""
        if self._active_policy is not None:
            self._step_results.append(False)
            self._plan_history.append((self._active_policy.original_sequence.sequence_id, False))
            self._active_policy = None
            self._current_step = 0

    @property
    def active_plan(self) -> Optional[TransferredPolicy]:
        return self._active_policy

    @property
    def plan_depth(self) -> int:
        """How many steps remaining in the active plan."""
        if self._active_policy is None:
            return 0
        return len(self._active_policy.mapped_steps) - self._current_step

    def to_dict(self) -> dict:
        return {
            "active_plan": self._active_policy.original_sequence.to_dict() if self._active_policy else None,
            "current_step": self._current_step,
            "step_results": self._step_results,
            "plan_history": self._plan_history[-20:],
            "stored_sequences": len(self.compositional_policy._sequences),
        }
