"""Generate explicitly unvalidated Telugu subject--verb agreement candidates."""

import csv
import random
import unicodedata
from collections import defaultdict
from pathlib import Path

try:
    from src.grammar_learn import load_all
except ModuleNotFoundError:
    from grammar_learn import load_all


ROOT = Path(__file__).resolve().parents[1]
TABLE_PATH = ROOT / "data" / "agreement" / "agreement_table.csv"
CANDIDATES_PATH = ROOT / "data" / "agreement" / "agreement_pairs_candidates.csv"
PAIR_FIELDS = [
    "pair_id", "good_sentence", "bad_sentence", "subject", "good_ending",
    "bad_ending", "ending_variants", "risk_note", "fold", "source", "validated",
    "validator_notes",
]

ZERO_WIDTH_CHARS = str.maketrans("", "", "\u200b\u200c\u200d\ufeff")
_KNOWN_NON_VERBS = None


def strip_zero_width(text):
    """Remove zero-width formatting characters (ZWSP, ZWNJ, ZWJ, BOM)."""
    return text.translate(ZERO_WIDTH_CHARS)


def clean_for_matching(text):
    """Normalize Unicode (NFC) and strip zero-width characters for robust matching."""
    return unicodedata.normalize("NFC", strip_zero_width(text))


def normalized(text):
    return unicodedata.normalize("NFC", text)


def load_known_non_verbs(sentences=None):
    """Return words seen in the treebank as NOUN, PROPN, PRON, or ADJ, but never as VERB."""
    if sentences is None:
        sentences = load_all()
    non_verbs = set()
    verbs = set()
    for s in sentences:
        for t in s:
            w = clean_for_matching(t["word"])
            pos = t["pos"]
            if pos in {"NOUN", "PROPN", "PRON", "ADJ"}:
                non_verbs.add(w)
            if pos == "VERB":
                verbs.add(w)
    return non_verbs - verbs


def get_known_non_verbs(sentences=None):
    """Cached loader for treebank words that are known non-verbs."""
    global _KNOWN_NON_VERBS
    if _KNOWN_NON_VERBS is None:
        _KNOWN_NON_VERBS = load_known_non_verbs(sentences)
    return _KNOWN_NON_VERBS


def load_agreement_table(path=TABLE_PATH):
    """Load the project table without interpreting unvalidated entries as facts."""
    with Path(path).open(newline="", encoding="utf8") as table_file:
        return [{key: normalized(value) for key, value in row.items()}
                for row in csv.DictReader(table_file)]


def nsubj_verb_pairs(sentences):
    """Yield direct dependency pairs whose nsubj head is a VERB."""
    for sentence_index, sentence in enumerate(sentences):
        by_id = {token["id"]: token for token in sentence}
        for subject in sentence:
            if subject["rel"] != "nsubj" or subject["head"] == 0:
                continue
            verb = by_id.get(subject["head"])
            if verb and verb["pos"] == "VERB":
                yield sentence_index, sentence, subject, verb


def ending_forms(word, ending_rows, known_non_verbs=None):
    """Return every listed ending form matching a word, longest first.

    A match is accepted only if:
    (a) the remaining stem has at least 2 Telugu characters/syllables, AND
    (b) the full word is not a known NOUN, PROPN, PRON, or ADJ in the treebank
        (never seen as VERB).
    """
    clean_word = clean_for_matching(word)
    if known_non_verbs is None:
        known_non_verbs = get_known_non_verbs()
    if known_non_verbs and clean_word in known_non_verbs:
        return []

    valid_forms = []
    for row in ending_rows:
        ending = clean_for_matching(row["form"])
        if clean_word.endswith(ending):
            stem = clean_word[:-len(ending)]
            telugu_chars = [c for c in stem if "\u0c00" <= c <= "\u0c7f"]
            if len(telugu_chars) >= 2:
                valid_forms.append(row["form"])
    return sorted(set(valid_forms), key=len, reverse=True)


def fold_assignments(sentence_count, k=5, seed=0):
    indices = list(range(sentence_count))
    random.Random(seed).shuffle(indices)
    return {sentence_index: position % k for position, sentence_index in enumerate(indices)}


def _sentence_with_replacement(sentence, verb_id, replacement):
    return " ".join(
        replacement if token["id"] == verb_id else token["word"] for token in sentence
    )


def build_candidates(sentences, rows, k=5, seed=0, known_non_verbs=None):
    """Return count summary and candidate rows; every output remains unvalidated.

    Spelling variants of the same ending (e.g. -ాం and -ాము) produce one candidate
    per (good sentence, subject, bad person/number class), retaining all spellings
    in ending_variants. Suffix -ారు carries risk_note='honorific_possible'.
    """
    if known_non_verbs is None:
        known_non_verbs = get_known_non_verbs(sentences)

    pronouns = defaultdict(list)
    endings = defaultdict(list)
    for row in rows:
        if row["type"] == "pronoun":
            pronouns[clean_for_matching(row["form"])].append(row)
        elif row["type"] == "verb_ending":
            endings[clean_for_matching(row["form"])].append(row)

    # Group verb endings into grammatical classes (collapsing spelling variants)
    classes = []
    for form, form_rows in endings.items():
        key = tuple(sorted((r["person"], r["number"], r.get("gender", "")) for r in form_rows))
        found = False
        for c in classes:
            if c["key"] == key:
                c["forms"].append(form)
                c["rows"].extend(form_rows)
                found = True
                break
        if not found:
            classes.append({"key": key, "forms": [form], "rows": list(form_rows)})

    occurrences = list(nsubj_verb_pairs(sentences))
    recognized_pronouns = 0
    recognized_endings = 0
    candidates = []
    fold_by_sentence = fold_assignments(len(sentences), k=k, seed=seed)
    ending_rows_all = [row for group in endings.values() for row in group]

    for sentence_index, sentence, subject, verb in occurrences:
        subject_rows = pronouns.get(clean_for_matching(subject["word"]), [])
        matched_forms = ending_forms(verb["word"], ending_rows_all, known_non_verbs=known_non_verbs)
        if subject_rows:
            recognized_pronouns += 1
        if matched_forms:
            recognized_endings += 1
        if not subject_rows or not matched_forms:
            continue

        subject_people = {row["person"] for row in subject_rows}
        for good_ending in matched_forms:
            good_people = {row["person"] for row in endings[good_ending]}
            if not subject_people.intersection(good_people):
                continue
            stem = clean_for_matching(verb["word"])[:-len(good_ending)]
            for c in classes:
                forms = c["forms"]
                if good_ending in forms:
                    continue
                bad_people = {r["person"] for r in c["rows"]}
                if subject_people.intersection(bad_people):
                    continue
                bad_ending = forms[0]
                ending_variants = ", ".join(forms)
                risk_note = "honorific_possible" if bad_ending == "ారు" else ""
                replacement = stem + bad_ending
                candidates.append({
                    "pair_id": f"agreement_{len(candidates) + 1:04d}",
                    "good_sentence": " ".join(token["word"] for token in sentence),
                    "bad_sentence": _sentence_with_replacement(sentence, verb["id"], replacement),
                    "subject": subject["word"],
                    "good_ending": good_ending,
                    "bad_ending": bad_ending,
                    "ending_variants": ending_variants,
                    "risk_note": risk_note,
                    "fold": fold_by_sentence[sentence_index],
                    "source": "generated",
                    "validated": "",
                    "validator_notes": "",
                })
    counts = {
        "nsubj_verb_pairs": len(occurrences),
        "recognized_pronoun_pairs": recognized_pronouns,
        "recognized_ending_pairs": recognized_endings,
        "candidate_pairs": len(candidates),
    }
    return counts, candidates


def write_candidates(output_path=CANDIDATES_PATH, table_path=TABLE_PATH, sentences=None):
    """Generate the candidate CSV from the current treebank and table."""
    if sentences is None:
        sentences = load_all()
    counts, candidates = build_candidates(sentences, load_agreement_table(table_path))
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=PAIR_FIELDS)
        writer.writeheader()
        writer.writerows(candidates)
    return counts, candidates


if __name__ == "__main__":
    summary, candidates = write_candidates()
    for label, count in summary.items():
        print(f"{label}: {count}")
    print(f"wrote unvalidated candidates: {CANDIDATES_PATH}")
