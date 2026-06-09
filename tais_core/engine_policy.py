"""Engine selection policy: decide which cognitive engines to activate based on action vocabulary.

Phase A: replaces hard-coded all-or-nothing engine conditions with a
generic policy that reads the action set's universal_op vocabulary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set

from .reality import Transformation


# Ops that require symbolic reasoning
SYMBOLIC_OPS: Set[str] = {
    "VERIFY", "TEST", "TRANSFORM", "COMPOSE", "DECOMPOSE", "PREDICT",
}

# Ops that are purely sensorimotor
SENSORIMOTOR_OPS: Set[str] = {
    "MOVE_TOWARD", "MOVE_AWAY",
}


@dataclass
class EnginePolicyDecision:
    """Which engines should be active for the current action set."""

    use_metacognition: bool = False
    use_causal_reasoning: bool = False
    use_planning: bool = False
    reason: str = "unknown"


def decide_engine_usage(actions: List[Transformation]) -> EnginePolicyDecision:
    """Decide which cognitive engines to activate based on action vocabulary.

    Rules:
        - If only sensorimotor ops (MOVE_TOWARD, MOVE_AWAY): no engines needed.
        - If any symbolic ops (VERIFY, TRANSFORM, etc.): full engines.
        - Otherwise (mixed or unknown ops): metacognition only.
    """
    ops = {a.universal_op for a in actions if a.universal_op}
    symbolic = bool(ops & SYMBOLIC_OPS)
    sensorimotor = bool(ops) and ops.issubset(SENSORIMOTOR_OPS)

    if sensorimotor and not symbolic:
        return EnginePolicyDecision(reason="sensorimotor-only")
    if symbolic:
        return EnginePolicyDecision(
            use_metacognition=True,
            use_causal_reasoning=True,
            use_planning=True,
            reason="symbolic",
        )
    return EnginePolicyDecision(
        use_metacognition=True,
        reason="mixed_or_unknown",
    )
