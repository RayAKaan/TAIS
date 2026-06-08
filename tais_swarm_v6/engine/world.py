"""
WorldV6 for TAIS Swarm V6.
"""

from __future__ import annotations

import math
import random
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass

from .config import WorldConfig
from .spatial import UnifiedSpatialIndex
from .ecosystem import EcosystemEngine, WorldModification


@dataclass
class Landmark:
    id: int
    kind: str
    x: float
    y: float
    token: str

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "x": round(self.x, 2), "y": round(self.y, 2), "token": self.token}

    @classmethod
    def from_dict(cls, d: dict) -> "Landmark":
        return cls(d["id"], d["kind"], d["x"], d["y"], d["token"])


class WorldV6:
    def __init__(self, config: WorldConfig):
        self.cfg = config
        self.size = config.size
        self.ecosystem = EcosystemEngine(config)
        self.spatial = UnifiedSpatialIndex(config.size, hash_cell_size=4.0)
        self.landmarks: List[Landmark] = []
        self._next_landmark_id = 1
        self._init_landmarks()
        for lm in self.landmarks:
            self.spatial.insert_resource(lm.x, lm.y, lm)

    def _init_landmarks(self):
        kinds = ["stone", "cave", "tree", "tower", "river", "bone", "ruin", "spire"]
        for i in range(self.cfg.landmark_count):
            kind = random.choice(kinds)
            x = random.uniform(self.size * 0.1, self.size * 0.9)
            y = random.uniform(self.size * 0.1, self.size * 0.9)
            self.landmarks.append(Landmark(
                id=self._next_landmark_id, kind=kind, x=x, y=y, token=f"lm{self._next_landmark_id}"
            ))
            self._next_landmark_id += 1

    def step(self):
        self.ecosystem.step()

    def sense(self, x: float, y: float, radius: float = 2.0) -> dict:
        resource_sense = self.ecosystem.sense(x, y, radius)
        nearest_lm = None
        nearest_dist = float('inf')
        for lm in self.landmarks:
            d = math.sqrt((lm.x - x) ** 2 + (lm.y - y) ** 2)
            if d < nearest_dist:
                nearest_dist = d
                nearest_lm = lm
        mods = self.ecosystem.get_modifications_near(x, y, radius, self.ecosystem.tick)
        return {
            **resource_sense,
            "nearest_landmark": nearest_lm,
            "nearest_landmark_dist": nearest_dist,
            "modifications": mods,
        }

    def nearest_landmark(self, x: float, y: float) -> Tuple[Optional[Landmark], float]:
        best = None
        best_dist = float('inf')
        for lm in self.landmarks:
            d = math.sqrt((lm.x - x) ** 2 + (lm.y - y) ** 2)
            if d < best_dist:
                best = lm
                best_dist = d
        return best, best_dist

    def deplete_resource(self, x: float, y: float, resource_type: str, amount: float):
        self.ecosystem.deplete(x, y, resource_type, amount)

    def add_modification(self, mod: WorldModification):
        self.ecosystem.add_modification(mod)

    def get_modifications_near(self, x: float, y: float, radius: float = 3.0) -> List[WorldModification]:
        return self.ecosystem.get_modifications_near(x, y, radius, self.ecosystem.tick)

    def is_in_shelter(self, x: float, y: float) -> bool:
        mods = self.get_modifications_near(x, y, 2.0)
        for mod in mods:
            if mod.type == "shelter" and mod.is_active(self.ecosystem.tick):
                d = math.sqrt((mod.x - x) ** 2 + (mod.y - y) ** 2)
                if d < 1.5:
                    return True
        return False

    def to_dict(self) -> dict:
        return {
            "size": self.size,
            "landmarks": [lm.to_dict() for lm in self.landmarks],
            "ecosystem": self.ecosystem.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict, config: WorldConfig) -> "WorldV6":
        world = cls(config)
        world.landmarks = [Landmark.from_dict(lm) for lm in data.get("landmarks", [])]
        world.ecosystem = EcosystemEngine.from_dict(data.get("ecosystem", {}), config)
        return world
