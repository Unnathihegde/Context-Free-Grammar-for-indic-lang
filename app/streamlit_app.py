"""Telugu Grammar Analyzer - Clean, Visual Streamlit Demo.

Automatic grammatical analysis for Telugu sentences using Universal Dependencies
(UD Telugu-MTG via Stanza), ISO 15919 transliteration, phrase-structure trees,
and syntactic pattern checks.
"""

from typing import Any, Dict, List, Optional, Tuple
import os
import sys
import unicodedata

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agreement import clean_for_matching, ending_forms, get_known_non_verbs, load_agreement_table
from src.analyzer import (
    ModelNotInstalledError,
    analyze_sentence,
    load_pcfg_parser,
    load_stanza_pipeline,
)
from src.grammar_learn import read_conllu
from src.viz import (
    build_pos_distribution_chart,
    format_words_and_arcs_for_displacy,
    render_dependency_svg,
    render_pos_badge_html,
    render_tree_svg,
)

# Page configuration
st.set_page_config(
    layout="wide",
    page_title="Telugu Grammar Analyzer",
    page_icon="📖",
)

ZERO_WIDTH_CHARS = str.maketrans("", "", "\u200b\u200c\u200d\ufeff")

# CSS Styling: Google Fonts Noto Sans Telugu + fallback to Nirmala UI and Gautami
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Telugu:wght@400;600;700&display=swap');

html, body, [class*="css"], [class*="st-"] {
    font-family: 'Noto Sans Telugu', 'Nirmala UI', 'Gautami', -apple-system, BlinkMacSystemFont, sans-serif;
}

.telugu-font {
    font-family: 'Noto Sans Telugu', 'Nirmala UI', 'Gautami', sans-serif !important;
}

.metric-card {
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 12px 16px;
    text-align: center;
}

.metric-label {
    font-size: 0.8rem;
    font-weight: 600;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.metric-val {
    font-size: 1.25rem;
    font-weight: 700;
    color: #0F172A;
    margin-top: 4px;
}

.summary-card {
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
    border-left: 4px solid #16A34A;
    border-radius: 6px;
    padding: 12px 18px;
    margin: 12px 0 20px 0;
    color: #166534;
    font-size: 0.95rem;
}

.unvalidated-badge {
    background-color: #FEF3C7;
    color: #92400E;
    border: 1px solid #FCD34D;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 4px;
    display: inline-block;
    text-transform: uppercase;
}

.app-footer {
    margin-top: 48px;
    padding-top: 16px;
    border-top: 1px solid #E2E8F0;
    font-size: 0.85rem;
    color: #64748B;
    text-align: center;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_resource(show_spinner="Loading Stanza Telugu dependency model (UD Telugu-MTG)...")
def get_cached_pipeline():
    """Load and cache the Stanza Telugu pipeline."""
    try:
        return load_stanza_pipeline()
    except ModelNotInstalledError as e:
        return e
    except Exception as e:
        return e


@st.cache_resource(show_spinner="Loading PCFG grammar rules...")
def get_cached_pcfg():
    """Load and cache the PCFG grammar rules and Viterbi parser."""
    return load_pcfg_parser()


@st.cache_data
def get_example_sentences() -> List[str]:
    """Load sample sentences dynamically from the dev treebank."""
    dev_path = "data/te_dev.conllu"
    if os.path.exists(dev_path):
        try:
            sents = read_conllu(dev_path)
            samples = []
            for s in sents:
                text = " ".join(t["word"] for t in s)
                if 3 <= len(s) <= 10:
                    samples.append(text)
                if len(samples) >= 15:
                    break
            return samples
        except Exception:
            pass
    return [
        "మనం ఎందుకు అన్నం తింటాం ?",
        "నువ్వు పని చెయ్యాలి .",
        "రాము నేను రేపు వెళ్తాను అని కమలతో చెప్పేడు .",
    ]


@st.cache_data
def load_treebank_lookup() -> Dict[str, List[Dict[str, Any]]]:
    """Load all treebank sentences mapped by normalized text for gold comparison."""
    lookup: Dict[str, List[Dict[str, Any]]] = {}
    for fn in ["data/te_train.conllu", "data/te_dev.conllu", "data/te_test.conllu"]:
        if os.path.exists(fn):
            try:
                for s in read_conllu(fn):
                    norm_text = unicodedata.normalize("NFC", " ".join(t["word"] for t in s)).strip()
                    if norm_text not in lookup:
                        lookup[norm_text] = s
            except Exception:
                pass
    return lookup


def clean_input_text(raw_text: str) -> Tuple[str, bool]:
    """Apply NFC normalization and strip hidden zero-width characters."""
    nfc_text = unicodedata.normalize("NFC", raw_text)
    cleaned = nfc_text.translate(ZERO_WIDTH_CHARS).strip()
    had_hidden = (nfc_text != cleaned)
    return cleaned, had_hidden


def compute_possible_suffixes(
    tokens: List[Dict[str, Any]], agreement_table: List[Dict[str, str]], known_non_verbs: set
) -> List[str]:
    """Compute possible suffix column: only fires on VERB tokens with valid agreement endings."""
    verb_ending_rows = [r for r in agreement_table if r.get("type") == "verb_ending"]
    suffixes = []
    for t in tokens:
        if t.get("upos") == "VERB":
            matched = ending_forms(t.get("text", ""), verb_ending_rows, known_non_verbs)
            if matched:
                suffixes.append(f"-{matched[0]}")
            else:
                suffixes.append("-")
        else:
            suffixes.append("-")
    return suffixes


# ==============================================================================
# MAIN APPLICATION
# ==============================================================================

st.title("📖 Telugu Grammar Analyzer")
st.caption("Automatic grammatical analysis with dependency and phrase-structure views")

# Model status check
nlp_or_err = get_cached_pipeline()
if isinstance(nlp_or_err, Exception):
    st.error(
        f"**Model Error**: Stanza Telugu model could not be loaded.\n\n"
        f"Please run this command in your PowerShell terminal to download the model:\n\n"
        f"```powershell\npython -c \"import stanza; stanza.download('te')\"\n```\n\n"
        f"*Details: {nlp_or_err}*"
    )
    st.stop()
else:
    nlp = nlp_or_err

pcfg_tuple = get_cached_pcfg()
parser = pcfg_tuple[1] if pcfg_tuple else None

# Status line
st.success("Stanza te pipeline loaded (processors: tokenize, pos, lemma [identity], depparse)", icon="✅")

# Accuracy card from results/stanza_eval.csv
eval_csv_path = "results/stanza_eval.csv"
if os.path.exists(eval_csv_path):
    try:
        df_eval = pd.read_csv(eval_csv_path)
        test_row = df_eval[df_eval["split"] == "test"]
        if not test_row.empty:
            r = test_row.iloc[0]
            col_acc1, col_acc2, col_acc3 = st.columns(3)
            with col_acc1:
                st.metric("Test UPOS Accuracy", f"{float(r['upos_acc']) * 100:.1f}%")
            with col_acc2:
                st.metric("Test UAS (Unlabeled)", f"{float(r['uas']) * 100:.1f}%")
            with col_acc3:
                st.metric("Test LAS (Labeled)", f"{float(r['las']) * 100:.1f}%")
            st.caption(
                "Measured on held-out treebank sentences with gold tokenization. "
                "Accuracy on other Telugu text is not measured and is likely lower."
            )
    except Exception:
        pass
else:
    st.info("Run `python scripts/eval_stanza.py` to populate held-out treebank reliability metrics.")

st.markdown("---")

# Session state initialization
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "cleaned_text" not in st.session_state:
    st.session_state.cleaned_text = ""
if "hidden_removed" not in st.session_state:
    st.session_state.hidden_removed = False

# Example selector & Input Form
examples = ["Select an example sentence from the treebank..."] + get_example_sentences()
selected_example = st.selectbox(
    "Choose an example sentence or type below:",
    examples,
    index=0,
)

default_text = ""
if selected_example != examples[0]:
    default_text = selected_example

col_input, col_btn = st.columns([5, 1])
with col_input:
    user_input = st.text_input(
        "Enter a Telugu sentence:",
        value=default_text,
        placeholder="e.g. రాము ఇంట్లోకి వెళ్ళాడు",
        key="sentence_input",
    )
with col_btn:
    st.write("")  # align with input box
    analyze_btn = st.button("Analyze", type="primary", use_container_width=True)

# Trigger analysis on button click or Enter key
should_analyze = (analyze_btn or (user_input and user_input != st.session_state.cleaned_text))

if should_analyze:
    if not user_input.strip():
        st.warning("Please type a Telugu sentence or select an example from the dropdown.")
    else:
        cleaned_text, had_hidden = clean_input_text(user_input)
        st.session_state.cleaned_text = cleaned_text
        st.session_state.hidden_removed = had_hidden

        try:
            with st.spinner("Analyzing sentence..."):
                res = analyze_sentence(cleaned_text, nlp=nlp, parser=parser)
                st.session_state.analysis_result = res
        except Exception as exc:
            st.error(
                "An unexpected error occurred during automatic analysis. "
                "Please verify that the input is a valid Telugu sentence.\n\n"
                f"*Notice: {exc}*"
            )
            st.session_state.analysis_result = None

# If hidden characters were cleaned, display notice
if st.session_state.hidden_removed:
    st.info("ℹ️ Hidden characters (such as zero-width spaces or joiners) were removed before analysis.")

# Render analysis results
res = st.session_state.analysis_result

if res and "error" not in res:
    tokens = res["tokens"]

    # 1. Row of constituent summary cards
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">Tokens</div>'
            f'<div class="metric-val">{res["token_count"]}</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        subj_str = res["subject"] if res["subject"] else '<span style="color:#94A3B8;">not found</span>'
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">Subject (nsubj)</div>'
            f'<div class="metric-val telugu-font">{subj_str}</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        obj_str = res["object"] if res["object"] else '<span style="color:#94A3B8;">not found</span>'
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">Object (obj)</div>'
            f'<div class="metric-val telugu-font">{obj_str}</div></div>',
            unsafe_allow_html=True,
        )
    with c4:
        verb_str = res["main_verb"] if res["main_verb"] else '<span style="color:#94A3B8;">not found</span>'
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">Main Verb (root)</div>'
            f'<div class="metric-val telugu-font">{verb_str}</div></div>',
            unsafe_allow_html=True,
        )
    with c5:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">Word Order</div>'
            f'<div class="metric-val">{res["word_order"]}</div></div>',
            unsafe_allow_html=True,
        )

    # 2. Template-based Plain-English Summary Card (No LLM)
    subj_disp = res["subject"] or "not found"
    obj_disp = res["object"] or "not found"
    verb_disp = res["main_verb"] or "not found"
    order_disp = res["word_order"] if res["word_order"] != "N/A" else "unidentified"

    summary_text = (
        f"**Automatic summary**: Subject: **{subj_disp}**. Object: **{obj_disp}**. "
        f"Main verb: **{verb_disp}**. Word order: **{order_disp}**."
    )
    st.markdown(f'<div class="summary-card">{summary_text}</div>', unsafe_allow_html=True)

    # 3. Six Dedicated Tabs
    tab_words, tab_dep, tab_cfg, tab_checks, tab_compare, tab_rel = st.tabs([
        "1. Word analysis",
        "2. Dependency chart",
        "3. Phrase-structure tree (CFG)",
        "4. Grammar checks",
        "5. Compare with treebank",
        "6. Reliability & limits",
    ])

    # --------------------------------------------------------------------------
    # TAB 1: Word Analysis
    # --------------------------------------------------------------------------
    with tab_words:
        st.subheader("Token-by-Token Morphosyntactic Breakdown")
        st.caption("Each word is assigned a Universal POS tag, dependency head, and syntactic relation.")

        # Compute possible suffix column (only fires on VERB)
        agreement_table = load_agreement_table()
        known_non_verbs = get_known_non_verbs()
        suffixes = compute_possible_suffixes(tokens, agreement_table, known_non_verbs)

        table_rows = []
        for i, t in enumerate(tokens):
            table_rows.append({
                "ID": t["id"],
                "Word": t["text"],
                "Transliteration (automatic)": t["translit"],
                "POS Tag": t["upos"],
                "POS Category": t["upos_name"],
                "Head Word": t["head_text"],
                "Relation": t["deprel"],
                "Relation Meaning": t["deprel_gloss"],
                "Possible suffix [EXPERIMENTAL]": suffixes[i],
            })
        df_tokens = pd.DataFrame(table_rows)

        st.dataframe(
            df_tokens,
            column_config={
                "ID": st.column_config.NumberColumn("ID", width="small"),
                "Word": st.column_config.TextColumn("Word"),
                "Transliteration (automatic)": st.column_config.TextColumn("Transliteration (ISO 15919)"),
                "POS Tag": st.column_config.TextColumn("UPOS"),
                "POS Category": st.column_config.TextColumn("Category"),
                "Head Word": st.column_config.TextColumn("Head"),
                "Relation": st.column_config.TextColumn("Relation"),
                "Relation Meaning": st.column_config.TextColumn("UD Description"),
                "Possible suffix [EXPERIMENTAL]": st.column_config.TextColumn("Possible suffix (unvalidated)"),
            },
            hide_index=True,
            use_container_width=True,
        )

        st.caption("⚠️ 'Possible suffix' is an experimental heuristic matching the unvalidated verb-ending table.")

        # POS Distribution bar chart
        st.markdown("#### Part-of-Speech Tag Frequencies")
        chart = build_pos_distribution_chart(res["pos_counts"])
        st.altair_chart(chart, use_container_width=True)

    # --------------------------------------------------------------------------
    # TAB 2: Dependency Chart
    # --------------------------------------------------------------------------
    with tab_dep:
        st.subheader("Syntactic Dependency Graph")
        st.caption("Directed arcs point from head words to their syntactic dependents (UD scheme).")

        words_and_arcs = format_words_and_arcs_for_displacy(tokens)
        dep_svg_html = render_dependency_svg(words_and_arcs)
        components.html(dep_svg_html, height=260, scrolling=True)

        with st.expander("📖 Dependency Relations Legend"):
            st.markdown(
                """
                - **root**: The main predicate / anchor of the sentence.
                - **nsubj**: Nominal subject of the verb or predicate.
                - **obj / iobj**: Direct / indirect complement of the verb.
                - **obl**: Oblique circumstantial argument (location, instrument, etc.).
                - **amod**: Adjectival modifier of a noun.
                - **det**: Determiner modifying a noun.
                - **case**: Postposition or case particle attached to a nominal.
                - **punct**: Punctuation mark.
                """
            )

    # --------------------------------------------------------------------------
    # TAB 3: Phrase-Structure Tree (CFG View)
    # --------------------------------------------------------------------------
    with tab_cfg:
        st.subheader("Phrase-Structure Hierarchy")
        st.info(
            "A Context-Free Grammar (CFG) tree represents sentence structure as nested hierarchical "
            "phrases (e.g. Noun Phrases and Verb Phrases) grouping words into constituents."
        )

        if res["tree_tuple"]:
            tree_svg_html = render_tree_svg(res["tree_tuple"])
            components.html(tree_svg_html, height=320, scrolling=True)

            with st.expander("View Bracketed Notation"):
                st.code(res["bracket_words"], language="text")

            st.markdown("#### Learned PCFG Coverage")
            pcfg_info = res["pcfg_eval"]
            if pcfg_info["covered"]:
                st.success(
                    f"**Parseable by learned grammar**: Viterbi parse probability = `{pcfg_info['probability']:.6e}`"
                )
                with st.expander("CFG Productions Used in Best Parse"):
                    for rule in pcfg_info["rules"]:
                        st.markdown(f"- `{rule}`")
            else:
                st.info(pcfg_info["message"])
        else:
            st.warning("Could not derive a projective phrase-structure tree for this sentence.")

    # --------------------------------------------------------------------------
    # TAB 4: Grammar Pattern Checks
    # --------------------------------------------------------------------------
    with tab_checks:
        st.subheader("Syntactic Pattern Consistency Checks")
        st.markdown(
            "> **Linguistic Note**: *These are pattern checks learned from a small treebank. "
            "They are not a full grammar checker, and a sentence that is not consistent with a "
            "pattern is not necessarily ungrammatical (Telugu word order is flexible).*"
        )

        checks_rows = []
        for chk in res["checks"]:
            status = chk["status"]
            if status == "consistent":
                status_badge = "✅ Consistent"
            elif status == "not consistent":
                status_badge = "⚠️ Not consistent"
            else:
                status_badge = "➖ Not applicable"

            name_disp = chk["name"]
            if chk.get("badge"):
                name_disp += f" ({chk['badge']})"

            checks_rows.append({
                "Pattern Check": name_disp,
                "Status": status_badge,
                "Linguistic Explanation": chk["explanation"],
            })

        df_checks = pd.DataFrame(checks_rows)
        st.dataframe(
            df_checks,
            column_config={
                "Pattern Check": st.column_config.TextColumn("Check"),
                "Status": st.column_config.TextColumn("Status", width="medium"),
                "Linguistic Explanation": st.column_config.TextColumn("Explanation"),
            },
            hide_index=True,
            use_container_width=True,
        )

    # --------------------------------------------------------------------------
    # TAB 5: Compare with Treebank Gold Annotations
    # --------------------------------------------------------------------------
    with tab_compare:
        st.subheader("Comparison with Gold Treebank Annotations")
        treebank_lookup = load_treebank_lookup()
        norm_input = unicodedata.normalize("NFC", cleaned_text).strip()

        if norm_input in treebank_lookup:
            gold_sent = treebank_lookup[norm_input]
            st.success("✨ Exact match found in the Universal Dependencies Telugu treebank!")

            gold_rows = []
            upos_matches = 0
            head_matches = 0
            las_matches = 0

            for i, gold_tok in enumerate(gold_sent):
                pred_tok = tokens[i] if i < len(tokens) else {}
                pred_pos = pred_tok.get("upos", "-")
                pred_head = pred_tok.get("head", -1)
                pred_rel = pred_tok.get("deprel", "-")

                match_pos = (pred_pos == gold_tok["pos"])
                match_head = (pred_head == gold_tok["head"])
                match_las = match_pos and match_head and (pred_rel == gold_tok["rel"])

                if match_pos:
                    upos_matches += 1
                if match_head:
                    head_matches += 1
                if match_las:
                    las_matches += 1

                gold_rows.append({
                    "ID": gold_tok["id"],
                    "Word": gold_tok["word"],
                    "Gold UPOS": gold_tok["pos"],
                    "Predicted UPOS": f"{pred_pos} {'✓' if match_pos else '✗'}",
                    "Gold Head": gold_tok["head"],
                    "Predicted Head": f"{pred_head} {'✓' if match_head else '✗'}",
                    "Gold Relation": gold_tok["rel"],
                    "Predicted Relation": f"{pred_rel} {'✓' if pred_rel == gold_tok['rel'] else '✗'}",
                })

            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.metric("Sentence UPOS Accuracy", f"{upos_matches}/{len(gold_sent)}")
            with col_m2:
                st.metric("Sentence UAS", f"{head_matches}/{len(gold_sent)}")
            with col_m3:
                st.metric("Sentence LAS", f"{las_matches}/{len(gold_sent)}")

            st.dataframe(pd.DataFrame(gold_rows), hide_index=True, use_container_width=True)
        else:
            st.info(
                "Available for treebank sentences only. Select an example from the dropdown "
                "above or type a treebank sentence to compare automatic predictions against gold annotations."
            )

    # --------------------------------------------------------------------------
    # TAB 6: Reliability & Limits
    # --------------------------------------------------------------------------
    with tab_rel:
        st.subheader("Model Reliability & Empirical Findings")
        st.markdown(
            """
            This section reports honest evaluation numbers measured on held-out test splits.
            Grammar and parser outputs are automatic statistical estimates and should not be
            assumed to be free of errors.
            """
        )

        st.markdown("#### 1. Stanza Parser Accuracy (UD Telugu-MTG Test Split)")
        if os.path.exists(eval_csv_path):
            st.dataframe(pd.read_csv(eval_csv_path), hide_index=True, use_container_width=True)
        else:
            st.info("Run `python scripts/eval_stanza.py` to generate parser evaluation metrics.")

        details_csv_path = "results/stanza_eval_details.csv"
        if os.path.exists(details_csv_path):
            st.markdown("#### 2. Detailed Accuracy by POS Tag and Relation")
            df_det = pd.read_csv(details_csv_path)
            tab_det_tags, tab_det_rels = st.tabs(["Accuracy by UPOS Tag", "LAS by Dependency Relation"])
            with tab_det_tags:
                df_tags = df_det[(df_det["category"] == "UPOS Tag") & (df_det["split"] == "test")]
                st.dataframe(
                    df_tags[["item", "frequency", "correct", "accuracy"]],
                    column_config={
                        "item": "UPOS Tag",
                        "frequency": "Frequency in Test",
                        "correct": "Correct Predictions",
                        "accuracy": st.column_config.NumberColumn("Accuracy", format="%.2f"),
                    },
                    hide_index=True,
                    use_container_width=True,
                )
            with tab_det_rels:
                df_rels = df_det[(df_det["category"] == "Dependency Relation") & (df_det["split"] == "test")]
                st.dataframe(
                    df_rels[["item", "frequency", "correct", "accuracy"]],
                    column_config={
                        "item": "Relation",
                        "frequency": "Frequency in Test",
                        "correct": "Correct LAS",
                        "accuracy": st.column_config.NumberColumn("LAS", format="%.2f"),
                    },
                    hide_index=True,
                    use_container_width=True,
                )

        st.markdown("#### 3. Word-Order Hypothesis Testing (PCFG vs POS-Bigram Baseline)")
        wo_path = "results/wordorder_results.csv"
        if os.path.exists(wo_path):
            df_wo = pd.read_csv(wo_path)
            st.dataframe(df_wo, hide_index=True, use_container_width=True)
            st.warning(
                "**Key Finding**: The learned POS-level PCFG did **not** outperform a simple POS-bigram "
                "baseline overall on word-order pairs (PCFG accuracy 0.944 vs Bigram accuracy 0.967; "
                "paired bootstrap p <= 0.002). The PCFG advantage on case_before was not statistically "
                "significant (p = 0.058). A context-free grammar does not improve discrimination over the baseline."
            )

        st.markdown("#### 4. Subject-Verb Agreement Validation Status")
        st.markdown(
            '<span class="unvalidated-badge">EXPERIMENTAL / UNVALIDATED</span> '
            "The subject-verb agreement table was inducted heuristically and has not yet completed "
            "double-annotated native speaker validation. Results are shown for demonstration only.",
            unsafe_allow_html=True,
        )

# Footer
st.markdown(
    '<div class="app-footer">'
    "Automatic analysis by Stanza (UD Telugu-MTG). Pattern checks are learned from a small treebank. "
    "Not a full grammar checker."
    "</div>",
    unsafe_allow_html=True,
)
