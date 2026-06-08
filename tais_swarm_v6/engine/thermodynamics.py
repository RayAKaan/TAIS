"""
Real thermodynamic engine for TAIS Swarm V6.

V5.5 had cosmetic energy (resets when depleted). V6 treats energy as a
hard constraint with entropy, heat dissipation, and irreversible processes.

Key principles:
1. Energy is conserved (except entropy loss)
2. No resets — death is permanent
3. Actions have real thermodynamic costs
4. Shelter reduces heat loss (thermodynamic efficiency)
5. Reproduction transfers actual energy (not magic creation)
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

from .config import ThermoConfig


class ThermodynamicState:
    """The complete thermodynamic state of an agent."""

    def __init__(
        self,
        energy: float,
        hydration: float,
        toxicity: float,
        heat: float,
    ):
        self.energy = energy
        self.hydration = hydration
        self.toxicity = toxicity
        self.heat = heat

    @property
    def vitality(self) -> float:
        return min(self.energy, self.hydration) - self.toxicity * 2.0 - max(0, self.heat - 20) * 0.5

    def is_alive(self, config: ThermoConfig) -> bool:
        return self.energy > config.death_energy and self.hydration > config.death_hydration

    def can_reproduce(self, config: ThermoConfig) -> bool:
        return (
            self.energy >= config.mitosis_energy
            and self.hydration >= config.mitosis_hydration
            and self.toxicity < 20
        )


class ThermodynamicEngine:
    """Processes all thermodynamic interactions."""

    def __init__(self, config: ThermoConfig, shout_cost_mult: float = 1.0):
        self.cfg = config
        self._shout_cost_mult = shout_cost_mult

    def metabolize(self, state: ThermodynamicState, sensed: dict, in_shelter: bool = False) -> ThermodynamicState:
        """
        One tick of metabolism. Returns new state (immutable update).

        Energy flow:
        1. Intake: food -> chemical energy (with efficiency loss)
        2. Basal: passive metabolism cost
        3. Entropy: irreversible heat loss
        4. Heat dissipation: shelter reduces this
        5. Hydration: water intake minus passive loss
        6. Toxicity: poison accumulation minus decay
        7. Heat stress: if heat > threshold, damage to energy
        """
        food = sensed.get("food", 0.0)
        water = sensed.get("water", 0.0)
        shelter = sensed.get("shelter", 0.0)
        poison = sensed.get("poison", 0.0)

        # 1. Energy intake (diminishing returns at high energy)
        energy_capacity = self.cfg.max_energy - state.energy
        food_efficiency = 0.6 + 0.4 * (energy_capacity / self.cfg.max_energy)
        energy_gain = min(food * 5.5 * food_efficiency, energy_capacity * 0.3)

        # 2. Basal metabolism
        basal_cost = self.cfg.base_metabolism

        # 3. Entropy (irreversible — this energy is GONE)
        entropy_loss = self.cfg.entropy_rate * (1 + state.heat / 50)

        # 4. Heat dissipation (shelter helps)
        shelter_bonus = 0.4 if shelter > 2.0 and in_shelter else 0.0
        heat_loss = self.cfg.heat_dissipation * (1 - shelter_bonus)

        # 5. Hydration
        hydration_capacity = self.cfg.max_hydration - state.hydration
        water_gain = min(water * 6.5, hydration_capacity * 0.4)
        hydration_cost = self.cfg.hydration_decay

        # 6. Toxicity
        tox_gain = poison * 0.8
        tox_decay = state.toxicity * self.cfg.toxicity_decay

        # 7. Heat dynamics
        metabolic_heat = basal_cost * 0.3
        new_heat = state.heat + metabolic_heat - heat_loss
        new_heat = max(0, min(new_heat, 100))

        # 8. Heat stress damage
        heat_stress = 0.0
        if new_heat > 60:
            heat_stress = (new_heat - 60) * 0.08
        elif new_heat < 10:
            heat_stress = (10 - new_heat) * 0.05

        # 9. Dehydration damage
        dehydration_damage = 0.0
        if state.hydration < 0:
            dehydration_damage = abs(state.hydration) * 0.25 + self.cfg.dehydration_damage

        # Compute new state
        new_energy = state.energy + energy_gain - basal_cost - entropy_loss - heat_stress - dehydration_damage
        new_hydration = state.hydration + water_gain - hydration_cost
        new_toxicity = state.toxicity + tox_gain - tox_decay

        # Clamp
        new_energy = max(0, min(new_energy, self.cfg.max_energy))
        new_hydration = max(-50, min(new_hydration, self.cfg.max_hydration))
        new_toxicity = max(0, min(new_toxicity, 100))

        return ThermodynamicState(
            energy=new_energy,
            hydration=new_hydration,
            toxicity=new_toxicity,
            heat=new_heat,
        )

    def action_cost(self, action_type: str) -> Tuple[float, float, float]:
        """Return (energy_cost, hydration_cost, heat_generated) for an action."""
        costs = {
            "move": (self.cfg.move_cost, 0.05, 0.3),
            "speak": (self.cfg.speak_cost, 0.1, 0.2),
            "shout": (self.cfg.speak_cost * self._shout_cost_mult, 0.2, 0.5),
            "whisper": (self.cfg.speak_cost * 0.3, 0.02, 0.05),
            "build": (self.cfg.build_cost, 1.0, 2.0),
            "mark": (self.cfg.mark_cost, 0.05, 0.1),
            "listen": (0.05, 0.0, 0.0),
        }
        return costs.get(action_type, (0.5, 0.05, 0.1))

    def apply_action(self, state: ThermodynamicState, action_type: str) -> ThermodynamicState:
        e_cost, h_cost, heat_gen = self.action_cost(action_type)
        return ThermodynamicState(
            energy=max(0, state.energy - e_cost),
            hydration=state.hydration - h_cost,
            toxicity=state.toxicity,
            heat=min(100, state.heat + heat_gen),
        )

    def can_afford(self, state: ThermodynamicState, action_type: str) -> bool:
        e_cost, h_cost, _ = self.action_cost(action_type)
        return (
            state.energy - e_cost > self.cfg.death_energy + self.cfg.base_metabolism * 3
            and state.hydration - h_cost > self.cfg.death_hydration + 5
        )

    def reproduce(self, parent_state: ThermodynamicState) -> Tuple[ThermodynamicState, ThermodynamicState]:
        """
        Parent gives energy to child.
        Returns (parent_new_state, child_initial_state).
        """
        if not self.can_reproduce(parent_state):
            raise ValueError("Parent cannot afford reproduction")

        transfer = parent_state.energy * self.cfg.reproduction_cost

        parent_new = ThermodynamicState(
            energy=parent_state.energy - transfer,
            hydration=parent_state.hydration * 0.6,
            toxicity=parent_state.toxicity * 0.15,
            heat=parent_state.heat * 0.8,
        )

        child_initial = ThermodynamicState(
            energy=transfer,
            hydration=parent_state.hydration * 0.4,
            toxicity=parent_state.toxicity * 0.05,
            heat=parent_state.heat * 0.5,
        )

        return parent_new, child_initial
