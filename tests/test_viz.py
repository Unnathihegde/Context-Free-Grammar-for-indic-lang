"""Tests for visualization functions in src/viz.py."""

from src.viz import (
    build_pos_distribution_chart,
    format_words_and_arcs_for_displacy,
    render_dependency_svg,
    render_pos_badge_html,
    render_tree_svg,
)


def test_format_words_and_arcs_for_displacy():
    tokens = [
        {"id": 1, "text": "రాము", "upos": "PROPN", "head": 2, "deprel": "nsubj"},
        {"id": 2, "text": "వెళ్ళాడు", "upos": "VERB", "head": 0, "deprel": "root"},
    ]
    formatted = format_words_and_arcs_for_displacy(tokens)
    assert len(formatted["words"]) == 2
    assert len(formatted["arcs"]) == 1
    arc = formatted["arcs"][0]
    assert arc["start"] == 0
    assert arc["end"] == 1
    assert arc["label"] == "nsubj"
    assert arc["dir"] == "left"


def test_render_dependency_svg():
    tokens = [
        {"id": 1, "text": "రాము", "upos": "PROPN", "head": 2, "deprel": "nsubj"},
        {"id": 2, "text": "వెళ్ళాడు", "upos": "VERB", "head": 0, "deprel": "root"},
    ]
    data = format_words_and_arcs_for_displacy(tokens)
    html = render_dependency_svg(data)
    assert "<svg" in html
    assert "Noto Sans Telugu" in html


def test_render_tree_svg():
    tree_tuple = ("S", ("VERB_P", ("PROPN", "రాము"), ("VERB", "వెళ్ళాడు")))
    html = render_tree_svg(tree_tuple)
    assert "<svg" in html
    assert "Noto Sans Telugu" in html

    # Empty / None tree handling
    none_html = render_tree_svg(None)
    assert "No phrase-structure tree available" in none_html


def test_render_pos_badge_html():
    badge = render_pos_badge_html("VERB")
    assert "<span" in badge
    assert "VERB" in badge
    assert "background-color:" in badge


def test_build_pos_distribution_chart():
    counts = {"NOUN": 3, "VERB": 1, "PROPN": 1}
    chart = build_pos_distribution_chart(counts)
    assert chart is not None
    # Check that Altair chart compiles to dictionary
    spec = chart.to_dict()
    assert spec["mark"]["type"] == "bar"
