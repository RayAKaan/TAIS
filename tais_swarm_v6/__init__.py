"""
TAIS Swarm V6: Thermodynamic Ecosystem with Emergent Communication
=================================================================

A complete rewrite of the V5.5 swarm engine with:
- Real thermodynamics (energy is a hard constraint, no resets)
- Quadtree + SpatialHash indexing (O(log n) lookups)
- FastAPI + WebSocket server (no LLM routes)
- SQLite time-series persistence (WAL mode)
- Tool use and world modification
- Temporal memory with Bayesian decay
- Vector trust with gossip protocols
- Grammar innovation and creole formation
- Metacognition (prediction tracking, self-model, strategy selection)
- Causal reasoning (Delta-P, counterfactuals)
- Hierarchical planning (backward chaining, plan library)

Version: 6.0.0
"""

__version__ = "6.0.0"

from .engine.core import SwarmV6
from .engine.world import WorldV6
from .engine.thermodynamics import ThermodynamicEngine
from .engine.spatial import SpatialHash, UnifiedSpatialIndex
from .engine.events import EventBus
from .engine.persistence import PersistenceLayer
from .agents.mote_v6 import MoteV6
from .agents.metacognition import MetacognitiveEngine
from .agents.causal import CausalReasoningEngine
from .agents.planning import HierarchicalPlanner
from .api.server import SwarmServer

__all__ = [
    "SwarmV6",
    "MoteV6",
    "WorldV6",
    "ThermodynamicEngine",
    "SpatialHash",
    "UnifiedSpatialIndex",
    "EventBus",
    "PersistenceLayer",
    "MetacognitiveEngine",
    "CausalReasoningEngine",
    "HierarchicalPlanner",
    "SwarmServer",
]
