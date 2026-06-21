"""Tests for the WebNav (Web Navigation) domain."""

import random
import unittest

from tais_core.domains.registry import load_domain
from tais_core.domains.webnav import WebNavWorld, make_webnav_graph
from tais_core.mote import UniversalMote
from tais_core.reality import Entity, Relation, Transformation


class WebNavWorldTests(unittest.TestCase):
    def setUp(self):
        self.world = WebNavWorld()
        self.graph = make_webnav_graph()

    def test_initial_graph_has_two_pages(self):
        pages = self.graph.entities("PAGE")
        self.assertEqual(len(pages), 2)

    def test_initial_graph_has_goal_targeting_submit_button(self):
        goal = self.graph.get_entity("goal")
        self.assertEqual(goal.get("target_id"), "btn1")

    def test_navigates_from_page1_to_page2(self):
        g = self.graph
        g, cons = self.world.act(g, Transformation("click_link", "webnav", "MOVE_TOWARD", base_cost=0.3), {})
        curr_pages = g.neighbors_out("nav", "NAVIGATES")
        self.assertEqual(len(curr_pages), 1)
        _, curr = curr_pages[0]
        self.assertEqual(curr.id, "page2")
        self.assertGreater(cons.net, 0)

    def test_click_link_without_link_fails(self):
        g = self.graph
        g.remove_relation("page1", "CONTAINS", "link_to_form")
        _, cons = self.world.act(g, Transformation("click_link", "webnav", "MOVE_TOWARD", base_cost=0.3), {})
        self.assertLess(cons.net, 0)

    def test_submit_form_on_page2_succeeds(self):
        g = self.graph
        g, _ = self.world.act(g, Transformation("click_link", "webnav", "MOVE_TOWARD", base_cost=0.3), {})
        _, cons = self.world.act(g, Transformation("submit_form", "webnav", "TRANSFORM", base_cost=0.5), {})
        self.assertEqual(cons.task_signal, "TASK_SUCCESS")

    def test_submit_form_on_wrong_page_fails(self):
        _, cons = self.world.act(self.graph, Transformation("submit_form", "webnav", "TRANSFORM", base_cost=0.5), {})
        self.assertLess(cons.net, 0)

    def test_close_modal_removes_ad(self):
        g = self.graph
        after, cons = self.world.act(g, Transformation("close_modal", "webnav", "MOVE_AWAY", base_cost=0.2), {})
        ads = [e for e in after.entities("ELEMENT") if e.get("role") == "ad"]
        self.assertEqual(len(ads), 0)
        self.assertGreater(cons.net, 0)

    def test_close_modal_without_ad_fails(self):
        g = self.graph
        g.remove_entity("ad_popup")
        _, cons = self.world.act(g, Transformation("close_modal", "webnav", "MOVE_AWAY", base_cost=0.2), {})
        self.assertLess(cons.net, 0)

    def test_scan_page_detects_ad(self):
        _, cons = self.world.act(self.graph, Transformation("scan_page", "webnav", "VERIFY", base_cost=0.2), {})
        self.assertGreater(cons.reward, 0)

    def test_mote_can_step_without_crashing(self):
        mote = UniversalMote(energy=100)
        for t in range(5):
            g, cons, action = mote.step(self.world, self.graph, mote_position="nav", tick=t)
            self.assertIsNotNone(g)
            self.assertIsNotNone(cons)

    def test_mote_solves_navigation_task(self):
        random.seed(42)
        mote = UniversalMote(energy=500)
        for d in ["grid", "rules"]:
            w = load_domain(d)
            g = w.initial_graph()
            pos = "mote" if d == "grid" else "rule_ab"
            for t in range(5):
                mote.step(w, g, mote_position=pos, tick=t)
        g = self.graph
        solved = False
        for t in range(50):
            g, cons, action = mote.step(self.world, g, mote_position="nav", tick=t)
            if cons.task_signal == "TASK_SUCCESS":
                solved = True
                break
        self.assertTrue(solved, "Mote should solve WebNav within 50 ticks with pretrain")

    def test_deep_tree_navigation_three_pages(self):
        g = make_webnav_graph(goal_id="btn1")
        g.add_entity(Entity("page3", "PAGE", {"title": "Deep Data"}))
        g.add_entity(Entity("link_to_deep", "ELEMENT", {"role": "link", "text": "Next"}))
        g.add_relation(Relation("page2", "CONTAINS", "link_to_deep"))
        g.add_relation(Relation("link_to_deep", "LINKS_TO", "page3"))
        g.add_entity(Entity("form2", "FORM", {"action": "/deep"}))
        g.add_entity(Entity("btn2", "ELEMENT", {"tag": "button", "text": "Deep Submit", "role": "submit"}))
        g.add_relation(Relation("page3", "CONTAINS", "form2"))
        g.add_relation(Relation("form2", "CONTAINS", "btn2"))
        g.update_entity("goal", target_id="btn2")

        mote = UniversalMote(energy=500)
        solved = False
        for t in range(100):
            g, cons, action = mote.step(self.world, g, mote_position="nav", tick=t)
            if cons.task_signal == "TASK_SUCCESS":
                solved = True
                break
        self.assertTrue(solved, "Mote should navigate 3-level deep tree within 100 ticks")
