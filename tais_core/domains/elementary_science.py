from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional
from ..reality import Consequence, Entity, RealityGraph, Relation, Transformation, WorldInterface


class PhysicsWorld(WorldInterface):
    domain_name = "physics"

    def __init__(self):
        self.answer: Any = None

    def initial_graph(self) -> RealityGraph:
        g = RealityGraph(self.domain_name, "newtonian_mechanics")
        g.add_entity(Entity("obj1", "OBJECT", {"mass": 10.0, "acceleration": 0.0}))
        g.add_entity(Entity("force_ext", "FORCE", {"magnitude": 0.0, "direction": "positive"}))
        g.add_relation(Relation("force_ext", "APPLIED_TO", "obj1"))
        g.add_entity(Entity("target", "GOAL", {"required_accel": 5.0, "achieved": False}))
        return g

    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        return graph.neighborhood(mote_position or "obj1", hops=2)

    def valid_actions(self, graph: RealityGraph, mote_state: Dict) -> List[Transformation]:
        return [
            Transformation("increase_force", self.domain_name, "TRANSFORM", base_cost=0.2),
            Transformation("measure_acceleration", self.domain_name, "VERIFY", base_cost=0.3),
            Transformation("change_mass", self.domain_name, "MUTATE", base_cost=0.5),
        ]

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict) -> Tuple[RealityGraph, Consequence]:
        after = graph.snapshot()
        obj = after.get_entity("obj1")
        force = after.get_entity("force_ext")
        target = after.get_entity("target")

        if transformation.name == "increase_force":
            new_force = force.get("magnitude") + 10.0
            after.update_entity("force_ext", magnitude=new_force)
            new_accel = new_force / obj.get("mass")
            after.update_entity("obj1", acceleration=new_accel)
            required = target.get("required_accel")
            # Diminishing returns: reward decreases as we approach and pass target
            if abs(new_accel - required) < 0.5:
                reward = 2.0
            elif new_accel > required:
                reward = 0.1
            else:
                reward = 1.0
            return after, Consequence(reward=reward, explanation={"why": f"Force increased to {new_force}N, acceleration now {new_accel:.2f} m/s^2"})

        if transformation.name == "measure_acceleration":
            curr_a = obj.get("acceleration")
            required = target.get("required_accel")
            if abs(curr_a - required) < 0.01:
                after.update_entity("target", achieved=True)
                self.answer = f"{curr_a:.2f} m/s²"
                return after, Consequence(reward=10.0, task_signal="TASK_SUCCESS", explanation={"why": "Target acceleration achieved!"})
            # Small info reward if making progress — encourages periodic checks
            info_reward = 0.15 if curr_a > 0 else 0.0
            return graph, Consequence(reward=info_reward, explanation={"why": f"Current acceleration is {curr_a:.2f} m/s^2, need {required}"})

        if transformation.name == "change_mass":
            new_mass = max(1.0, obj.get("mass") - 2.0)
            after.update_entity("obj1", mass=new_mass)
            new_accel = force.get("magnitude") / new_mass
            after.update_entity("obj1", acceleration=new_accel)
            return after, Consequence(reward=0.5, explanation={"why": f"Mass reduced to {new_mass}kg, acceleration now {new_accel:.2f} m/s^2"})

        return graph, Consequence(penalty=0.5)

    def evaluate(self, graph: RealityGraph, mote_state: Dict) -> float:
        t = graph.get_entity("target")
        return 10.0 if t and t.get("achieved") else 0.0


class ChemistryWorld(WorldInterface):
    domain_name = "chemistry"

    def __init__(self):
        self.answer: Any = None

    def initial_graph(self) -> RealityGraph:
        g = RealityGraph(self.domain_name, "molecular_bonding")
        g.add_entity(Entity("o1", "ATOM", {"element": "Oxygen", "valence_electrons": 6, "needed": 2}))
        g.add_entity(Entity("h1", "ATOM", {"element": "Hydrogen", "valence_electrons": 1, "needed": 1}))
        g.add_entity(Entity("h2", "ATOM", {"element": "Hydrogen", "valence_electrons": 1, "needed": 1}))
        g.add_entity(Entity("molecule", "GOAL", {"stable": False}))
        return g

    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        return graph.neighborhood(mote_position or "o1", hops=2)

    def valid_actions(self, graph: RealityGraph, mote_state: Dict) -> List[Transformation]:
        actions = [
            Transformation("check_stability", self.domain_name, "VERIFY", base_cost=0.2),
        ]
        # Only offer form_bond if there are unbonded hydrogens
        h_atoms = [e for e in graph.entities() if e.get("element") == "Hydrogen"]
        o_atom = graph.get_entity("o1")
        if o_atom and o_atom.get("needed", 0) > 0:
            actions.insert(0, Transformation("form_bond", self.domain_name, "COMPOSE", base_cost=0.4))
        return actions

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict) -> Tuple[RealityGraph, Consequence]:
        after = graph.snapshot()

        if transformation.name == "form_bond":
            h_atoms = [e for e in after.entities() if e.get("element") == "Hydrogen"]
            o_atom = after.get_entity("o1")
            for h in h_atoms:
                if not after.get_relation(h.id, "BONDED_TO", "o1"):
                    after.add_relation(Relation(h.id, "BONDED_TO", "o1", directed=False))
                    after.update_entity("o1", needed=max(0, o_atom.get("needed") - 1))
                    return after, Consequence(reward=2.0, explanation={"why": f"Formed bond between {h.id} and O"})
            return graph, Consequence(penalty=0.5, explanation={"why": "No available sites for bonding"})

        if transformation.name == "check_stability":
            o = after.get_entity("o1")
            if o.get("needed") == 0:
                after.update_entity("molecule", stable=True)
                self.answer = "H₂O"
                return after, Consequence(reward=10.0, task_signal="TASK_SUCCESS", explanation={"why": "Molecule H2O is stable!"})
            return graph, Consequence(penalty=0.3, reward=0.0, explanation={"why": "Molecule still unstable, need to form more bonds"})

        return graph, Consequence(penalty=0.5)

    def evaluate(self, graph: RealityGraph, mote_state: Dict) -> float:
        m = graph.get_entity("molecule")
        return 10.0 if m and m.get("stable") else 0.0


def make_physics_graph(**kwargs):
    return PhysicsWorld().initial_graph()

def make_chemistry_graph(**kwargs):
    return ChemistryWorld().initial_graph()
