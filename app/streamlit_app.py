"""Interactive inspection UI for the Telugu PCFG and agreement scorer."""

import sys
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st
from nltk.parse import ViterbiParser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agreement import TABLE_PATH, ending_forms, load_agreement_table  # noqa: E402
from grammar_learn import induce, load_all, parse_prob, pos_seq, prepare  # noqa: E402
from hybrid import agreement_check, hybrid_score  # noqa: E402
from ngram_lm import train_from_corpus  # noqa: E402


RAW_CORPUS = ROOT / "data" / "raw" / "telugu_corpus.txt"
RESULTS_DIR = ROOT / "results"


@st.cache_resource(show_spinner="Learning the PCFG from the treebank…")
def pcfg_backend():
    trees, skipped = prepare(load_all())
    grammar = induce(trees)
    return trees, ViterbiParser(grammar), skipped


@st.cache_resource(show_spinner="Loading the word language model…")
def lm_backend():
    if not RAW_CORPUS.is_file():
        return None, (
            "Word LM unavailable: add data/raw/telugu_corpus.txt (one sentence per line) "
            "and reload."
        )
    try:
        return train_from_corpus(RAW_CORPUS), None
    except ValueError as error:
        return None, f"Word LM unavailable: {error}"


def sentence_label(index, trees):
    words = " ".join(token["word"] for token in trees[index][0])
    return f"{index + 1}: {words[:120]}"


def get_token_statuses(sentence, table_rows, lm=None):
    """Analyze each word for agreement-table and language-model recognition.

    Unknown words are labeled UNKNOWN, reflecting standard vocabulary and rule
    coverage limits, not operational errors.
    """
    pronouns = {
        unicodedata.normalize("NFC", row["form"])
        for row in table_rows
        if row.get("type") == "pronoun"
    }
    ending_rows = [row for row in table_rows if row.get("type") == "verb_ending"]

    tokens = unicodedata.normalize("NFC", sentence).split()
    records = []
    for token in tokens:
        if token in pronouns:
            agr_status = "KNOWN"
            agr_detail = "pronoun"
        else:
            forms = ending_forms(token, ending_rows)
            if forms:
                agr_status = "KNOWN"
                agr_detail = f"verb ending (-{forms[0]})"
            else:
                agr_status = "UNKNOWN"
                agr_detail = "-"

        record = {
            "Token": token,
            "Agreement Table": agr_status,
            "Agreement Detail": agr_detail,
        }
        if lm is not None:
            record["LM Vocabulary"] = (
                "IN VOCABULARY" if token in lm.vocabulary else "UNKNOWN"
            )
        records.append(record)
    return records


st.set_page_config(page_title="Telugu CFG demo", layout="wide")
st.title("Telugu PCFG and agreement demo")
st.caption("Unknown words and unsupported structures are normal model limitations, not errors.")

st.header("1. Treebank PCFG")
trees, parser, skipped = pcfg_backend()
sentence_index = st.selectbox(
    "Choose a usable treebank sentence",
    range(len(trees)),
    format_func=lambda index: sentence_label(index, trees),
)
sentence = trees[sentence_index][0]
sequence = pos_seq(sentence)
st.write("POS sequence:", " ".join(sequence))
try:
    parsed_tree = next(parser.parse(sequence), None)
except ValueError:
    parsed_tree = None
if parsed_tree is None:
    st.info("The learned PCFG does not support this POS sequence. This is not an error.")
else:
    st.code(parsed_tree.pformat(margin=100), language=None)
    st.write(f"PCFG probability: `{parse_prob(parser, sequence):.8g}`")

st.header("2. Sentence scoring")
user_sentence = st.text_input("Enter a Telugu sentence")
table_rows = load_agreement_table(TABLE_PATH)
lm, lm_message = lm_backend()
if user_sentence.strip():
    token_records = get_token_statuses(user_sentence, table_rows, lm=lm)
    st.subheader("Token Analysis")
    st.caption("Words not recognized in tables are labeled UNKNOWN, not errors.")
    st.dataframe(pd.DataFrame(token_records), hide_index=True)

    check = agreement_check(user_sentence, table_rows)
    if check["status"] == "abstained":
        st.info("Agreement check: abstained — no supported pronoun–verb-ending combination was found.")
    elif check["status"] == "matched":
        st.success("Agreement check: matched (0 table-based person mismatches).")
    else:
        st.warning(f"Agreement check: violated ({check['violations']} table-based person mismatch(es)).")

    if check["rule_rows"]:
        unique_rows = {tuple(sorted(row.items())): row for row in check["rule_rows"]}
        st.write("Agreement-table rows used:")
        st.dataframe(pd.DataFrame(unique_rows.values()), hide_index=True)

    if lm is None:
        st.info(lm_message)
        st.info("LM score and hybrid score are unavailable until the real corpus is supplied.")
    else:
        b1_score = lm.normalized_score(user_sentence)
        lambda_value = st.number_input("Hybrid λ", min_value=0.0, value=1.0, step=0.1)
        h_score = hybrid_score(b1_score, check["violations"], lambda_value)
        left, right = st.columns(2)
        left.metric("B1 normalized LM score", f"{b1_score:.6f}")
        right.metric("Hybrid score", f"{h_score:.6f}")
        if check["violations"] is None:
            st.caption("G abstained, so the hybrid score equals B1 exactly.")

st.header("3. Generated results")
result_files = sorted(RESULTS_DIR.glob("*.csv"))
if not result_files:
    st.info("Run the scripts first; no result CSV files exist yet.")
else:
    for result_file in result_files:
        st.subheader(result_file.name)
        result_frame = pd.read_csv(result_file)
        if result_file.name in {"agreement_results.csv", "datasize_curve.csv"}:
            if "reportable" not in result_frame.columns:
                st.warning("This result file has no reportability field; do not treat it as reportable.")
            else:
                false_rows = result_frame[
                    result_frame["reportable"].astype(str).str.lower() == "false"
                ]
                if not false_rows.empty:
                    reasons = []
                    if "reportability_reason" in false_rows.columns:
                        reasons = sorted(set(false_rows["reportability_reason"].dropna()))
                    detail = " ".join(reasons) if reasons else "See the reportability fields below."
                    st.warning(f"Not reportable: {detail}")
        st.dataframe(result_frame, hide_index=True)
