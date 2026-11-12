"""Leakage-aware evaluation helpers for validated agreement pairs."""

import csv
import random
from collections import defaultdict
from pathlib import Path

from agreement import CANDIDATES_PATH, TABLE_PATH, load_agreement_table
from hybrid import hybrid_score, score_sentence
from ngram_lm import DEFAULT_CORPUS, TrigramLanguageModel, load_training_sentences, normalize_sentence


ROOT = Path(__file__).resolve().parents[1]
VALIDATED_PATH = ROOT / "data" / "agreement" / "agreement_pairs_validated.csv"
RESULTS_PATH = ROOT / "results" / "agreement_results.csv"
SOURCES = ("generated", "speaker_written")
LAMBDA_GRID = (0, 0.1, 0.5, 1, 2, 5, 10)
BOOTSTRAP_RESAMPLES = 1_000
SEED = 0
DEMO_CORPUS = [
    ["నేను", "వెళ్ళాను"],
    ["నువ్వు", "వెళ్ళావు"],
    ["ఆమె", "వచ్చింది"],
]


def load_pair_rows(candidate_path=CANDIDATES_PATH, validated_path=VALIDATED_PATH):
    """Load generated and speaker-maintained pair files, retaining source labels."""
    pairs = []
    for path, default_source in ((Path(candidate_path), "generated"),
                                 (Path(validated_path), "speaker_written")):
        if not path.is_file():
            continue
        with path.open(newline="", encoding="utf8") as pair_file:
            for row in csv.DictReader(pair_file):
                row = {key: value or "" for key, value in row.items()}
                row["source"] = row.get("source") or default_source
                if row["source"] not in SOURCES:
                    raise ValueError(f"unknown pair source: {row['source']}")
                row["good_sentence"] = normalize_sentence(row["good_sentence"])
                row["bad_sentence"] = normalize_sentence(row["bad_sentence"])
                pairs.append(row)
    return pairs


def is_validated(row):
    return row.get("validated", "").strip().lower() == "yes"


def table_status(table_rows):
    """A table is usable for reportable results only after every row is validated."""
    statuses = {row.get("status", "").strip().lower() for row in table_rows}
    return "validated" if statuses == {"validated"} else "unvalidated"


def split_by_sentence(rows, seed=SEED, validation_fraction=0.7):
    """Split all variants of a good sentence into either validation or test."""
    groups = defaultdict(list)
    for row in rows:
        groups[row["good_sentence"]].append(row)
    sentence_keys = list(groups)
    random.Random(seed).shuffle(sentence_keys)
    if len(sentence_keys) < 2:
        return list(rows), []
    validation_count = max(1, min(len(sentence_keys) - 1,
                                  round(len(sentence_keys) * validation_fraction)))
    validation_keys = set(sentence_keys[:validation_count])
    validation, test = [], []
    for sentence, group in groups.items():
        (validation if sentence in validation_keys else test).extend(group)
    return validation, test


def evaluation_sentences(rows):
    return [sentence for row in rows for sentence in (row["good_sentence"], row["bad_sentence"])]


def build_language_model(rows, corpus_path=DEFAULT_CORPUS, max_sentences=None):
    """Train after removing every evaluation sentence, or enter clearly marked demo mode."""
    corpus_path = Path(corpus_path)
    if not corpus_path.is_file():
        return TrigramLanguageModel().fit(DEMO_CORPUS), "demo", len(DEMO_CORPUS)
    training_sentences = load_training_sentences(
        corpus_path, evaluation_sentences(rows), max_sentences=max_sentences
    )
    if not training_sentences:
        raise ValueError("no LM training sentences remain after evaluation-sentence removal")
    return TrigramLanguageModel().fit(training_sentences), "corpus", len(training_sentences)


def _outcome(good_score, bad_score):
    if good_score > bad_score:
        return 1.0
    if good_score < bad_score:
        return 0.0
    return 0.5


def score_pairs(rows, lm, table_rows, lambda_value):
    """Score pair rankings for B1, G, and H without changing the pair source."""
    scored = []
    for row in rows:
        b1_good, g_good, _ = score_sentence(lm, row["good_sentence"], table_rows, 0)
        b1_bad, g_bad, _ = score_sentence(lm, row["bad_sentence"], table_rows, 0)
        h_good = hybrid_score(b1_good, g_good, lambda_value)
        h_bad = hybrid_score(b1_bad, g_bad, lambda_value)
        g_score = 0.5 if g_good is None or g_bad is None else _outcome(-g_good, -g_bad)
        scored.append({
            "sentence": row["good_sentence"],
            "b1": _outcome(b1_good, b1_bad),
            "g": g_score,
            "hybrid": _outcome(h_good, h_bad),
            "abstained": float(g_good is None or g_bad is None),
        })
    return scored


def tune_lambda(validation_rows, lm, table_rows):
    """Select the smallest tied lambda using validation pairs only."""
    if not validation_rows:
        return None
    candidate_scores = []
    for lambda_value in LAMBDA_GRID:
        scored = score_pairs(validation_rows, lm, table_rows, lambda_value)
        candidate_scores.append((sum(row["hybrid"] for row in scored) / len(scored), lambda_value))
    return max(candidate_scores, key=lambda item: item[0])[1]


def _bootstrap_summary(scored, seed=SEED):
    """Sentence-resampled CIs and paired p-value for H minus B1."""
    if not scored:
        return None
    groups = defaultdict(list)
    for row in scored:
        groups[row["sentence"]].append(row)
    sentence_groups = list(groups.values())

    def mean(rows, key):
        return sum(row[key] for row in rows) / len(rows)

    point = {key: mean(scored, key) for key in ("b1", "g", "hybrid", "abstained")}
    generator = random.Random(seed)
    samples = {key: [] for key in ("b1", "g", "hybrid")}
    differences = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        sample = [row for _ in sentence_groups
                  for row in generator.choice(sentence_groups)]
        for key in samples:
            samples[key].append(mean(sample, key))
        differences.append(samples["hybrid"][-1] - samples["b1"][-1])

    def interval(values):
        ordered = sorted(values)
        return ordered[round((len(ordered) - 1) * 0.025)], ordered[round((len(ordered) - 1) * 0.975)]

    non_positive = sum(value <= 0 for value in differences)
    non_negative = sum(value >= 0 for value in differences)
    p_value = min(1.0, 2 * (min(non_positive, non_negative) + 1) /
                  (BOOTSTRAP_RESAMPLES + 1))
    return {
        "b1_acc": point["b1"], "g_acc": point["g"], "hybrid_acc": point["hybrid"],
        "abstention_rate": point["abstained"],
        "b1_ci_low": interval(samples["b1"])[0], "b1_ci_high": interval(samples["b1"])[1],
        "g_ci_low": interval(samples["g"])[0], "g_ci_high": interval(samples["g"])[1],
        "hybrid_ci_low": interval(samples["hybrid"])[0],
        "hybrid_ci_high": interval(samples["hybrid"])[1],
        "paired_bootstrap_p_h_minus_b1": p_value,
    }


def _reportability(n_distinct_total, status, lm_mode, n_test_pairs):
    reasons = []
    if n_distinct_total < 30:
        reasons.append("fewer than 30 distinct validated good sentences")
    if status != "validated":
        reasons.append("agreement table is unvalidated")
    if lm_mode != "corpus":
        reasons.append("LM corpus is missing; DEMO mode")
    if not n_test_pairs:
        reasons.append("no held-out test pairs")
    return not reasons, "; ".join(reasons)


def evaluate_agreement(candidate_path=CANDIDATES_PATH, validated_path=VALIDATED_PATH,
                       table_path=TABLE_PATH, corpus_path=DEFAULT_CORPUS):
    """Evaluate each source independently and return output rows plus run metadata."""
    table_rows = load_agreement_table(table_path)
    status = table_status(table_rows)
    all_pairs = load_pair_rows(candidate_path, validated_path)
    validated = [row for row in all_pairs if is_validated(row)]
    lm, lm_mode, lm_sentence_count = build_language_model(validated, corpus_path)
    result_rows = []
    for source in SOURCES:
        source_pairs = [row for row in all_pairs if row["source"] == source]
        source_validated = [row for row in source_pairs if is_validated(row)]
        distinct_total = len({row["good_sentence"] for row in source_validated})
        validation, test = split_by_sentence(source_validated)
        distinct_test = len({row["good_sentence"] for row in test})
        lambda_value = tune_lambda(validation, lm, table_rows)
        scored = score_pairs(test, lm, table_rows, lambda_value) if lambda_value is not None else []
        metrics = _bootstrap_summary(scored)
        reportable, reason = _reportability(distinct_total, status, lm_mode, len(test))
        row = {
            "source": source,
            "n_pairs": len(source_pairs),
            "n_validated": len(source_validated),
            "n_distinct_sentences_total": distinct_total,
            "n_distinct_sentences_test": distinct_test,
            "n_validation_pairs": len(validation),
            "n_test_pairs": len(test),
            "lambda": "" if lambda_value is None else lambda_value,
            "table_status": status,
            "lm_mode": lm_mode,
            "lm_training_sentences": lm_sentence_count,
            "reportable": reportable,
            "reportability_reason": reason,
        }
        for key in ("b1_acc", "g_acc", "hybrid_acc", "abstention_rate", "b1_ci_low", "b1_ci_high",
                    "g_ci_low", "g_ci_high", "hybrid_ci_low", "hybrid_ci_high",
                    "paired_bootstrap_p_h_minus_b1"):
            row[key] = "" if metrics is None else metrics[key]
        result_rows.append(row)
    return result_rows, {"lm_mode": lm_mode, "lm_training_sentences": lm_sentence_count,
                         "table_status": status}


RESULT_FIELDS = [
    "source", "n_pairs", "n_validated", "n_distinct_sentences_total", "n_distinct_sentences_test",
    "n_validation_pairs", "n_test_pairs", "lambda",
    "b1_acc", "g_acc", "hybrid_acc", "abstention_rate", "b1_ci_low", "b1_ci_high",
    "g_ci_low", "g_ci_high", "hybrid_ci_low", "hybrid_ci_high",
    "paired_bootstrap_p_h_minus_b1", "table_status", "lm_mode", "lm_training_sentences",
    "reportable", "reportability_reason",
]


def write_results(output_path=RESULTS_PATH, **kwargs):
    rows, metadata = evaluate_agreement(**kwargs)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: f"{value:.6f}" if isinstance(value, float) else value
                             for key, value in row.items()})
    return rows, metadata
