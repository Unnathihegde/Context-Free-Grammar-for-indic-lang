"""Generate a neutral LM data-size curve for validated agreement test pairs."""

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agreement import TABLE_PATH, load_agreement_table  # noqa: E402
from eval_agreement import (  # noqa: E402
    CANDIDATES_PATH, DEFAULT_CORPUS, SOURCES, VALIDATED_PATH, _bootstrap_summary,
    _reportability, build_language_model, is_validated, load_pair_rows, score_pairs,
    split_by_sentence, table_status,
)


REQUESTED_SIZES = (1_000, 10_000, 100_000)
CSV_PATH = ROOT / "results" / "datasize_curve.csv"
PNG_PATH = ROOT / "results" / "datasize_curve.png"
FIELDS = [
    "source", "requested_n", "lm_training_sentences", "n_pairs", "n_validated",
    "n_test_pairs", "b1_acc", "b1_ci_low", "b1_ci_high", "g_acc", "table_status",
    "lm_mode", "reportable", "reportability_reason",
]


def run_curve(candidate_path=CANDIDATES_PATH, validated_path=VALIDATED_PATH,
              table_path=TABLE_PATH, corpus_path=DEFAULT_CORPUS):
    table_rows = load_agreement_table(table_path)
    status = table_status(table_rows)
    all_pairs = load_pair_rows(candidate_path, validated_path)
    validated = [row for row in all_pairs if is_validated(row)]
    test_by_source = {}
    for source in SOURCES:
        source_validated = [row for row in validated if row["source"] == source]
        _, test_by_source[source] = split_by_sentence(source_validated)

    rows = []
    for requested_n in REQUESTED_SIZES:
        lm, lm_mode, lm_training_sentences = build_language_model(
            validated, corpus_path=corpus_path, max_sentences=requested_n
        )
        for source in SOURCES:
            source_pairs = [row for row in all_pairs if row["source"] == source]
            source_validated = [row for row in source_pairs if is_validated(row)]
            scored = score_pairs(test_by_source[source], lm, table_rows, lambda_value=0)
            metrics = _bootstrap_summary(scored)
            reportable, reason = _reportability(
                len(source_validated), status, lm_mode, len(test_by_source[source])
            )
            rows.append({
                "source": source,
                "requested_n": requested_n,
                "lm_training_sentences": lm_training_sentences,
                "n_pairs": len(source_pairs),
                "n_validated": len(source_validated),
                "n_test_pairs": len(test_by_source[source]),
                "b1_acc": "" if metrics is None else metrics["b1_acc"],
                "b1_ci_low": "" if metrics is None else metrics["b1_ci_low"],
                "b1_ci_high": "" if metrics is None else metrics["b1_ci_high"],
                "g_acc": "" if metrics is None else metrics["g_acc"],
                "table_status": status,
                "lm_mode": lm_mode,
                "reportable": reportable,
                "reportability_reason": reason,
            })
    return rows


def write_curve(csv_path=CSV_PATH, png_path=PNG_PATH, **kwargs):
    rows = run_curve(**kwargs)
    csv_path, png_path = Path(csv_path), Path(png_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: f"{value:.6f}" if isinstance(value, float) else value
                             for key, value in row.items()})

    figure, axis = plt.subplots(figsize=(7, 4.5))
    plotted = False
    for source in SOURCES:
        source_rows = [row for row in rows if row["source"] == source and row["b1_acc"] != ""]
        if not source_rows:
            continue
        x_values = [row["lm_training_sentences"] for row in source_rows]
        b1_values = [row["b1_acc"] for row in source_rows]
        g_value = source_rows[0]["g_acc"]
        axis.plot(x_values, b1_values, marker="o", label=f"B1 ({source})")
        axis.axhline(g_value, linestyle="--", label=f"G ({source})")
        plotted = True
    axis.set_xlabel("LM training sentences")
    axis.set_ylabel("Pair-ranking accuracy")
    axis.set_title("Agreement test-pair scores by LM training size")
    if plotted:
        axis.legend()
    else:
        axis.text(0.5, 0.5, "No validated test pairs available", ha="center", va="center",
                  transform=axis.transAxes)
    figure.tight_layout()
    figure.savefig(png_path, dpi=150)
    plt.close(figure)
    return rows


if __name__ == "__main__":
    rows = write_curve()
    for row in rows:
        print(f"{row['source']} N={row['requested_n']} n_validated={row['n_validated']} "
              f"reportable={row['reportable']}")
        if not row["reportable"]:
            print(f"WARNING [{row['source']}]: {row['reportability_reason']}")
    print(f"wrote: {CSV_PATH}")
    print(f"wrote: {PNG_PATH}")
