"""Engine core for TAIS Swarm V6."""
from .config import SwarmConfig, WorldConfig, ThermoConfig, CommunicationConfig, MemoryConfig, CONFIG_PRESETS
from .spatial import QuadtreeNode, SpatialHash, UnifiedSpatialIndex, AABB
from .thermodynamics import ThermodynamicEngine, ThermodynamicState
from .ecosystem import EcosystemEngine, ResourceCell, WorldModification, Season
from .events import EventBus, Event, EventType
from .persistence import PersistenceLayer, TickRecord, EventRecord, MoteSnapshot
from .world import WorldV6, Landmark
from .core import SwarmV6

__all__ = [
    "SwarmConfig", "WorldConfig", "ThermoConfig", "CommunicationConfig", "MemoryConfig",
    "CONFIG_PRESETS",
    "QuadtreeNode", "SpatialHash", "UnifiedSpatialIndex", "AABB",
    "ThermodynamicEngine", "ThermodynamicState",
    "EcosystemEngine", "ResourceCell", "WorldModification", "Season",
    "EventBus", "Event", "EventType",
    "PersistenceLayer", "TickRecord", "EventRecord", "MoteSnapshot",
    "WorldV6", "Landmark",
    "SwarmV6",
]
