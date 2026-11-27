"""Tests for src/analyzer.py."""

import pytest

from src.analyzer import (
    analyze_sentence,
    convert_dependency_to_phrase_tree,
    detect_word_order,
    evaluate_pcfg_coverage,
    transliterate_to_iso,
)


def test_transliterate_to_iso():
    out = transliterate_to_iso("రాము ఇంట్లోకి వెళ్ళాడు")
    assert "rāmu" in out
    assert "veḷḷāḍu" in out


def test_detect_word_order():
    subj = {"id": 1}
    obj = {"id": 2}
    verb = {"id": 3}
    assert detect_word_order(subj, obj, verb) == "S-O-V"

    # S-V-O
    assert detect_word_order(subj, {"id": 3}, {"id": 2}) == "S-V-O"

    # S-V only
    assert detect_word_order(subj, None, verb) == "S-V"

    # None
    assert detect_word_order(None, None, None) == "N/A"


def test_convert_dependency_to_phrase_tree():
    tokens = [
        {"id": 1, "text": "రాము", "upos": "PROPN", "head": 2, "deprel": "nsubj"},
        {"id": 2, "text": "వెళ్ళాడు", "upos": "VERB", "head": 0, "deprel": "root"},
        {"id": 3, "text": ".", "upos": "PUNCT", "head": 2, "deprel": "punct"},
    ]
    tree_tuple, bracket_words, bracket_pos = convert_dependency_to_phrase_tree(tokens)
    assert tree_tuple is not None
    assert tree_tuple[0] == "S"
    assert "రాము" in bracket_words
    assert "propn" in bracket_pos.lower()


def test_evaluate_pcfg_coverage_uncovered():
    # If parser is None
    res = evaluate_pcfg_coverage([], None)
    assert res["covered"] is False
    assert "not loaded" in res["message"]


@pytest.mark.slow
def test_live_pipeline_analysis():
    # Runs the actual Stanza pipeline (marked slow)
    res = analyze_sentence("రాము ఇంట్లోకి వెళ్ళాడు")
    assert res["token_count"] == 3
    assert res["main_verb"] == "వెళ్ళాడు"
    assert res["subject"] == "రాము"
    assert res["word_order"] == "S-V"
    assert len(res["checks"]) == 6
