"""Evaluate PCFG and POS-bigram word-order ranking under matched CV folds."""

import csv
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

from nltk.parse import ViterbiParser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from grammar_learn import induce, load_all, parse_prob, prepare  # noqa: E402
from pairs_eval import make_pairs  # noqa: E402
from pos_bigram import PosBigramModel  # noqa: E402


K_FOLDS = 5
SEED = 0
MAX_LEN = 20
ADD_K = 0.1
BOOTSTRAP_RESAMPLES = 1_000


def accuracy(counts):
    total = sum(counts.values())
    return (counts["good wins"] + 0.5 * counts["tie"]) / total if total else 0.0


def winner(good_score, bad_score):
    if good_score > bad_score:
        return "good wins"
    if good_score < bad_score:
        return "bad wins"
    return "tie"


def evaluate(k=K_FOLDS, seed=SEED, max_len=MAX_LEN, add_k=ADD_K):
    """Return sentence-grouped outcomes for PCFG and POS-bigram scoring.

    Each item is ``(sentence_index, PCFG accuracy contribution, bigram accuracy
    contribution)``. Keeping outcomes grouped by sentence lets uncertainty
    estimates respect the dependence among several pairs from one sentence.
    """
    trees, _ = prepare(load_all())
    idx = list(range(len(trees)))
    random.Random(seed).shuffle(idx)
    folds = [idx[i::k] for i in range(k)]
    outcomes = defaultdict(list)

    for fold in folds:
        test = set(fold)
        train_trees = [trees[i] for i in idx if i not in test]
        parser = ViterbiParser(induce(train_trees))
        bigram = PosBigramModel(add_k=add_k).fit(
            [[token["pos"].lower() for token in sent] for sent, _ in train_trees]
        )
        for i in fold:
            sent = trees[i][0]
            if len(sent) > max_len:
                continue
            for kind, good, bad in make_pairs(sent):
                if good == bad:
                    continue
                pcfg_result = winner(parse_prob(parser, good), parse_prob(parser, bad))
                bigram_result = winner(
                    bigram.normalized_score(good), bigram.normalized_score(bad)
                )
                outcome_score = {"good wins": 1.0, "bad wins": 0.0, "tie": 0.5}
                outcomes[kind].append((i, outcome_score[pcfg_result], outcome_score[bigram_result]))
    return outcomes


def summarize_outcomes(outcomes):
    """Return accuracy and paired sentence-bootstrap statistics for outcomes."""
    if not outcomes:
        raise ValueError("cannot summarize zero pair outcomes")
    by_sentence = defaultdict(list)
    for sentence_index, pcfg_score, bigram_score in outcomes:
        by_sentence[sentence_index].append((pcfg_score, bigram_score))
    sentence_groups = list(by_sentence.values())
    pcfg_accuracy = sum(item[1] for item in outcomes) / len(outcomes)
    bigram_accuracy = sum(item[2] for item in outcomes) / len(outcomes)

    random_generator = random.Random(SEED)
    pcfg_samples, bigram_samples, difference_samples = [], [], []
    for _ in range(BOOTSTRAP_RESAMPLES):
        sampled_groups = [
            sentence_groups[random_generator.randrange(len(sentence_groups))]
            for _ in sentence_groups
        ]
        sampled_outcomes = [item for group in sampled_groups for item in group]
        sampled_pcfg = sum(item[0] for item in sampled_outcomes) / len(sampled_outcomes)
        sampled_bigram = sum(item[1] for item in sampled_outcomes) / len(sampled_outcomes)
        pcfg_samples.append(sampled_pcfg)
        bigram_samples.append(sampled_bigram)
        difference_samples.append(sampled_pcfg - sampled_bigram)

    def percentile(samples, quantile):
        ordered = sorted(samples)
        index = round((len(ordered) - 1) * quantile)
        return ordered[index]

    # Two-sided paired-bootstrap sign probability with a +1 finite-sample correction.
    non_positive = sum(value <= 0 for value in difference_samples)
    non_negative = sum(value >= 0 for value in difference_samples)
    paired_p_value = min(1.0, 2 * (min(non_positive, non_negative) + 1) /
                         (BOOTSTRAP_RESAMPLES + 1))
    return {
        "n_pairs": len(outcomes),
        "pcfg_acc": pcfg_accuracy,
        "bigram_acc": bigram_accuracy,
        "pcfg_ci_low": percentile(pcfg_samples, 0.025),
        "pcfg_ci_high": percentile(pcfg_samples, 0.975),
        "bigram_ci_low": percentile(bigram_samples, 0.025),
        "bigram_ci_high": percentile(bigram_samples, 0.975),
        "paired_bootstrap_p": paired_p_value,
    }


def write_results(output_path=ROOT / "results" / "wordorder_results.csv"):
    outcomes = evaluate()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    kinds = sorted(outcomes)
    rows = []
    for kind in kinds:
        rows.append({"kind": kind, **summarize_outcomes(outcomes[kind])})
    rows.append({"kind": "ALL", **summarize_outcomes(
        [item for kind in kinds for item in outcomes[kind]]
    )})

    formatted_rows = []
    for row in rows:
        formatted_rows.append({
            "kind": row["kind"],
            "n_pairs": row["n_pairs"],
            "n_validated": "not_applicable",
            "table_status": "not_applicable",
            "reportable": True,
            **{key: f"{row[key]:.6f}" for key in (
                "pcfg_acc", "bigram_acc", "pcfg_ci_low", "pcfg_ci_high",
                "bigram_ci_low", "bigram_ci_high", "paired_bootstrap_p",
            )},
        })
    with output_path.open("w", newline="", encoding="utf8") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=[
                "kind", "n_pairs", "pcfg_acc", "bigram_acc", "pcfg_ci_low",
                "pcfg_ci_high", "bigram_ci_low", "bigram_ci_high",
                "paired_bootstrap_p", "n_validated", "table_status", "reportable",
            ],
        )
        writer.writeheader()
        writer.writerows(formatted_rows)
    return formatted_rows


if __name__ == "__main__":
    for row in write_results():
        print(
            f"{row['kind']:12s} pairs={row['n_pairs']:4d} "
            f"pcfg={row['pcfg_acc']} bigram={row['bigram_acc']}"
        )
