"""Phase 2 tests for the hardened RuleWorld.

These pin down the behavioral contract the ablation v2 runner relies on:

- TASK_SUCCESS is emitted exactly once per trial (on first target derivation)
- verify_rule cannot accumulate enough reward to mimic a real solution
- chain world requires TASK_PROGRESS before TASK_SUCCESS
- distractor world still has a unique TASK_SUCCESS path
- evaluate() reflects the explicit TARGET marker
"""

import unittest

from tais_core.domains import (
    RuleWorld,
    RuleWorldChain,
    RuleWorldDistractor,
    make_rule_graph,
    make_rule_graph_chain,
    make_rule_graph_distractor,
)
from tais_core.domains.rules import (
    APPLY_REWARD_FIRST,
    VERIFY_REWARD,
    RANDOM_ASSERT_PENALTY,
)
from tais_core.reality import Transformation


APPLY = Transformation("apply_implication", "rules", "TRANSFORM", base_cost=0.4)
VERIFY = Transformation("verify_rule", "rules", "VERIFY", base_cost=0.2)
RANDOM = Transformation("random_assert", "rules", "MUTATE", base_cost=0.5)


class RuleWorldV2EasyTests(unittest.TestCase):
    def setUp(self):
        self.world = RuleWorld()
        self.graph = make_rule_graph()

    def test_target_marker_present(self):
        tgt = self.graph.get_entity("TARGET")
        self.assertIsNotNone(tgt)
        self.assertEqual(tgt.get("derive_id"), "fact_b_known")

    def test_evaluate_initial_zero(self):
        self.assertEqual(self.world.evaluate(self.graph, {}), 0.0)

    def test_first_apply_emits_TASK_SUCCESS(self):
        new_graph, cons = self.world.act(self.graph, APPLY, {})
        self.assertEqual(cons.task_signal, "TASK_SUCCESS")
        self.assertEqual(cons.reward, APPLY_REWARD_FIRST)
        self.assertTrue(cons.valid)
        self.assertIsNotNone(new_graph.get_entity("fact_b_known"))
        self.assertEqual(self.world.evaluate(new_graph, {}), 10.0)

    def test_repeat_apply_is_near_neutral(self):
        g2, _ = self.world.act(self.graph, APPLY, {})
        _, cons2 = self.world.act(g2, APPLY, {})
        # second apply must NOT emit TASK_SUCCESS again and must give a tiny reward
        self.assertNotEqual(cons2.task_signal, "TASK_SUCCESS")
        self.assertLess(cons2.reward, 0.5)

    def test_verify_reward_cannot_mimic_solution(self):
        """Critical: this is the metric-leak fix.

        In v1, verify_rule paid +1.5, so 3 verifies > 1 apply_implication.
        Reviewers would (rightly) ask whether transfer scores came from
        verify-spamming. Here we assert that 100 verifies still pay less than
        one real solution.
        """
        total = 0.0
        for _ in range(100):
            _, cons = self.world.act(self.graph, VERIFY, {})
            total += cons.reward
        self.assertLess(total, APPLY_REWARD_FIRST,
                        f"verify spam ({total:.2f}) must not exceed one true solution "
                        f"({APPLY_REWARD_FIRST}); the v1 metric-leak would fail here")

    def test_random_assert_penalty(self):
        _, cons = self.world.act(self.graph, RANDOM, {})
        self.assertEqual(cons.penalty, RANDOM_ASSERT_PENALTY)
        self.assertEqual(cons.task_signal, "TASK_FAILURE")
        self.assertFalse(cons.valid)


class RuleWorldV2ChainTests(unittest.TestCase):
    def setUp(self):
        self.world = RuleWorldChain()
        self.graph = make_rule_graph_chain()

    def test_chain_requires_two_steps_to_succeed(self):
        # First apply: derives fact_b_known (TASK_PROGRESS, not SUCCESS).
        g1, cons1 = self.world.act(self.graph, APPLY, {})
        self.assertEqual(cons1.task_signal, "TASK_PROGRESS")
        self.assertIsNotNone(g1.get_entity("fact_b_known"))
        self.assertIsNone(g1.get_entity("fact_c_known"))
        self.assertEqual(self.world.evaluate(g1, {}), 0.0)
        # Second apply: derives fact_c_known (the actual target).
        g2, cons2 = self.world.act(g1, APPLY, {})
        self.assertEqual(cons2.task_signal, "TASK_SUCCESS")
        self.assertIsNotNone(g2.get_entity("fact_c_known"))
        self.assertEqual(self.world.evaluate(g2, {}), 10.0)


class RuleWorldV2DistractorTests(unittest.TestCase):
    def setUp(self):
        self.world = RuleWorldDistractor()
        self.graph = make_rule_graph_distractor()

    def test_distractor_still_has_unique_solution(self):
        g, cons = self.world.act(self.graph, APPLY, {})
        # The only satisfied implication is rule_ab → fact_b, so success on
        # first apply is the right behavior even amid distractors.
        self.assertEqual(cons.task_signal, "TASK_SUCCESS")

    def test_distractor_graph_has_real_distractors(self):
        # Sanity: more than one IMPLIES relation, but only one is SATISFIED.
        implies = self.graph.relations("IMPLIES")
        satisfies = self.graph.relations("SATISFIES")
        self.assertGreater(len(implies), 1)
        self.assertEqual(len(satisfies), 1)


if __name__ == "__main__":
    unittest.main()
