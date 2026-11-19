"""Evaluate Stanza Telugu pipeline on UD Telugu-MTG dev and test splits.

Measures UPOS accuracy, UAS, and LAS using gold tokenization (pretokenized=True).
Outputs results/stanza_eval.csv.
"""

from collections import Counter
from datetime import date
import os
import sys

import pandas as pd
import stanza

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.grammar_learn import read_conllu


def get_stanza_pipeline():
    """Load Stanza Telugu pipeline with fallback and default model directory."""
    default_dir = getattr(stanza.resources.common, "DEFAULT_MODEL_DIR", None)
    try:
        nlp = stanza.Pipeline(
            "te",
            dir=default_dir,
            processors="tokenize,pos,lemma,depparse",
            download_method=None,
            tokenize_pretokenized=True,
            verbose=False,
        )
        return nlp
    except Exception as e:
        print(f"Error loading Stanza Telugu model: {e}")
        print("Please ensure the model is installed by running:")
        print('    python -c "import stanza; stanza.download(\'te\')"')
        raise


def evaluate_split(nlp, conllu_path):
    """Evaluate pipeline on a CoNLL-U file with gold tokenization."""
    sents = read_conllu(conllu_path)
    n_sentences = len(sents)
    token_lists = [[t["word"] for t in s] for s in sents]

    # Run Stanza batch with gold tokenization
    doc = nlp(token_lists)

    total_tokens = 0
    correct_upos = 0
    correct_uas = 0
    correct_las = 0

    tag_counts = Counter()
    tag_correct = Counter()

    rel_counts = Counter()
    rel_correct_las = Counter()

    for gold_sent, pred_sent in zip(sents, doc.sentences):
        assert len(gold_sent) == len(pred_sent.words), "Token length mismatch"
        for gold_tok, pred_tok in zip(gold_sent, pred_sent.words):
            total_tokens += 1
            gold_pos = gold_tok["pos"]
            gold_head = gold_tok["head"]
            gold_rel = gold_tok["rel"]

            pred_pos = pred_tok.upos
            pred_head = pred_tok.head
            pred_rel = pred_tok.deprel

            # UPOS accuracy
            tag_counts[gold_pos] += 1
            if pred_pos == gold_pos:
                correct_upos += 1
                tag_correct[gold_pos] += 1

            # Dependency metrics
            head_match = (pred_head == gold_head)
            rel_match = (pred_rel == gold_rel)

            if head_match:
                correct_uas += 1

            rel_counts[gold_rel] += 1
            if head_match and rel_match:
                correct_las += 1
                rel_correct_las[gold_rel] += 1

    upos_acc = correct_upos / total_tokens if total_tokens else 0.0
    uas = correct_uas / total_tokens if total_tokens else 0.0
    las = correct_las / total_tokens if total_tokens else 0.0

    return {
        "n_sentences": n_sentences,
        "n_tokens": total_tokens,
        "upos_acc": upos_acc,
        "uas": uas,
        "las": las,
        "tag_counts": tag_counts,
        "tag_correct": tag_correct,
        "rel_counts": rel_counts,
        "rel_correct_las": rel_correct_las,
    }


def main():
    print("Loading Stanza Telugu pipeline (pretokenized mode)...")
    nlp = get_stanza_pipeline()

    splits = {
        "dev": "data/te_dev.conllu",
        "test": "data/te_test.conllu",
    }

    results = []
    today = str(date.today())
    version = getattr(stanza, "__version__", "unknown")

    for split_name, conllu_path in splits.items():
        print(f"\nEvaluating split: {split_name} ({conllu_path})...")
        res = evaluate_split(nlp, conllu_path)
        print(f"Sentences: {res['n_sentences']}, Tokens: {res['n_tokens']}")
        print(f"UPOS Accuracy: {res['upos_acc']:.4f}")
        print(f"UAS: {res['uas']:.4f}")
        print(f"LAS: {res['las']:.4f}")

        # Top 5 most frequent tags
        print(f"\nTop 5 tags by frequency in {split_name}:")
        for tag, count in res["tag_counts"].most_common(5):
            corr = res["tag_correct"][tag]
            acc = corr / count if count else 0.0
            print(f"  {tag:<8}: {acc:.4f} ({corr}/{count})")

        # Top 3 most frequent relations
        print(f"\nTop 3 relations by frequency in {split_name} (LAS):")
        for rel, count in res["rel_counts"].most_common(3):
            corr = res["rel_correct_las"][rel]
            las_rel = corr / count if count else 0.0
            print(f"  {rel:<12}: {las_rel:.4f} ({corr}/{count})")

        results.append({
            "split": split_name,
            "n_sentences": res["n_sentences"],
            "n_tokens": res["n_tokens"],
            "upos_acc": round(res["upos_acc"], 6),
            "uas": round(res["uas"], 6),
            "las": round(res["las"], 6),
            "stanza_version": version,
            "date": today,
        })

    out_csv = "results/stanza_eval.csv"
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    df = pd.DataFrame(results)
    df.to_csv(out_csv, index=False)
    print(f"\nSaved evaluation results to {out_csv}:")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
