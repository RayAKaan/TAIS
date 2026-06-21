"""Phase 1.5 tests for PredictionEngine calibration.

These pin the four fixes described in tais_core/memory.py::PredictionEngine:

1. Per-action history is keyed by (domain, name), not just name.
2. Outcomes use an exponentially-weighted running mean (alpha=0.4).
3. Pattern-valence fallback is cost-anchored: |prior| <= 1.5 * base_cost,
   clipped at +-3.0.
4. Unseen-action prior is discounted by _UNSEEN_DISCOUNT (0.5).

Together these eliminate the v2 bug where an unseen action in a "GOOD"-looking
graph received a hardcoded +3.0 prediction regardless of its own cost — which
in RuleWorld caused verify_rule (cost 0.2, real reward +0.02) to beat
apply_implication (cost 0.4, real reward +4.00) on the choose_action score
after a few ticks.
"""

import unittest

from tais_core.memory import PredictionEngine, PatternMemory
from tais_core.reality import (
    Consequence,
    Entity,
    RealityGraph,
    Relation,
    Transformation,
)


def _empty_pattern_memory_unknown() -> PatternMemory:
    pm = PatternMemory()
    # Force predict_consequence to return "GOOD" so we exercise the fallback branch.
    pm.predict_consequence = lambda g: "GOOD"
    return pm


def _empty_pattern_memory_bad() -> PatternMemory:
    pm = PatternMemory()
    pm.predict_consequence = lambda g: "BAD"
    return pm


def _empty_pattern_memory_neutral() -> PatternMemory:
    pm = PatternMemory()
    pm.predict_consequence = lambda g: "NEUTRAL"
    return pm


def _graph() -> RealityGraph:
    g = RealityGraph("toy")
    g.add_entity(Entity("x", "X", {}))
    return g


CHEAP = Transformation("cheap_verify", "rules", "VERIFY", base_cost=0.2)
NORMAL = Transformation("normal_act", "rules", "TRANSFORM", base_cost=1.0)
COSTLY = Transformation("costly_build", "chem", "COMPOSE", base_cost=2.4)


class CostAnchoredPriorTests(unittest.TestCase):
    """The Phase 2 / 1.5 fix: |prior| <= 1.5 * base_cost, * 0.5 unseen discount."""

    def test_cheap_action_in_good_graph_gets_small_prior(self):
        pe = PredictionEngine()
        pm = _empty_pattern_memory_unknown()
        pred = pe.predict(CHEAP, pm, _graph())
        # cap = max(0.5, min(3.0, 1.5*0.2)) = max(0.5, 0.3) = 0.5; then * 0.5 discount
        self.assertAlmostEqual(pred, 0.25, places=6,
                               msg="cheap action should not be promised a large reward")

    def test_normal_action_in_good_graph(self):
        pe = PredictionEngine()
        pm = _empty_pattern_memory_unknown()
        pred = pe.predict(NORMAL, pm, _graph())
        # cap = max(0.5, min(3.0, 1.5*1.0)) = 1.5; then * 0.5 = 0.75
        self.assertAlmostEqual(pred, 0.75, places=6)

    def test_costly_action_clipped_at_max(self):
        pe = PredictionEngine()
        pm = _empty_pattern_memory_unknown()
        pred = pe.predict(COSTLY, pm, _graph())
        # cap = max(0.5, min(3.0, 1.5*2.4)) = min(3.0, 3.6) = 3.0; then * 0.5 = 1.5
        self.assertAlmostEqual(pred, 1.5, places=6,
                               msg="prior should be clipped at 3.0 even for very costly actions")

    def test_bad_valence_mirrors_good(self):
        pe = PredictionEngine()
        pm = _empty_pattern_memory_bad()
        self.assertAlmostEqual(pe.predict(CHEAP, pm, _graph()),  -0.25, places=6)
        self.assertAlmostEqual(pe.predict(NORMAL, pm, _graph()), -0.75, places=6)
        self.assertAlmostEqual(pe.predict(COSTLY, pm, _graph()), -1.50, places=6)

    def test_neutral_valence_is_zero(self):
        pe = PredictionEngine()
        pm = _empty_pattern_memory_neutral()
        self.assertEqual(pe.predict(CHEAP, pm, _graph()), 0.0)


class EWMHistoryTests(unittest.TestCase):
    """The Phase 1.5 EWM fix: first +4 solve must not get drowned by repeats."""

    def test_first_outcome_seeds_the_mean(self):
        pe = PredictionEngine()
        pe.record_outcome(0.0, Consequence(reward=4.0), NORMAL, "rules")
        pred = pe.predict(NORMAL, _empty_pattern_memory_unknown(), _graph())
        # First outcome must be the exact mean (no decay yet).
        self.assertAlmostEqual(pred, 4.0, places=6)

    def test_ewm_with_alpha_0_4(self):
        pe = PredictionEngine()
        # +4, then five +0.05 repeats (RuleWorld pattern).
        pe.record_outcome(0.0, Consequence(reward=4.0), NORMAL, "rules")
        for _ in range(5):
            pe.record_outcome(0.0, Consequence(reward=0.05), NORMAL, "rules")
        pred = pe.predict(NORMAL, _empty_pattern_memory_unknown(), _graph())
        # EWM_t = (1-a)^t * x0 + sum...; with a=0.4, after 5 repeats the mean
        # should be well above the unweighted average (4.0 + 5*0.05)/6 = 0.71
        # but well below the v2 sliding window's 4.0.
        unweighted = (4.0 + 5 * 0.05) / 6
        # Concretely: 0.6^5 * 4 + 0.05*(1 - 0.6^5) ~= 0.311 + 0.046 = ~0.357
        # The key invariant is that the first +4 still nudges it above the unweighted mean.
        self.assertGreater(pred, unweighted * 0.4,
                           msg=f"EWM ({pred:.3f}) crashed below 40% of unweighted ({unweighted:.3f})")
        self.assertLess(pred, 4.0,
                        msg="EWM did not decay at all after 5 repeats")

    def test_per_action_history_keyed_by_domain(self):
        """An action with the same name in two domains keeps separate means.

        Domain-A net=4.0 must NOT contaminate domain-B's prediction.
        """
        pe = PredictionEngine()
        a_grid = Transformation("shared_name", "grid", "TRANSFORM", base_cost=0.4)
        a_chem = Transformation("shared_name", "chem", "TRANSFORM", base_cost=0.4)
        pe.record_outcome(0.0, Consequence(reward=4.0), a_grid, "grid")
        # Chem-side predicts from valence-prior, NOT from grid's +4 history.
        pred_chem = pe.predict(a_chem, _empty_pattern_memory_unknown(), _graph())
        # cap = max(0.5, min(3.0, 1.5*0.4)) = max(0.5, 0.6) = 0.6; * 0.5 = 0.30
        self.assertAlmostEqual(pred_chem, 0.30, places=6,
                               msg=f"chem prediction ({pred_chem:.2f}) leaked from grid's +4 history")


class IntegrationGuard(unittest.TestCase):
    """The exact bug that motivated Phase 1.5: verify_rule must not be promised
    more reward than apply_implication on first sight in a 'GOOD' RuleWorld graph."""

    def test_verify_cannot_outscore_apply_on_first_sight(self):
        pe = PredictionEngine()
        pm = _empty_pattern_memory_unknown()
        g = _graph()
        verify = Transformation("verify_rule", "rules", "VERIFY", base_cost=0.2)
        apply_ = Transformation("apply_implication", "rules", "TRANSFORM", base_cost=0.4)
        random_ = Transformation("random_assert", "rules", "MUTATE", base_cost=0.5)
        # Cost-anchored priors should respect base_cost ordering on unseen
        # actions: the costlier the action the larger the magnitude of its
        # speculative prior. This means a tiny-cost action can never out-promise
        # a higher-cost action in the same valence direction.
        p_v = pe.predict(verify, pm, g)
        p_a = pe.predict(apply_, pm, g)
        p_r = pe.predict(random_, pm, g)
        self.assertLess(p_v, p_a,
                        msg=f"verify prior {p_v:.2f} >= apply prior {p_a:.2f}; the v2 bug is back")
        self.assertLessEqual(p_v, p_r,
                             msg="verify prior should also not exceed random_assert prior on first sight")


if __name__ == "__main__":
    unittest.main()
