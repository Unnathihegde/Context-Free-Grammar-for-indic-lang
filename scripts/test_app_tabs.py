"""Headless AppTest runner for the new Streamlit Telugu Grammar Analyzer.

Tests analysis across all tabs for 3 sentences:
1. 'రాము ఇంట్లోకి వెళ్ళాడు'
2. 'నేను పుస్తకం చదివాను .'
3. 'రాము నేను రేపు వెళ్తాను అని కమలతో చెప్పేడు .'
"""

import os
import sys

from streamlit.testing.v1 import AppTest

# Add project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def run_sentence_apptest(sentence: str):
    print("=" * 80)
    print(f"RUNNING APPTEST FOR: {sentence}")
    print("=" * 80)

    at = AppTest.from_file("app/streamlit_app.py", default_timeout=60)
    at.run()
    if at.exception:
        print(f"Exception on init: {at.exception}")
        return

    # Enter text in the input and click analyze
    at.text_input[0].input(sentence)
    at.button[0].click().run()

    if at.exception:
        print(f"Exception after analyze: {at.exception}")
        return

    # Render summary card
    print("\n--- SUMMARY METRICS & TEMPLATE CARD ---")
    for m in at.metric:
        print(f"Metric [{m.label}]: {m.value}")

    for md in at.markdown:
        v = str(md.value)
        if "summary-card" in v or "Automatic summary" in v:
            print(f"Summary Card: {v}")

    # Render DataFrames
    print("\n--- RENDERED TABLES ---")
    for i, df_elem in enumerate(at.dataframe):
        df = df_elem.value
        title = getattr(df_elem, "help", None) or f"Table {i+1}"
        print(f"\nDataFrame {i+1} [Columns: {list(df.columns)}]:")
        print(df.to_string(index=False))

    # Render Subheaders & Infoboxes
    print("\n--- RENDERED HEADINGS & MESSAGES ---")
    for sub in at.subheader:
        print(f"Subheader: {sub.value}")

    for info in at.info:
        print(f"Info Box: {info.value}")

    for succ in at.success:
        print(f"Success Box: {succ.value}")

    for warn in at.warning:
        print(f"Warning Box: {warn.value}")


def main():
    test_sentences = [
        "రాము ఇంట్లోకి వెళ్ళాడు",
        "నేను పుస్తకం చదివాను .",
        "రాము నేను రేపు వెళ్తాను అని కమలతో చెప్పేడు .",
    ]
    for s in test_sentences:
        run_sentence_apptest(s)


if __name__ == "__main__":
    main()
