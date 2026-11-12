"""Tests for token-level status reporting in the Streamlit application."""

from streamlit.testing.v1 import AppTest

from app.streamlit_app import get_token_statuses
from ngram_lm import TrigramLanguageModel


TOY_TABLE = [
    {"form": "నేను", "type": "pronoun", "person": "1"},
    {"form": "ాను", "type": "verb_ending", "person": "1"},
]


def test_get_token_statuses_without_lm():
    sentence = "నేను తెలియని_పదం వెళ్ళాను"
    statuses = get_token_statuses(sentence, TOY_TABLE, lm=None)

    assert len(statuses) == 3

    # First token: "నేను" -> recognized pronoun
    assert statuses[0]["Token"] == "నేను"
    assert statuses[0]["Agreement Table"] == "KNOWN"
    assert statuses[0]["Agreement Detail"] == "pronoun"
    assert "LM Vocabulary" not in statuses[0]

    # Second token: "తెలియని_పదం" -> completely unknown
    assert statuses[1]["Token"] == "తెలియని_పదం"
    assert statuses[1]["Agreement Table"] == "UNKNOWN"
    assert statuses[1]["Agreement Detail"] == "-"
    assert "LM Vocabulary" not in statuses[1]

    # Third token: "వెళ్ళాను" -> verb ending -ాను recognized
    assert statuses[2]["Token"] == "వెళ్ళాను"
    assert statuses[2]["Agreement Table"] == "KNOWN"
    assert "-ాను" in statuses[2]["Agreement Detail"]


def test_get_token_statuses_with_lm():
    model = TrigramLanguageModel().fit([["నేను", "వెళ్ళాను"]])
    sentence = "నేను తెలియని_పదం వెళ్ళాను"
    statuses = get_token_statuses(sentence, TOY_TABLE, lm=model)

    assert statuses[0]["LM Vocabulary"] == "IN VOCABULARY"
    assert statuses[1]["LM Vocabulary"] == "UNKNOWN"
    assert statuses[2]["LM Vocabulary"] == "IN VOCABULARY"


def test_apptest_renders_token_status_table():
    at = AppTest.from_file("app/streamlit_app.py")
    at.run(timeout=30)
    assert not at.exception

    # Type a sentence containing both known and unknown words
    at.text_input[0].input("నేను తెలియని_పదం వెళ్ళాను").run(timeout=30)
    assert not at.exception

    # Confirm dataframes are rendered (token table and results)
    assert len(at.dataframe) >= 1
    token_df = at.dataframe[0].value
    assert "Token" in token_df.columns
    assert "Agreement Table" in token_df.columns
    assert "UNKNOWN" in token_df["Agreement Table"].values
