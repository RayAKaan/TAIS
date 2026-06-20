"""Web Navigation domain implementation for TAIS."""

from __future__ import annotations
import random
from typing import Any, Dict, List, Tuple, Optional

from ..reality import Consequence, Entity, RealityGraph, Relation, Transformation, WorldInterface


def make_webnav_graph(goal_id: str = "btn1") -> RealityGraph:
    """Creates a simulated web environment graph."""
    g = RealityGraph("webnav", "web_env_v1")

    # Global state & Goal
    g.add_entity(Entity("nav", "NAVIGATION", {"depth": 0, "max_depth": 3}))
    g.add_entity(Entity("goal", "GOAL", {"target_id": goal_id, "satisfied": False}))

    # Page 1: Home
    g.add_entity(Entity("page1", "PAGE", {"url": "home", "title": "Home"}))
    g.add_relation(Relation("nav", "NAVIGATES", "page1"))

    # Elements on Home
    g.add_entity(Entity("link_to_form", "ELEMENT", {"tag": "a", "text": "Sign Up", "role": "link"}))
    g.add_entity(Entity("ad_popup", "ELEMENT", {"tag": "div", "text": "ADVERTISEMENT", "role": "ad", "annoying": True}))

    g.add_relation(Relation("page1", "CONTAINS", "link_to_form"))
    g.add_relation(Relation("page1", "CONTAINS", "ad_popup"))

    # Page 2: Form
    g.add_entity(Entity("page2", "PAGE", {"url": "signup", "title": "Sign Up"}))
    g.add_relation(Relation("link_to_form", "LINKS_TO", "page2"))

    g.add_entity(Entity("form1", "FORM", {"action": "/submit"}))
    g.add_entity(Entity("btn1", "ELEMENT", {"tag": "button", "text": "Submit", "role": "submit"}))

    g.add_relation(Relation("page2", "CONTAINS", "form1"))
    g.add_relation(Relation("form1", "CONTAINS", "btn1"))

    # Goal targeting
    g.add_relation(Relation("goal", "TARGETS", "btn1"))

    return g


class WebNavWorld(WorldInterface):
    """
    Simulated Web Navigation domain.

    Structural Transfer mappings:
    - GridWorld: THREAT -> WebNav: AD/POPUP
    - GridWorld: RESOURCE -> WebNav: RELEVANT_LINK / SUBMIT_BUTTON
    - GridWorld: NEAR -> WebNav: CONTAINS
    """
    domain_name = "webnav"

    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        pos = mote_position or "nav"
        return graph.neighborhood(pos, hops=2)

    def valid_actions(self, graph: RealityGraph, mote_state: Dict) -> List[Transformation]:
        return [
            Transformation("click_link", self.domain_name, "MOVE_TOWARD", base_cost=0.3, role_hint="APPROACH_GOOD"),
            Transformation("submit_form", self.domain_name, "TRANSFORM", base_cost=0.5, role_hint="TRANSFORM_TOWARD_GOAL"),
            Transformation("scan_page", self.domain_name, "VERIFY", base_cost=0.2, role_hint="VERIFY_UNCERTAIN"),
            Transformation("close_modal", self.domain_name, "MOVE_AWAY", base_cost=0.2, role_hint="AVOID_BAD"),
            Transformation("scroll_down", self.domain_name, "OBSERVE", base_cost=0.1, role_hint="EXPLORE_UNCERTAIN"),
        ]

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict) -> Tuple[RealityGraph, Consequence]:
        before = graph.snapshot()
        after = graph.snapshot()

        nav = graph.get_entity("nav")
        current_pages = graph.neighbors_out("nav", "NAVIGATES")
        if not current_pages:
            return graph, Consequence(penalty=0.5, valid=False, explanation={"why": "lost navigation"})

        curr_page_rel, curr_page = current_pages[0]

        if transformation.name == "click_link":
            links = graph.neighbors_out(curr_page.id, "CONTAINS")
            valid_link = None
            for rel, el in links:
                if el.get("role") == "link":
                    valid_link = el
                    break

            if valid_link:
                targets = graph.neighbors_out(valid_link.id, "LINKS_TO")
                if targets:
                    _, next_page = targets[0]
                    after.remove_relation("nav", "NAVIGATES", curr_page.id)
                    after.add_relation(Relation("nav", "NAVIGATES", next_page.id))
                    return after, Consequence(
                        reward=2.0,
                        concept_signals={"GOOD": 0.5, "PROGRESS": 1.0},
                        explanation={"why": f"navigated to {next_page.id}"}
                    )

            return graph, Consequence(penalty=0.5, explanation={"why": "no clickable link found"})

        if transformation.name == "close_modal":
            elements = graph.neighbors_out(curr_page.id, "CONTAINS")
            ad = None
            for rel, el in elements:
                if el.get("role") == "ad":
                    ad = el
                    break

            if ad:
                after.remove_relation(curr_page.id, "CONTAINS", ad.id)
                after.remove_entity(ad.id)
                return after, Consequence(
                    reward=4.0,
                    concept_signals={"SAFE": 1.0, "GOOD": 0.5},
                    explanation={"why": "closed annoying ad"}
                )
            return graph, Consequence(penalty=0.2, explanation={"why": "nothing to close"})

        if transformation.name == "submit_form":
            elements = graph.neighbors_out(curr_page.id, "CONTAINS")
            form = None
            for rel, el in elements:
                if el.etype == "FORM":
                    form = el
                    break

            if form:
                form_elements = graph.neighbors_out(form.id, "CONTAINS")
                submit_btn = None
                for rel, el in form_elements:
                    if el.get("role") == "submit":
                        submit_btn = el
                        break

                if submit_btn:
                    goal = graph.get_entity("goal")
                    if goal and goal.get("target_id") == submit_btn.id:
                        after.update_entity("goal", satisfied=True)
                        return after, Consequence(
                            reward=10.0,
                            concept_signals={"GOOD": 1.0, "SUCCESS": 1.0},
                            task_signal="TASK_SUCCESS",
                            explanation={"why": "goal reached via form submission"}
                        )

            return graph, Consequence(penalty=1.0, explanation={"why": "submit failed"})

        if transformation.name == "scan_page":
            has_ad = any(el.get("role") == "ad" for _, el in graph.neighbors_out(curr_page.id, "CONTAINS"))
            reward = 1.5 if has_ad else 0.5
            return graph, Consequence(
                reward=reward,
                concept_signals={"DANGER": 0.5 if has_ad else 0.0, "TRUST": 0.3},
                explanation={"why": "scanned page for features"}
            )

        if transformation.name == "scroll_down":
            return graph, Consequence(reward=0.1, explanation={"why": "scrolled"})

        return graph, Consequence(penalty=1.0, valid=False)

    def evaluate(self, graph: RealityGraph, mote_state: Dict) -> float:
        goal = graph.get_entity("goal")
        if goal and goal.get("satisfied"):
            return 10.0
        return 0.0

    def concepts(self) -> List[str]:
        return ["GOOD", "BAD", "SAFE", "DANGER", "PROGRESS", "SUCCESS", "TRUST"]
