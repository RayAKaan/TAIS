"""
Typed configuration system for TAIS Swarm V6.

Replaces the flat CFG dict from V5.5 with structured, validated,
experiment-trackable configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
import json
import random


@dataclass(frozen=True)
class WorldConfig:
    """World generation and physics parameters."""
    size: float = 64.0
    resource_count: int = 250
    landmark_count: int = 48
    predator_count: int = 10
    max_population: int = 500

    # Resource dynamics (NEW in V6)
    resource_regen_rate: float = 0.15
    resource_depletion: bool = True
    carrying_capacity: float = 1.0

    # Seasonal cycles (NEW in V6)
    season_length: int = 2000
    season_drift: float = 0.3

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WorldConfig":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass(frozen=True)
class ThermoConfig:
    """Real thermodynamic parameters — NO ENERGY RESETS."""
    initial_energy: float = 80.0
    initial_hydration: float = 80.0

    # Metabolic rates (energy per tick)
    base_metabolism: float = 0.85
    hydration_decay: float = 0.65
    toxicity_decay: float = 0.92

    # Thermodynamic efficiency (NEW in V6)
    entropy_rate: float = 0.02
    heat_dissipation: float = 0.15

    # Action costs (energy)
    move_cost: float = 0.35
    speak_cost: float = 4.2
    direct_cost: float = 2.0
    build_cost: float = 25.0
    mark_cost: float = 1.5

    # Death thresholds (hard limits)
    death_energy: float = 0.0
    death_hydration: float = -30.0
    max_energy: float = 150.0
    max_hydration: float = 120.0

    # Dehydration damage
    dehydration_damage: float = 0.3

    # Reproduction threshold (higher bar)
    mitosis_energy: float = 110.0
    mitosis_hydration: float = 55.0
    reproduction_cost: float = 0.45

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CommunicationConfig:
    """Speech, trust, and social parameters."""
    whisper_range: float = 2.0
    speak_range: float = 4.5
    shout_range: float = 8.0
    broadcast_cost_mult: float = 1.0
    shout_cost_mult: float = 2.5

    # Lexicon learning
    lexicon_lr: float = 0.10
    self_ground_lr: float = 0.06
    teaching_boost: float = 0.60

    # Trust dynamics (NEW: vector trust)
    trust_decay: float = 0.94
    trust_gossip_range: float = 6.0
    trust_gossip_prob: float = 0.15

    # Grammar evolution
    grammar_mutate: float = 0.04
    grammar_innovation_prob: float = 0.08

    # Comprehension thresholds
    min_speech_energy: float = 10.0
    curiosity_rate: float = 0.15

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MemoryConfig:
    """Memory system parameters."""
    memory_slots: int = 48
    memory_forget: float = 0.988
    memory_merge_dist: float = 1.8

    # Temporal memory (NEW in V6)
    temporal_horizon: int = 500
    expected_resource_duration: Dict[str, float] = field(default_factory=lambda: {
        "FOOD": 80.0,
        "WATER": 100.0,
        "SHELTER": 300.0,
        "POISON": 50.0,
    })

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SwarmConfig:
    """Master configuration container."""
    world: WorldConfig = field(default_factory=WorldConfig)
    thermo: ThermoConfig = field(default_factory=ThermoConfig)
    comm: CommunicationConfig = field(default_factory=CommunicationConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)

    # Simulation control
    ticks_per_second: float = 8.0
    seed: Optional[int] = None

    # Persistence
    db_path: str = "./tais_v6_data.db"
    snapshot_interval: int = 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "world": self.world.to_dict(),
            "thermo": self.thermo.to_dict(),
            "comm": self.comm.to_dict(),
            "memory": self.memory.to_dict(),
            "ticks_per_second": self.ticks_per_second,
            "seed": self.seed,
            "db_path": self.db_path,
            "snapshot_interval": self.snapshot_interval,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SwarmConfig":
        return cls(
            world=WorldConfig.from_dict(d.get("world", {})),
            thermo=ThermoConfig(**d.get("thermo", {})),
            comm=CommunicationConfig(**d.get("comm", {})),
            memory=MemoryConfig(**d.get("memory", {})),
            ticks_per_second=d.get("ticks_per_second", 8.0),
            seed=d.get("seed"),
            db_path=d.get("db_path", "./tais_v6_data.db"),
            snapshot_interval=d.get("snapshot_interval", 100),
        )

    @classmethod
    def from_json(cls, s: str) -> "SwarmConfig":
        return cls.from_dict(json.loads(s))

    @classmethod
    def from_file(cls, path: str) -> "SwarmConfig":
        with open(path) as f:
            return cls.from_json(f.read())


CONFIG_PRESETS = {
    "standard": SwarmConfig(),
    "harsh": SwarmConfig(
        world=WorldConfig(resource_count=150, predator_count=16),
        thermo=ThermoConfig(
            initial_energy=60.0,
            base_metabolism=1.1,
            entropy_rate=0.04,
            death_hydration=-20.0,
            speak_cost=5.5,
        ),
        comm=CommunicationConfig(
            trust_decay=0.90,
        ),
    ),
    "abundant": SwarmConfig(
        world=WorldConfig(resource_count=400, predator_count=4),
        thermo=ThermoConfig(
            initial_energy=100.0,
            base_metabolism=0.6,
            entropy_rate=0.01,
        ),
    ),
    "communication_focus": SwarmConfig(
        thermo=ThermoConfig(speak_cost=2.5),
        comm=CommunicationConfig(
            teaching_boost=0.80,
            grammar_innovation_prob=0.15,
            trust_gossip_prob=0.25,
        ),
        memory=MemoryConfig(memory_slots=64),
    ),
}
