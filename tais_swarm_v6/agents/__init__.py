"""
TAIS Swarm V6 Agents.

Enhanced motes with:
- Temporal memory (Bayesian decay, expected durations)
- Vector trust (per-concept reputation + gossip)
- Tool use (build shelter, mark trail, create cache)
- Grammar innovation and creole formation
- Metacognition (prediction tracking, self-model, strategy selection)
- Causal reasoning (Delta-P, counterfactuals, action-outcome attribution)
- Hierarchical planning (backward chaining, plan library, rollback)
"""

from .memory_v6 import TemporalMemory, EpisodicEvent, MemoryItemV6
from .trust_v6 import TrustVector, ReputationNetwork, GossipProtocol
from .speech_v6 import (
    SpeechGenomeV6, GrammarInnovator, ChannelType,
    UtteranceV6, UtteranceV6Booklet,
)
from .metacognition import MetacognitiveEngine, PredictionTracker, SelfModel
from .causal import CausalReasoningEngine, CausalLink, Counterfactual
from .planning import HierarchicalPlanner, Plan, PlanStep
from .mote_v6 import MoteV6

__all__ = [
    "TemporalMemory", "EpisodicEvent", "MemoryItemV6",
    "TrustVector", "ReputationNetwork", "GossipProtocol",
    "SpeechGenomeV6", "GrammarInnovator", "ChannelType",
    "UtteranceV6", "UtteranceV6Booklet",
    "MetacognitiveEngine", "PredictionTracker", "SelfModel",
    "CausalReasoningEngine", "CausalLink", "Counterfactual",
    "HierarchicalPlanner", "Plan", "PlanStep",
    "MoteV6",
]
