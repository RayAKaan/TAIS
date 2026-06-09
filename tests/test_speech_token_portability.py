"""Tests for Phase A speech token portability benchmark."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from experiments.speech_token_portability import (
    make_mote, run_pretrain, run_eval, run_seed, run_experiment,
    ConditionResult, CONDITIONS,
)


def test_runner_imports():
    """Module imports without error."""
    assert len(CONDITIONS) == 3


def test_make_mote_trained_token():
    """trained_token condition teaches ka->DANGER with high strength."""
    mote = make_mote(0, "trained_token")
    dw = mote.speech.lexicon.table.get("ka", {}).get("DANGER", 0.0)
    assert dw > 0.5, f"DANGER weight for ka should be high, got {dw}"


def test_make_mote_no_token():
    """no_token condition does not teach DANGER for ka."""
    mote = make_mote(0, "no_token")
    dw = mote.speech.lexicon.table.get("ka", {}).get("DANGER", 0.0)
    assert dw < 0.02, f"DANGER weight for ka should be negligible, got {dw}"


def test_3_seed_smoke():
    """3-seed run completes without error."""
    results = run_experiment(3, 5, 5)
    for c in CONDITIONS:
        assert results[c].n == 3
        assert results[c].summary()["n"] == 3


def test_metrics_contain_avoid_bad_rate():
    """Output metrics include avoid_bad_rate."""
    results = run_experiment(3, 5, 5)
    for c in CONDITIONS:
        s = results[c].summary()
        assert "avoid_bad_rate" in s
        assert isinstance(s["avoid_bad_rate"], float)


def test_condition_result_record():
    """ConditionResult records and summarizes correctly."""
    cr = ConditionResult(condition="test")
    cr.record({
        "first_success_tick": 5.0,
        "succeeded": True,
        "avoid_bad_count": 3,
        "total_actions": 10,
        "final_energy": 80.0,
        "total_reward": 2.5,
        "invalid_actions": 1,
        "mean_prediction_error": 0.5,
    })
    s = cr.summary()
    assert s["n"] == 1
    assert s["first_success_tick"] == 5.0
    assert s["completion_rate"] == 1.0
    assert s["avoid_bad_rate"] == 0.3
    assert s["avoid_bad_count"] == 3.0
