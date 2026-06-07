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
from .domains import GridGraphWorld, SequenceWorld, RuleWorld

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
    "GridGraphWorld",
    "SequenceWorld",
    "RuleWorld",
]
