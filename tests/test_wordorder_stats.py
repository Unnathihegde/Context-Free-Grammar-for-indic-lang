import pytest

from run_wordorder import summarize_outcomes


def test_sentence_bootstrap_summary_uses_outcome_scores_not_sentence_ids():
    outcomes = [
        (10, 1.0, 0.0),
        (10, 1.0, 0.0),
        (99, 0.0, 1.0),
    ]

    summary = summarize_outcomes(outcomes)

    assert summary["pcfg_acc"] == pytest.approx(2 / 3)
    assert summary["bigram_acc"] == pytest.approx(1 / 3)
    assert summary["n_pairs"] == 3
