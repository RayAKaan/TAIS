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
from .experiments import Condition, Metric, ExperimentSuite

# --- Structural Transfer v2: genuine structural analogy without role labels ---
from .role_discovery import RoleDiscoveryEngine, DiscoveredRole
from .structural_similarity import StructuralCompatibility, wl_relabeled_graph, wl_similarity
from .analogy_engine import StructuralAnalogyEngine, StructuralAnalogy
from .policy_transfer import (
    CompositionalPolicy, PolicySequence, PolicyStep,
    TransferredPolicy, HierarchicalPlannerV2,
)
from .domains.procedural import ProceduralDomainFactory, ProceduralWorld

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
    "Condition",
    "Metric",
    "ExperimentSuite",
    # Structural Transfer v2
    "RoleDiscoveryEngine",
    "DiscoveredRole",
    "StructuralCompatibility",
    "wl_relabeled_graph",
    "wl_similarity",
    "StructuralAnalogyEngine",
    "StructuralAnalogy",
    "CompositionalPolicy",
    "PolicySequence",
    "PolicyStep",
    "TransferredPolicy",
    "HierarchicalPlannerV2",
    "ProceduralDomainFactory",
    "ProceduralWorld",
]
