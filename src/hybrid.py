"""Agreement-rule and hybrid scoring for validated agreement evaluation only."""

import unicodedata
from collections import defaultdict

try:
    from src.agreement import clean_for_matching, ending_forms, get_known_non_verbs
except ModuleNotFoundError:
    from agreement import clean_for_matching, ending_forms, get_known_non_verbs


def _tokens(sentence):
    return unicodedata.normalize("NFC", sentence).split()


def agreement_check(sentence, table_rows, known_non_verbs=None):
    """Return table-backed agreement details for one sentence.

    The table supplies all person labels.  A form with multiple listed people (such
    as an honorific candidate) is considered compatible if it shares any person
    with the pronoun.  This function makes no linguistic claim beyond the table.
    """
    if known_non_verbs is None:
        known_non_verbs = get_known_non_verbs()

    pronouns = defaultdict(list)
    endings = defaultdict(list)
    for row in table_rows:
        clean_form = clean_for_matching(row["form"])
        if row["type"] == "pronoun":
            pronouns[clean_form].append(row)
        elif row["type"] == "verb_ending":
            endings[clean_form].append(row)

    tokens = _tokens(sentence)
    clean_tokens = [clean_for_matching(t) for t in tokens]
    subjects = [pronouns[clean_t] for clean_t in clean_tokens if clean_t in pronouns]
    recognized_verbs = []
    ending_rows = [row for rows in endings.values() for row in rows]
    for token, clean_t in zip(tokens, clean_tokens):
        if clean_t in pronouns:
            continue
        forms = ending_forms(token, ending_rows, known_non_verbs=known_non_verbs)
        if forms:
            # Longest-match behavior avoids counting a shorter ending inside a longer one.
            recognized_verbs.append(endings[clean_for_matching(forms[0])])
    if not subjects or not recognized_verbs:
        return {"violations": None, "rule_rows": [], "status": "abstained"}

    violations = 0
    rule_rows = []
    for subject_rows in subjects:
        subject_people = {row["person"] for row in subject_rows}
        for verb_rows in recognized_verbs:
            verb_people = {row["person"] for row in verb_rows}
            violations += not bool(subject_people.intersection(verb_people))
            rule_rows.extend(subject_rows + verb_rows)
    return {
        "violations": violations,
        "rule_rows": rule_rows,
        "status": "matched" if violations == 0 else "violated",
    }


def agreement_violations(sentence, table_rows, known_non_verbs=None):
    """Count pronoun--verb person mismatches, or return None when unsupported."""
    return agreement_check(sentence, table_rows, known_non_verbs=known_non_verbs)["violations"]


def hybrid_score(b1_score, violations, lambda_value):
    """Combine LM and agreement scores while preserving the abstention contract."""
    if violations is None:
        return b1_score
    return b1_score - lambda_value * violations


def score_sentence(lm, sentence, table_rows, lambda_value, known_non_verbs=None):
    """Return B1, G violations, and H for one sentence."""
    b1_score = lm.normalized_score(sentence)
    violations = agreement_violations(sentence, table_rows, known_non_verbs=known_non_verbs)
    return b1_score, violations, hybrid_score(b1_score, violations, lambda_value)
