"""Generate explicitly unvalidated Telugu subject--verb agreement candidates."""

import csv
import random
import unicodedata
from collections import defaultdict
from pathlib import Path

from grammar_learn import load_all


ROOT = Path(__file__).resolve().parents[1]
TABLE_PATH = ROOT / "data" / "agreement" / "agreement_table.csv"
CANDIDATES_PATH = ROOT / "data" / "agreement" / "agreement_pairs_candidates.csv"
PAIR_FIELDS = [
    "pair_id", "good_sentence", "bad_sentence", "subject", "good_ending",
    "bad_ending", "fold", "validated", "validator_notes",
]


def normalized(text):
    return unicodedata.normalize("NFC", text)


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


def ending_forms(word, ending_rows):
    """Return every listed ending form matching a word, longest first."""
    forms = {row["form"] for row in ending_rows if normalized(word).endswith(row["form"])}
    return sorted(forms, key=len, reverse=True)


def fold_assignments(sentence_count, k=5, seed=0):
    indices = list(range(sentence_count))
    random.Random(seed).shuffle(indices)
    return {sentence_index: position % k for position, sentence_index in enumerate(indices)}


def _sentence_with_replacement(sentence, verb_id, replacement):
    return " ".join(
        replacement if token["id"] == verb_id else token["word"] for token in sentence
    )


def build_candidates(sentences, rows, k=5, seed=0):
    """Return count summary and candidate rows; every output remains unvalidated.

    A candidate is created only when the pronoun and original verb ending have at
    least one shared person.  Replacement endings must have no person in common
    with the subject, preventing a mere number change or an ambiguous match.
    """
    pronouns = defaultdict(list)
    endings = defaultdict(list)
    for row in rows:
        if row["type"] == "pronoun":
            pronouns[row["form"]].append(row)
        elif row["type"] == "verb_ending":
            endings[row["form"]].append(row)

    occurrences = list(nsubj_verb_pairs(sentences))
    recognized_pronouns = 0
    recognized_endings = 0
    candidates = []
    fold_by_sentence = fold_assignments(len(sentences), k=k, seed=seed)

    for sentence_index, sentence, subject, verb in occurrences:
        subject_rows = pronouns.get(normalized(subject["word"]), [])
        matched_forms = ending_forms(verb["word"], [row for group in endings.values() for row in group])
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
            stem = normalized(verb["word"])[:-len(good_ending)]
            for bad_ending, bad_rows in endings.items():
                bad_people = {row["person"] for row in bad_rows}
                if bad_ending == good_ending or subject_people.intersection(bad_people):
                    continue
                replacement = stem + bad_ending
                candidates.append({
                    "pair_id": f"agreement_{len(candidates) + 1:04d}",
                    "good_sentence": " ".join(token["word"] for token in sentence),
                    "bad_sentence": _sentence_with_replacement(sentence, verb["id"], replacement),
                    "subject": subject["word"],
                    "good_ending": good_ending,
                    "bad_ending": bad_ending,
                    "fold": fold_by_sentence[sentence_index],
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
