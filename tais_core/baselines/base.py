from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, Tuple

from tais_core.reality import Consequence, RealityGraph, Transformation, WorldInterface


class BaselineAgent(Protocol):
    name: str

    def reset(self, seed: int = 0) -> None: ...

    def choose_action(
        self,
        world: WorldInterface,
        graph: RealityGraph,
        actions: List[Transformation],
        mote_state: Dict[str, Any],
        tick: int,
    ) -> Optional[Transformation]: ...

    def observe_outcome(
        self,
        world: WorldInterface,
        before: RealityGraph,
        action: Optional[Transformation],
        after: RealityGraph,
        consequence: Consequence,
        tick: int,
    ) -> None: ...


def run_agent_step(
    agent: BaselineAgent,
    world: WorldInterface,
    graph: RealityGraph,
    mote_state: Dict[str, Any],
    mote_position: Any,
    tick: int,
) -> Tuple[RealityGraph, Consequence, Optional[Transformation]]:
    observation = world.observe(graph, mote_position)
    actions = world.valid_actions(observation, mote_state)
    action = agent.choose_action(world, observation, actions, mote_state, tick)
    if action is None:
        cons = Consequence(penalty=0.2, valid=False, concept_signals={"VOID": 1.0},
                           explanation={"why": "no action chosen"})
        return graph, cons, None
    after, cons = world.act(graph, action, mote_state)
    agent.observe_outcome(world, graph, action, after, cons, tick)
    return after, cons, action
