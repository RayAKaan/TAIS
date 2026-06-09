"""
tais_core.role_learning
======================

Learned role compatibility: prototype that learns how compatible each
(role, universal_op) pair is from consequence statistics, using
bounded-normalized EWM updates.

This is an experimental alternative to the hand-coded
``role_compatibility()`` table in ``memory.py``.  Default TAIS
behaviour is unchanged — this must be explicitly enabled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

RoleOpKey = Tuple[str, str]


@dataclass
class LearnedRoleCompatibility:
    alpha: float = 0.3
    default_value: float = 0.0

    values: Dict[RoleOpKey, float] = field(default_factory=dict)
    counts: Dict[RoleOpKey, int] = field(default_factory=dict)

    def update(self, role: str, op: str, outcome_net: float) -> None:
        target = max(-1.0, min(1.0, outcome_net / 4.0))
        key = (role, op)
        current = self.values.get(key, self.default_value)
        self.values[key] = (1.0 - self.alpha) * current + self.alpha * target
        self.counts[key] = self.counts.get(key, 0) + 1

    def score(self, role: str, op: str) -> float:
        return self.values.get((role, op), self.default_value)

    def role_score(self, role: str) -> float:
        matching = [
            v for (r, _op), v in self.values.items() if r == role
        ]
        if not matching:
            return self.default_value
        return sum(matching) / len(matching)

    def has_observed(self, role: str, op: str) -> bool:
        return (role, op) in self.values

    def table_size(self) -> int:
        return len(self.values)

    def total_observations(self) -> int:
        return sum(self.counts.values())

    def mean_learned_score(self) -> float:
        if not self.values:
            return 0.0
        return sum(self.values.values()) / len(self.values)

    def to_dict(self) -> dict:
        return {
            "alpha": self.alpha,
            "default_value": self.default_value,
            "values": {f"{r}__{o}": v for (r, o), v in self.values.items()},
            "counts": {f"{r}__{o}": c for (r, o), c in self.counts.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LearnedRoleCompatibility":
        obj = cls(alpha=data.get("alpha", 0.3), default_value=data.get("default_value", 0.0))
        raw_values = data.get("values", {})
        raw_counts = data.get("counts", {})
        for key_str, v in raw_values.items():
            parts = key_str.split("__", 1)
            if len(parts) == 2:
                obj.values[(parts[0], parts[1])] = v
        for key_str, c in raw_counts.items():
            parts = key_str.split("__", 1)
            if len(parts) == 2:
                obj.counts[(parts[0], parts[1])] = c
        return obj


def make_learned_role_compatibility_fn(
    learned: LearnedRoleCompatibility,
    mode: str = "learned",
    hardcoded_fn=None,
    seed: int = 0,
):
    """Return a ``role_compatibility(source_role, target_role)`` function.

    Parameters
    ----------
    learned : LearnedRoleCompatibility
        The learned table populated during pretrain / step().
    mode : str
        One of:
        * ``"learned"`` — use ``learned.role_score`` for cross-role pairs.
        * ``"learned_plus_hardcoded"`` — average learned + hardcoded.
        * ``"random"`` — seed-deterministic random table.
        * ``"zero"`` — always return 0.0 for cross-role pairs.
    hardcoded_fn : callable or None
        The original ``role_compatibility`` (required for
        ``learned_plus_hardcoded``).
    seed : int
        Seed for ``"random"`` mode.
    """
    import random as _random
    _rng = _random.Random(seed + 999_006)

    _compat_table: Dict[Tuple[str, str], float] = {}
    _all_roles = [
        "APPROACH_GOOD", "AVOID_BAD", "VERIFY_UNCERTAIN", "TRANSFORM_TOWARD_GOAL",
        "EXPLORE_UNCERTAIN", "REPAIR_MISMATCH", "MAINTAIN_STABLE", "FAILED", "UNCLASSIFIED",
    ]
    for src in _all_roles:
        for tgt in _all_roles:
            _compat_table[(src, tgt)] = _rng.uniform(0.0, 1.0) if src != tgt else 1.0

    def patched(source_role: str, target_role: str) -> float:
        if not source_role or not target_role:
            return 0.0
        if source_role == target_role:
            return 1.0
        if mode == "zero":
            return 0.0
        if mode == "random":
            return _compat_table.get((source_role, target_role), 0.0)
        if mode == "learned":
            return learned.role_score(target_role)
        if mode == "learned_plus_hardcoded":
            if hardcoded_fn is None:
                return learned.role_score(target_role)
            learned_val = learned.role_score(target_role)
            hardcoded_val = hardcoded_fn(source_role, target_role)
            return 0.5 * learned_val + 0.5 * hardcoded_val
        return 0.0

    return patched
