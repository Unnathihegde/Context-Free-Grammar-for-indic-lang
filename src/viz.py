"""Visualization helpers for dependency graphs, phrase-structure trees, and POS badges.

Uses spaCy displaCy for dependency arcs and svgling for phrase-structure trees,
with CSS styling for 'Noto Sans Telugu' font rendering.
"""

from typing import Any, Dict, List, Tuple
import re
from spacy import displacy
import svgling

from src.glossary import get_upos_color, get_upos_name


TELUGU_FONT_FAMILY = "'Noto Sans Telugu', 'Gautami', 'Mandali', sans-serif"


def format_words_and_arcs_for_displacy(tokens: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Convert tokens into spaCy manual displaCy format."""
    words = []
    arcs = []

    for t in tokens:
        words.append({
            "text": t.get("text", ""),
            "tag": t.get("upos", ""),
        })

    for t in tokens:
        head_id = t.get("head", 0)
        tok_id = t.get("id", 0)
        deprel = t.get("deprel", "")

        # Skip root (head == 0) and invalid heads
        if head_id == 0 or head_id == tok_id:
            continue

        # In displaCy, start is the smaller index, end is the larger (0-indexed)
        # dir indicates direction of arrow: "left" means arrow points from right to left;
        # "right" means arrow points from left to right.
        tok_idx = tok_id - 1
        head_idx = head_id - 1

        if tok_idx < head_idx:
            # dependent is to the left of head: head -> dependent
            start = tok_idx
            end = head_idx
            direction = "left"  # arrow points to dependent (left)
        else:
            # dependent is to the right of head: head -> dependent
            start = head_idx
            end = tok_idx
            direction = "right"  # arrow points to dependent (right)

        arcs.append({
            "start": start,
            "end": end,
            "label": deprel,
            "dir": direction,
        })

    return {"words": words, "arcs": arcs}


def render_dependency_svg(words_and_arcs: Dict[str, Any]) -> str:
    """Render a horizontal dependency arc SVG using displaCy manual mode."""
    options = {
        "compact": False,
        "bg": "#FFFFFF",
        "color": "#1E293B",
        "distance": 110,
        "word_spacing": 30,
        "arrow_stroke": 2,
        "arrow_width": 7,
    }
    raw_svg = displacy.render(words_and_arcs, style="dep", manual=True, options=options)

    # Inject Noto Sans Telugu font styling into SVG text elements
    styled_svg = re.sub(
        r'<text\s+([^>]*?)font-family="[^"]*"',
        rf'<text \1font-family="{TELUGU_FONT_FAMILY}"',
        raw_svg,
    )
    if 'font-family="' not in raw_svg and "<text" in styled_svg:
        styled_svg = styled_svg.replace("<text", f'<text font-family="{TELUGU_FONT_FAMILY}"')

    # Wrap in horizontal scrollable container
    wrapped_html = f"""
    <div style="overflow-x: auto; width: 100%; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; background: #FFFFFF;">
        {styled_svg}
    </div>
    """
    return wrapped_html


def render_tree_svg(tree_tuple: Any) -> str:
    """Render a phrase-structure tree as SVG using svgling."""
    if tree_tuple is None:
        return "<p style='color: #64748B;'>No phrase-structure tree available.</p>"

    try:
        drawn = svgling.draw_tree(tree_tuple)
        if hasattr(drawn, "_repr_svg_"):
            raw_svg = drawn._repr_svg_()
        elif hasattr(drawn, "get_svg"):
            raw_svg = drawn.get_svg().tostring()
        else:
            raw_svg = str(drawn)

        # Inject font style
        font_style = f'<style>text {{ font-family: {TELUGU_FONT_FAMILY}; }}</style>'
        if "<svg" in raw_svg:
            raw_svg = raw_svg.replace(">", f">\n{font_style}", 1)

        wrapped_html = f"""
        <div style="overflow-x: auto; width: 100%; border: 1px solid #E2E8F0; border-radius: 8px; padding: 16px; background: #FFFFFF; text-align: center;">
            {raw_svg}
        </div>
        """
        return wrapped_html
    except Exception as e:
        return f"<p style='color: #DC2626;'>Could not render tree: {e}</p>"


def render_pos_badge_html(upos: str) -> str:
    """Generate an inline HTML badge for a UPOS tag."""
    bg_color, text_color = get_upos_color(upos)
    name = get_upos_name(upos)
    return (
        f'<span title="{name}" style="'
        f'background-color: {bg_color}; '
        f'color: {text_color}; '
        f'border: 1px solid {text_color}33; '
        f'padding: 2px 7px; '
        f'border-radius: 4px; '
        f'font-size: 0.82rem; '
        f'font-weight: 600; '
        f'font-family: monospace; display: inline-block;">'
        f'{upos}'
        f'</span>'
    )


def build_pos_distribution_chart(pos_counts: Dict[str, int]) -> Any:
    """Build an Altair bar chart for POS tag frequencies."""
    import altair as alt
    import pandas as pd

    data = []
    for pos, count in sorted(pos_counts.items(), key=lambda x: -x[1]):
        bg, text = get_upos_color(pos)
        data.append({
            "POS": pos,
            "Count": count,
            "Name": get_upos_name(pos),
            "Color": text,
        })
    df = pd.DataFrame(data)

    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("POS:N", sort="-y", title="Universal POS Tag"),
            y=alt.Y("Count:Q", title="Frequency", axis=alt.Axis(tickMinStep=1)),
            color=alt.Color("Color:N", scale=None, legend=None),
            tooltip=["POS", "Name", "Count"],
        )
        .properties(
            title="Part-of-Speech Distribution",
            height=200,
        )
    )
    return chart
