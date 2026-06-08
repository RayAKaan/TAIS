"""TAIS Core: universal reality, memory, and speech substrate."""

from .reality import (
    Entity,
    Relation,
    GraphPattern,
    Transformation,
    Constraint,
    Consequence,
    GraphDelta,
    AnalogyMapping,
    RealityGraph,
    WorldInterface,
)
from .memory import MoteMemory, CulturalMemory, Episode, PatternMemory, PredictionEngine
from .speech import SpeechOrgan, Lexicon, Utterance, SpeechGenome
from .mote import UniversalMote, MetaGenes
from .metacognition import MetacognitiveEngine, SelfModel, PredictionTracker
from .causal import CausalReasoningEngine, CausalLink, Counterfactual
from .planning import HierarchicalPlanner, Plan, PlanStep
from .domains import GridGraphWorld, SequenceWorld, RuleWorld, load_domain

__all__ = [
    "Entity",
    "Relation",
    "GraphPattern",
    "Transformation",
    "Constraint",
    "Consequence",
    "GraphDelta",
    "AnalogyMapping",
    "RealityGraph",
    "WorldInterface",
    "MoteMemory",
    "CulturalMemory",
    "Episode",
    "PatternMemory",
    "PredictionEngine",
    "SpeechOrgan",
    "Lexicon",
    "Utterance",
    "SpeechGenome",
    "UniversalMote",
    "MetaGenes",
    "MetacognitiveEngine",
    "SelfModel",
    "PredictionTracker",
    "CausalReasoningEngine",
    "CausalLink",
    "Counterfactual",
    "HierarchicalPlanner",
    "Plan",
    "PlanStep",
    "GridGraphWorld",
    "SequenceWorld",
    "RuleWorld",
    "load_domain",
]
