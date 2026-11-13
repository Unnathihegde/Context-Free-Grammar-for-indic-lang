from hybrid import agreement_violations, hybrid_score


TABLE = [
    {"form": "నేను", "type": "pronoun", "person": "1"},
    {"form": "నువ్వు", "type": "pronoun", "person": "2"},
    {"form": "ాను", "type": "verb_ending", "person": "1"},
    {"form": "ావు", "type": "verb_ending", "person": "2"},
]


def test_agreement_abstains_without_a_recognized_subject_or_ending():
    assert agreement_violations("పుస్తకం ఉంది", TABLE) is None
    assert agreement_violations("నేను పుస్తకం", TABLE) is None


def test_hybrid_equals_b1_for_abstention_or_zero_violations():
    assert hybrid_score(-3.25, None, 10) == -3.25
    assert hybrid_score(-3.25, 0, 10) == -3.25


def test_lambda_zero_and_larger_lambda_behavior():
    baseline = -2.0
    assert hybrid_score(baseline, 2, 0) == baseline
    assert hybrid_score(baseline, 2, 2) < hybrid_score(baseline, 2, 0.5)


def test_agreement_detects_a_person_mismatch_from_the_table():
    assert agreement_violations("నేను చేసావు", TABLE) == 1
    assert agreement_violations("నేను చేసాను", TABLE) == 0
