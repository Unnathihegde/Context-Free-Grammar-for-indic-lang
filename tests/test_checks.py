"""Tests for syntactic pattern checks in src/checks.py.

All tests are pure-function unit tests with mock tokens; no Stanza model is required.
"""

from src.checks import (
    check_amod_before_noun,
    check_case_after_noun,
    check_det_before_noun,
    check_subject_verb_agreement,
    check_unknown_tokens,
    check_verb_final,
    run_all_checks,
)


TOY_AGREEMENT_TABLE = [
    {"form": "నేను", "type": "pronoun", "person": "1", "number": "sg"},
    {"form": "ను", "type": "verb_ending", "person": "1", "number": "sg"},
    {"form": "ాడు", "type": "verb_ending", "person": "3", "number": "sg"},
]


def test_verb_final_consistent():
    tokens = [
        {"id": 1, "text": "రాము", "upos": "PROPN", "head": 2, "deprel": "nsubj"},
        {"id": 2, "text": "వచ్చాడు", "upos": "VERB", "head": 0, "deprel": "root"},
        {"id": 3, "text": ".", "upos": "PUNCT", "head": 2, "deprel": "punct"},
    ]
    res = check_verb_final(tokens)
    assert res["status"] == "consistent"
    assert "sentence-final" in res["explanation"]


def test_verb_final_not_consistent():
    # Verb initial / non-final
    tokens = [
        {"id": 1, "text": "వచ్చాడు", "upos": "VERB", "head": 0, "deprel": "root"},
        {"id": 2, "text": "రాము", "upos": "PROPN", "head": 1, "deprel": "nsubj"},
    ]
    res = check_verb_final(tokens)
    assert res["status"] == "not consistent"


def test_verb_final_not_applicable_nominal():
    # Nominal predicate
    tokens = [
        {"id": 1, "text": "అతను", "upos": "PRON", "head": 2, "deprel": "nsubj"},
        {"id": 2, "text": "మంచివాడు", "upos": "NOUN", "head": 0, "deprel": "root"},
    ]
    res = check_verb_final(tokens)
    assert res["status"] == "not applicable"


def test_det_before_noun():
    tokens_good = [
        {"id": 1, "text": "ఆ", "upos": "DET", "head": 2, "deprel": "det"},
        {"id": 2, "text": "పుస్తకం", "upos": "NOUN", "head": 0, "deprel": "root"},
    ]
    assert check_det_before_noun(tokens_good)["status"] == "consistent"

    tokens_bad = [
        {"id": 1, "text": "పుస్తకం", "upos": "NOUN", "head": 0, "deprel": "root"},
        {"id": 2, "text": "ఆ", "upos": "DET", "head": 1, "deprel": "det"},
    ]
    assert check_det_before_noun(tokens_bad)["status"] == "not consistent"

    tokens_none = [
        {"id": 1, "text": "పుస్తకం", "upos": "NOUN", "head": 0, "deprel": "root"},
    ]
    assert check_det_before_noun(tokens_none)["status"] == "not applicable"


def test_amod_before_noun():
    tokens_good = [
        {"id": 1, "text": "మంచి", "upos": "ADJ", "head": 2, "deprel": "amod"},
        {"id": 2, "text": "పుస్తకం", "upos": "NOUN", "head": 0, "deprel": "root"},
    ]
    assert check_amod_before_noun(tokens_good)["status"] == "consistent"

    tokens_bad = [
        {"id": 1, "text": "పుస్తకం", "upos": "NOUN", "head": 0, "deprel": "root"},
        {"id": 2, "text": "మంచి", "upos": "ADJ", "head": 1, "deprel": "amod"},
    ]
    assert check_amod_before_noun(tokens_bad)["status"] == "not consistent"


def test_case_after_noun():
    tokens_good = [
        {"id": 1, "text": "బల్ల", "upos": "NOUN", "head": 0, "deprel": "root"},
        {"id": 2, "text": "మీద", "upos": "ADP", "head": 1, "deprel": "case"},
    ]
    assert check_case_after_noun(tokens_good)["status"] == "consistent"

    tokens_bad = [
        {"id": 1, "text": "మీద", "upos": "ADP", "head": 2, "deprel": "case"},
        {"id": 2, "text": "బల్ల", "upos": "NOUN", "head": 0, "deprel": "root"},
    ]
    assert check_case_after_noun(tokens_bad)["status"] == "not consistent"


def test_subject_verb_agreement_pronoun_match():
    # నేను వెళ్ళాను (1sg pronoun + 1sg verb)
    tokens = [
        {"id": 1, "text": "నేను", "upos": "PRON", "head": 2, "deprel": "nsubj"},
        {"id": 2, "text": "వెళ్ళాను", "upos": "VERB", "head": 0, "deprel": "root"},
    ]
    res = check_subject_verb_agreement(tokens, agreement_rows=TOY_AGREEMENT_TABLE, known_non_verbs=set())
    assert res["status"] == "consistent"
    assert res["badge"] == "EXPERIMENTAL, UNVALIDATED"


def test_subject_verb_agreement_pronoun_mismatch():
    # నేను వెళ్ళాడు (1sg pronoun + 3sg verb)
    tokens = [
        {"id": 1, "text": "నేను", "upos": "PRON", "head": 2, "deprel": "nsubj"},
        {"id": 2, "text": "వెళ్ళాడు", "upos": "VERB", "head": 0, "deprel": "root"},
    ]
    res = check_subject_verb_agreement(tokens, agreement_rows=TOY_AGREEMENT_TABLE, known_non_verbs=set())
    assert res["status"] == "not consistent"
    assert res["badge"] == "EXPERIMENTAL, UNVALIDATED"


def test_subject_verb_agreement_abstain_on_name():
    # Proper name subject: must abstain (not in pronoun table)
    tokens = [
        {"id": 1, "text": "రాము", "upos": "PROPN", "head": 2, "deprel": "nsubj"},
        {"id": 2, "text": "వెళ్ళాడు", "upos": "VERB", "head": 0, "deprel": "root"},
    ]
    res = check_subject_verb_agreement(tokens, agreement_rows=TOY_AGREEMENT_TABLE, known_non_verbs={"రాము"})
    assert res["status"] == "not applicable"
    assert "abstains" in res["explanation"]


def test_unknown_tokens():
    tokens = [
        {"id": 1, "text": "రాము", "upos": "PROPN"},
        {"id": 2, "text": "వెళ్ళాడు", "upos": "VERB"},
    ]
    res_clean = check_unknown_tokens(tokens)
    assert res_clean["status"] == "consistent"

    res_oov = check_unknown_tokens(tokens, known_vocab={"వెళ్ళాడు"})
    assert res_oov["status"] == "not applicable"
    assert "రాము" in res_oov["explanation"]


def test_run_all_checks():
    tokens = [
        {"id": 1, "text": "రాము", "upos": "PROPN", "head": 2, "deprel": "nsubj"},
        {"id": 2, "text": "వెళ్ళాడు", "upos": "VERB", "head": 0, "deprel": "root"},
    ]
    all_res = run_all_checks(tokens, agreement_rows=TOY_AGREEMENT_TABLE)
    assert len(all_res) == 6
    check_ids = [c["check_id"] for c in all_res]
    assert "verb_final" in check_ids
    assert "det_before_noun" in check_ids
    assert "amod_before_noun" in check_ids
    assert "case_after_noun" in check_ids
    assert "subject_verb_agreement" in check_ids
    assert "unknown_tokens" in check_ids
