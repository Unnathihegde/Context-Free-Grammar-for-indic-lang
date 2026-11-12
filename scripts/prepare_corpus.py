"""Prepare a clean Telugu LM training corpus from a raw text file."""

import argparse
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

try:
    from grammar_learn import load_all
    from ngram_lm import normalize_sentence
except ImportError:
    load_all = None

    def normalize_sentence(sentence):
        return " ".join(unicodedata.normalize("NFC", sentence).split())


DEFAULT_OUTPUT = ROOT / "data" / "raw" / "telugu_corpus.txt"
SENTENCE_SPLIT_REGEX = re.compile(r"[.?!।॥\r\n]+")


def is_mostly_telugu(sentence, threshold=0.6):
    """Check if the majority of non-punctuation/non-whitespace characters are Telugu."""
    telugu_count = 0
    total_letters = 0
    for char in sentence:
        if char.isspace() or unicodedata.category(char).startswith("P"):
            continue
        total_letters += 1
        if "\u0c00" <= char <= "\u0c7f":
            telugu_count += 1
    if total_letters == 0:
        return False
    return (telugu_count / total_letters) >= threshold


def load_treebank_set():
    """Load NFC-normalized treebank sentences to prevent training/test leakage."""
    if load_all is None:
        return set()
    try:
        sentences = load_all()
        return {
            normalize_sentence(" ".join(token["word"] for token in sentence))
            for sentence in sentences
        }
    except (FileNotFoundError, OSError):
        return set()


def process_corpus(raw_text, treebank_set=None):
    """Clean, split, filter, and deduplicate Telugu sentences.

    Returns the list of processed sentences and a dictionary of step counts.
    """
    if treebank_set is None:
        treebank_set = load_treebank_set()

    # Step 1: NFC Normalization
    text_nfc = unicodedata.normalize("NFC", raw_text)

    # Step 2: Split on punctuation (. ? ! and danda)
    raw_splits = [
        s.strip() for s in SENTENCE_SPLIT_REGEX.split(text_nfc) if s.strip()
    ]

    # Step 3: Keep 4-25 words
    length_filtered = []
    for sent in raw_splits:
        words = sent.split()
        if 4 <= len(words) <= 25:
            length_filtered.append(" ".join(words))

    # Step 4: Mostly Telugu script
    script_filtered = [
        sent for sent in length_filtered if is_mostly_telugu(sent)
    ]

    # Step 5: Deduplicate (preserving order)
    seen = set()
    deduped = []
    for sent in script_filtered:
        norm = normalize_sentence(sent)
        if norm not in seen:
            seen.add(norm)
            deduped.append(sent)

    # Step 6: Filter treebank leakage
    clean_sentences = [
        sent for sent in deduped if normalize_sentence(sent) not in treebank_set
    ]

    counts = {
        "raw_sentences": len(raw_splits),
        "length_filtered": len(length_filtered),
        "script_filtered": len(script_filtered),
        "deduplicated": len(deduped),
        "treebank_filtered": len(clean_sentences),
    }
    return clean_sentences, counts


def main():
    parser = argparse.ArgumentParser(
        description="Prepare a clean Telugu corpus for LM training."
    )
    parser.add_argument("input_path", type=Path, help="Path to raw Telugu text file")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to output corpus file (default: data/raw/telugu_corpus.txt)",
    )
    args = parser.parse_args()

    if not args.input_path.is_file():
        sys.exit(f"Input file not found: {args.input_path}")

    raw_text = args.input_path.read_text(encoding="utf8")
    sentences, counts = process_corpus(raw_text)

    print("Corpus preparation counts:")
    print(f"  1. Raw sentences split:        {counts['raw_sentences']}")
    print(f"  2. Length filtered (4-25 w):   {counts['length_filtered']}")
    print(f"  3. Script filtered (Telugu):   {counts['script_filtered']}")
    print(f"  4. Deduplicated:               {counts['deduplicated']}")
    print(f"  5. Treebank leakage filtered:  {counts['treebank_filtered']}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf8") as out:
        for sent in sentences:
            out.write(sent + "\n")
    print(f"Wrote {len(sentences)} clean sentences to: {args.output}")


if __name__ == "__main__":
    main()
