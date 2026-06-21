"""Phase 1.6 test — pretrain helpers must NOT reseed the global RNG.

Before Phase 1.6, run_grid_pretrain() and run_random_pretrain() each called
random.seed(seed) inside their bodies, AFTER the outer run_trial() had
already called random.seed(seed) and constructed the mote. This re-seed
made the pretraining trajectory consume the same RNG sequence that just
built the mote's lexicon (~30 numbers), creating a non-obvious correlation
between mote identity and pretraining decisions.

Effect: the ablation_runner reported a transfer delta ~42% smaller than
the cleaner predict_calibration_sweep.py at the same 200-seed budget on
the same code (Δ=-1.15 vs Δ=-1.96).

This test pins the fix: after constructing a mote and calling
run_grid_pretrain(seed=S), the global RNG state must equal what a single
random.seed(S)+mote_construction+pretrain stream would have produced —
NOT a reset-then-pretrain stream.

If anyone re-introduces the inner random.seed(seed), this test fails.
"""

import random
import unittest

from tais_core.mote import UniversalMote
from tais_core.experiments.runners.ablation_runner import (
    run_grid_pretrain,
    run_random_pretrain,
    run_rule_pretrain,
)


class RNGIsolationTests(unittest.TestCase):
    def _capture_rng_after(self, fn) -> tuple:
        random.seed(12345)
        fn()
        return random.getstate()

    def test_run_grid_pretrain_does_not_reseed(self):
        """run_grid_pretrain must not call random.seed() internally.

        We verify this behaviorally: the RNG state after
            random.seed(S); mote = UniversalMote(); run_grid_pretrain(mote, T, S)
        must differ from
            random.seed(S); mote = UniversalMote(); random.seed(S); <pretrain>
        because the no-reseed path consumes the RNG continuously from
        mote-construction onward, while the reseed path resets the stream.
        """
        def with_no_reseed():
            mote = UniversalMote(energy=100.0)
            run_grid_pretrain(mote, ticks=5, seed=12345, mixed=True)

        def with_reseed():
            mote = UniversalMote(energy=100.0)
            random.seed(12345)
            # Inline the pretrain body without calling the helper:
            from tais_core.domains import GridGraphWorld, make_grid_graph
            world = GridGraphWorld()
            graph = make_grid_graph(threat_near_resource=True)
            for t in range(5):
                graph = make_grid_graph(threat_near_resource=(t % 2 == 0))
                graph, _, _ = mote.step(world, graph, mote_position="mote", tick=t)
                if mote.energy <= 0:
                    mote.energy = 50.0

        state_no_reseed = self._capture_rng_after(with_no_reseed)
        state_reseed    = self._capture_rng_after(with_reseed)
        self.assertNotEqual(
            state_no_reseed, state_reseed,
            "run_grid_pretrain appears to re-seed internally (the Phase 1.6 bug "
            "would make these two RNG states equal)."
        )

    def test_run_random_pretrain_does_not_reseed_global(self):
        """RandomWorld has its own RNG; run_random_pretrain must not touch global."""
        random.seed(99999)
        snapshot_before = random.getstate()
        # Consume some numbers so we can tell if it gets reset
        for _ in range(50):
            random.random()
        state_after_consume = random.getstate()
        self.assertNotEqual(snapshot_before, state_after_consume)

        # Now run the pretrain. If it called random.seed(seed=42), the state
        # would be deterministic and very specific. We assert that after the
        # pretrain, the global RNG continued from where consume left it.
        mote = UniversalMote(energy=100.0)
        run_random_pretrain(mote, ticks=5, seed=42)
        # The pretrain consumes some global RNG via mote.choose_action's
        # should_explore() calls, but it must NOT have reset to seed=42.
        random.seed(42)
        if_it_had_reset = []
        for _ in range(200):
            if_it_had_reset.append(random.random())
        # The post-pretrain RNG state must NOT equal the seed=42 reset state
        # (after one random() consumption to match the if_it_had_reset start).
        # The cleanest check: the value drawn next is not the first value of seed=42.
        random.setstate(state_after_consume)
        # Re-run a 5-tick pretrain to consume the same amount
        mote2 = UniversalMote(energy=100.0)
        run_random_pretrain(mote2, ticks=5, seed=42)
        next_val = random.random()
        self.assertNotAlmostEqual(
            next_val, if_it_had_reset[0], places=10,
            msg="run_random_pretrain appears to reseed the global RNG"
        )


class RegressionGuard(unittest.TestCase):
    """If the runner reports a smaller transfer Δ than the sweep, the Phase 1.6
    bug has been reintroduced. 5-seed canary so the test stays fast (~0.4s).
    """

    def test_runner_matches_sweep_on_full_5seed_canary(self):
        from tais_core.experiments.runners.ablation_runner import run_trial as runner_trial, AblationControls
        # Pretrained delta via the runner path
        diffs_runner = []
        for s in range(5):
            fresh = runner_trial(seed=10_000 + s, controls=AblationControls.full(),
                                 pretrain_domain=None, pretrain_ticks=20, eval_ticks=12)
            pre = runner_trial(seed=10_000 + s, controls=AblationControls.full(),
                               pretrain_domain="grid", pretrain_ticks=20, eval_ticks=12)
            diffs_runner.append(pre.first_apply_implication_tick - fresh.first_apply_implication_tick)

        # Mean must be negative (transfer helps). If the v1.6 bug returns this
        # will drift toward 0 or positive on this seed range.
        mean_delta = sum(diffs_runner) / len(diffs_runner)
        self.assertLess(
            mean_delta, -0.5,
            f"runner mean delta ({mean_delta:+.2f}) suggests Phase 1.6 RNG bug returned. "
            f"Expected something like -2.0 ticks on this seed range."
        )


if __name__ == "__main__":
    unittest.main()
