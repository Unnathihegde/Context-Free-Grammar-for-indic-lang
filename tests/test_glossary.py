"""Tests for src/glossary.py."""

from src.glossary import DEPREL_GLOSSES, UPOS_NAMES, get_deprel_gloss, get_upos_color, get_upos_name


def test_get_upos_name():
    assert get_upos_name("VERB") == "Verb"
    assert get_upos_name("NOUN") == "Noun"
    assert get_upos_name("PROPN") == "Proper Noun"
    assert get_upos_name("UNKNOWN_TAG") == "UNKNOWN_TAG"


def test_get_deprel_gloss():
    assert get_deprel_gloss("nsubj") == "Nominal subject"
    assert get_deprel_gloss("root") == "Root predicate of sentence"
    # Subtyped relations fall back to main relation if not explicitly mapped
    assert "Oblique" in get_deprel_gloss("obl:arg")
    assert "Custom" in get_deprel_gloss("custom_rel") or "custom_rel" in get_deprel_gloss("custom_rel")


def test_get_upos_color():
    bg, text = get_upos_color("VERB")
    assert bg.startswith("#") and text.startswith("#")
    assert len(bg) == 7 and len(text) == 7
    # Unknown tag returns fallback color
    bg_unk, text_unk = get_upos_color("FOOBAR")
    assert bg_unk.startswith("#")
