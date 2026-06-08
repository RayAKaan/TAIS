"""
Cellular automata ecosystem for TAIS Swarm V6.

Replaces V5.5's static Gaussian resource blobs with:
- Cellular automata resource layer (diffusion, depletion, regrowth)
- Seasonal cycles that shift resource distributions
- Carrying capacity and density-dependent growth
- Persistent world modifications (trails, shelters, caches)
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum, auto

from .config import WorldConfig


class Season(Enum):
    SPRING = auto()
    SUMMER = auto()
    AUTUMN = auto()
    WINTER = auto()


@dataclass
class ResourceCell:
    """A single cell in the resource CA grid."""
    food: float = 0.0
    water: float = 0.0
    shelter_quality: float = 0.0
    poison: float = 0.0
    food_capacity: float = 1.0
    water_capacity: float = 1.0

    def total_biomass(self) -> float:
        return self.food + self.water + self.shelter_quality


@dataclass
class WorldModification:
    """Persistent changes made by motes."""
    type: str
    x: float
    y: float
    creator_id: int
    tick_created: int
    strength: float = 1.0
    decay_rate: float = 0.995
    last_used_tick: int = 0

    def current_strength(self, tick: int) -> float:
        age = tick - self.tick_created
        return self.strength * (self.decay_rate ** age)

    def is_active(self, tick: int, threshold: float = 0.1) -> bool:
        return self.current_strength(tick) > threshold


class EcosystemEngine:
    """Cellular automata resource dynamics."""

    def __init__(self, config: WorldConfig):
        self.cfg = config
        self.grid_size = int(config.size)
        self.cells: Dict[Tuple[int, int], ResourceCell] = {}
        self.modifications: List[WorldModification] = []
        self.tick = 0
        self.season = Season.SPRING
        self.season_progress = 0.0

        self.season_params = {
            Season.SPRING:  {"food_growth": 0.12, "water_growth": 0.15, "shelter_growth": 0.05},
            Season.SUMMER:  {"food_growth": 0.18, "water_growth": 0.08, "shelter_growth": 0.10},
            Season.AUTUMN:  {"food_growth": 0.08, "water_growth": 0.10, "shelter_growth": 0.15},
            Season.WINTER:  {"food_growth": 0.02, "water_growth": 0.05, "shelter_growth": 0.20},
        }
        self._initialize_resources()

    def _initialize_resources(self):
        size = self.grid_size
        num_clusters = max(3, int(self.cfg.size / 12))
        clusters = []
        for _ in range(num_clusters):
            cx = random.uniform(size * 0.15, size * 0.85)
            cy = random.uniform(size * 0.15, size * 0.85)
            kind = random.choice(["food", "water", "mixed"])
            radius = random.uniform(3.0, 8.0)
            clusters.append((cx, cy, kind, radius))

        for x in range(size):
            for y in range(size):
                cell = ResourceCell()
                cell.food = random.uniform(0.0, 0.15)
                cell.water = random.uniform(0.0, 0.12)
                cell.shelter_quality = random.uniform(0.0, 0.08)

                for cx, cy, kind, radius in clusters:
                    d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                    if d < radius * 3:
                        influence = math.exp(-(d * d) / (2 * radius * radius))
                        if kind in ("food", "mixed"):
                            cell.food += influence * random.uniform(0.3, 0.8)
                        if kind in ("water", "mixed"):
                            cell.water += influence * random.uniform(0.3, 0.8)
                        cell.shelter_quality += influence * random.uniform(0.1, 0.4)

                if random.random() < 0.02:
                    cell.poison = random.uniform(0.3, 1.0)

                cell.food_capacity = cell.food * 1.5 + 0.2
                cell.water_capacity = cell.water * 1.5 + 0.2
                self.cells[(x, y)] = cell

    def _get_season(self, tick: int) -> Season:
        season_idx = (tick // self.cfg.season_length) % 4
        return list(Season)[season_idx]

    def _seasonal_shift(self, tick: int) -> Tuple[float, float]:
        angle = (tick % (self.cfg.season_length * 4)) / (self.cfg.season_length * 4) * 2 * math.pi
        return (math.cos(angle) * self.cfg.season_drift * 2, math.sin(angle) * self.cfg.season_drift * 2)

    def step(self):
        self.tick += 1
        self.season = self._get_season(self.tick)
        params = self.season_params[self.season]
        dx, dy = self._seasonal_shift(self.tick)

        new_cells = {}
        size = self.grid_size

        for (x, y), cell in self.cells.items():
            new_cell = ResourceCell()
            neighbors = self._neighbors(x, y)
            for nx, ny, ncell in neighbors:
                new_cell.food += ncell.food * 0.125
                new_cell.water += ncell.water * 0.125
                new_cell.shelter_quality += ncell.shelter_quality * 0.125

            new_cell.food += cell.food * 0.5
            new_cell.water += cell.water * 0.5
            new_cell.shelter_quality += cell.shelter_quality * 0.5
            new_cell.poison = cell.poison * 0.95

            shifted_x = (x + dx) % size
            shifted_y = (y + dy) % size
            base_capacity = self.cells.get((int(shifted_x), int(shifted_y)), ResourceCell())

            food_target = base_capacity.food_capacity * (0.8 + 0.4 * random.random())
            water_target = base_capacity.water_capacity * (0.8 + 0.4 * random.random())

            food_gap = food_target - new_cell.food
            new_cell.food += food_gap * params["food_growth"] * (1 - new_cell.food / max(food_target, 0.1))

            water_gap = water_target - new_cell.water
            new_cell.water += water_gap * params["water_growth"] * (1 - new_cell.water / max(water_target, 0.1))

            shelter_target = 0.5 + 0.3 * (1 if self.season == Season.WINTER else 0)
            new_cell.shelter_quality += (shelter_target - new_cell.shelter_quality) * params["shelter_growth"]

            biomass = new_cell.total_biomass()
            if biomass > self.cfg.carrying_capacity * 2:
                suppression = 1 - (biomass - self.cfg.carrying_capacity * 2) / (self.cfg.carrying_capacity * 4)
                new_cell.food *= max(0.5, suppression)
                new_cell.water *= max(0.5, suppression)

            for mod in self.modifications:
                if mod.is_active(self.tick) and mod.type in ("shelter", "cache"):
                    d = math.sqrt((x - mod.x) ** 2 + (y - mod.y) ** 2)
                    if d < 2:
                        strength = mod.current_strength(self.tick)
                        if mod.type == "shelter":
                            new_cell.shelter_quality += strength * 0.3

            new_cell.food = max(0, min(new_cell.food, 2.0))
            new_cell.water = max(0, min(new_cell.water, 2.0))
            new_cell.shelter_quality = max(0, min(new_cell.shelter_quality, 1.5))
            new_cell.poison = max(0, min(new_cell.poison, 1.0))
            new_cells[(x, y)] = new_cell

        self.cells = new_cells
        self.modifications = [m for m in self.modifications if m.is_active(self.tick)]

    def _neighbors(self, x: int, y: int):
        size = self.grid_size
        result = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx = (x + dx) % size
                ny = (y + dy) % size
                if (nx, ny) in self.cells:
                    result.append((nx, ny, self.cells[(nx, ny)]))
        return result

    def sense(self, x: float, y: float, radius: float = 2.0) -> dict:
        ix = int(x)
        iy = int(y)
        fx = x - ix
        fy = y - iy

        def sample(field: str) -> float:
            c00 = getattr(self.cells.get((ix, iy), ResourceCell()), field, 0.0)
            c10 = getattr(self.cells.get((ix + 1, iy), ResourceCell()), field, 0.0)
            c01 = getattr(self.cells.get((ix, iy + 1), ResourceCell()), field, 0.0)
            c11 = getattr(self.cells.get((ix + 1, iy + 1), ResourceCell()), field, 0.0)
            return c00 * (1 - fx) * (1 - fy) + c10 * fx * (1 - fy) + c01 * (1 - fx) * fy + c11 * fx * fy

        falloff = math.exp(-radius * 0.3)
        return {
            "food": sample("food") * falloff,
            "water": sample("water") * falloff,
            "shelter": sample("shelter_quality") * falloff,
            "poison": sample("poison") * falloff,
            "season": self.season.name,
            "season_progress": self.season_progress,
        }

    def deplete(self, x: float, y: float, resource_type: str, amount: float):
        ix = int(x)
        iy = int(y)
        if (ix, iy) in self.cells:
            cell = self.cells[(ix, iy)]
            current = getattr(cell, resource_type, 0.0)
            setattr(cell, resource_type, max(0, current - amount))
            if resource_type in ("food", "water"):
                cap_field = f"{resource_type}_capacity"
                current_cap = getattr(cell, cap_field, 1.0)
                setattr(cell, cap_field, max(0.1, current_cap - amount * 0.1))

    def add_modification(self, mod: WorldModification):
        self.modifications.append(mod)

    def get_modifications_near(self, x: float, y: float, radius: float = 3.0, tick: int = 0):
        return [m for m in self.modifications if m.is_active(tick) and math.sqrt((m.x - x) ** 2 + (m.y - y) ** 2) <= radius]

    def to_dict(self) -> dict:
        return {
            "grid_size": self.grid_size,
            "tick": self.tick,
            "season": self.season.name,
            "cells": {f"{x},{y}": {"food": c.food, "water": c.water, "shelter": c.shelter_quality, "poison": c.poison} for (x, y), c in self.cells.items()},
            "modifications": [{"type": m.type, "x": m.x, "y": m.y, "creator_id": m.creator_id, "tick_created": m.tick_created, "strength": m.strength} for m in self.modifications],
        }

    @classmethod
    def from_dict(cls, data: dict, config: WorldConfig) -> "EcosystemEngine":
        engine = cls(config)
        engine.tick = data.get("tick", 0)
        engine.season = Season[data.get("season", "SPRING")]
        for key, cell_data in data.get("cells", {}).items():
            x, y = map(int, key.split(","))
            cell = ResourceCell()
            cell.food = cell_data.get("food", 0.0)
            cell.water = cell_data.get("water", 0.0)
            cell.shelter_quality = cell_data.get("shelter", 0.0)
            cell.poison = cell_data.get("poison", 0.0)
            engine.cells[(x, y)] = cell
        for mod_data in data.get("modifications", []):
            engine.modifications.append(WorldModification(**mod_data))
        return engine
