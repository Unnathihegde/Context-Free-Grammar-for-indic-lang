"""Evaluate and compare all models across POS tagging, parsing, and word-order pairs.

Produces results/model_comparison.csv with columns:
    task, model, metric, value, n, ci_low, ci_high, notes
"""

import csv
import random
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from nltk.parse import ViterbiParser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from grammar_learn import induce, load_all, parse_prob, prepare  # noqa: E402
from pairs_eval import make_word_pairs  # noqa: E402
from pll import load_mlm, score_pll  # noqa: E402
from pos_bigram import PosBigramModel  # noqa: E402

K_FOLDS = 5
SEED = 0
MAX_LEN = 20
ADD_K = 0.1
BOOTSTRAP_RESAMPLES = 1000


def winner_score(good_val: float, bad_val: float) -> float:
    if good_val > bad_val:
        return 1.0
    if good_val < bad_val:
        return 0.0
    return 0.5


def bootstrap_ci_and_p(
    outcomes: List[Tuple[int, float, float]],
    seed: int = SEED,
    n_resamples: int = BOOTSTRAP_RESAMPLES,
) -> Dict[str, Any]:
    """Compute sentence-grouped bootstrap 95% CI for model A, model B, and paired p-value (A - B)."""
    by_sent = defaultdict(list)
    for sent_idx, score_a, score_b in outcomes:
        by_sent[sent_idx].append((score_a, score_b))
    groups = list(by_sent.values())

    acc_a = sum(x[1] for x in outcomes) / len(outcomes)
    acc_b = sum(x[2] for x in outcomes) / len(outcomes)

    rng = random.Random(seed)
    a_samples, b_samples, diff_samples = [], [], []
    for _ in range(n_resamples):
        sampled_groups = [groups[rng.randrange(len(groups))] for _ in groups]
        flat = [item for g in sampled_groups for item in g]
        sa = sum(x[0] for x in flat) / len(flat)
        sb = sum(x[1] for x in flat) / len(flat)
        a_samples.append(sa)
        b_samples.append(sb)
        diff_samples.append(sa - sb)

    def pct(samples: List[float], q: float) -> float:
        ordered = sorted(samples)
        return ordered[round((len(ordered) - 1) * q)]

    non_pos = sum(d <= 0 for d in diff_samples)
    non_neg = sum(d >= 0 for d in diff_samples)
    p_val = min(1.0, 2 * (min(non_pos, non_neg) + 1) / (n_resamples + 1))

    return {
        "n": len(outcomes),
        "acc_a": acc_a,
        "acc_b": acc_b,
        "a_ci_low": pct(a_samples, 0.025),
        "a_ci_high": pct(a_samples, 0.975),
        "b_ci_low": pct(b_samples, 0.025),
        "b_ci_high": pct(b_samples, 0.975),
        "p_val": p_val,
    }


def evaluate_word_order_models(
    pll_models: List[str],
) -> List[Dict[str, Any]]:
    """Run 5-fold word-order pair evaluation for POS-bigram, PCFG, and PLL models."""
    trees, _ = prepare(load_all())
    idx = list(range(len(trees)))
    random.Random(SEED).shuffle(idx)
    folds = [idx[i::K_FOLDS] for i in range(K_FOLDS)]

    # Pre-load PLL models and keep a score cache keyed by (model_name, " ".join(words))
    loaded_mlms = {}
    for m_name in pll_models:
        try:
            print(f"Loading MLM for PLL scoring: {m_name}")
            loaded_mlms[m_name] = load_mlm(m_name)
        except Exception as exc:
            print(f"Warning: could not load MLM '{m_name}': {exc}", file=sys.stderr)

    pll_cache: Dict[Tuple[str, str], float] = {}

    def get_pll_norm(m_name: str, words: List[str]) -> float:
        key = (m_name, " ".join(words))
        if key not in pll_cache:
            res = score_pll(
                words,
                model_name=m_name,
                batch_size=32,
                max_words=40,
                tokenizer_and_model=loaded_mlms[m_name],
            )
            pll_cache[key] = res["normalized_pll"]
        return pll_cache[key]

    # Collect per-pair scores: model_key -> kind -> list of (sent_idx, score)
    model_outcomes: Dict[str, Dict[str, List[Tuple[int, float]]]] = defaultdict(
        lambda: defaultdict(list)
    )

    t0 = time.time()
    for fold_idx, fold in enumerate(folds):
        test = set(fold)
        train_trees = [trees[i] for i in idx if i not in test]
        parser = ViterbiParser(induce(train_trees))
        bigram = PosBigramModel(add_k=ADD_K).fit(
            [[token["pos"].lower() for token in sent] for sent, _ in train_trees]
        )

        for i in fold:
            sent = trees[i][0]
            if len(sent) > MAX_LEN:
                continue
            for kind, good_pos, bad_pos, good_words, bad_words in make_word_pairs(sent):
                if good_pos == bad_pos or good_words == bad_words:
                    continue

                pcfg_s = winner_score(parse_prob(parser, good_pos), parse_prob(parser, bad_pos))
                bigram_s = winner_score(
                    bigram.normalized_score(good_pos), bigram.normalized_score(bad_pos)
                )
                model_outcomes["Learned PCFG (POS)"][kind].append((i, pcfg_s))
                model_outcomes["POS-bigram (POS)"][kind].append((i, bigram_s))

                for m_name in loaded_mlms:
                    g_pll = get_pll_norm(m_name, good_words)
                    b_pll = get_pll_norm(m_name, bad_words)
                    pll_s = winner_score(g_pll, b_pll)
                    model_outcomes[f"PLL ({m_name})"][kind].append((i, pll_s))

        print(f"  Completed fold {fold_idx + 1}/{K_FOLDS} ({time.time() - t0:.1f}s)", flush=True)

    # Summarize all kinds + ALL
    kinds = sorted(model_outcomes["POS-bigram (POS)"].keys())
    rows: List[Dict[str, Any]] = []

    for kind in kinds + ["ALL"]:
        if kind == "ALL":
            bigram_list = [x for k in kinds for x in model_outcomes["POS-bigram (POS)"][k]]
        else:
            bigram_list = model_outcomes["POS-bigram (POS)"][kind]

        for model_label in ["POS-bigram (POS)", "Learned PCFG (POS)"] + [
            f"PLL ({m})" for m in loaded_mlms
        ]:
            if kind == "ALL":
                m_list = [x for k in kinds for x in model_outcomes[model_label][k]]
            else:
                m_list = model_outcomes[model_label][kind]

            paired = [
                (m_item[0], m_item[1], b_item[1])
                for m_item, b_item in zip(m_list, bigram_list)
            ]
            stats = bootstrap_ci_and_p(paired)
            note = "reference baseline"
            if model_label != "POS-bigram (POS)":
                note = f"paired bootstrap p vs POS-bigram = {stats['p_val']:.4f}"
                if model_label.startswith("PLL"):
                    note += "; pretrained MLM may have seen treebank sentences (potential pretraining leakage)"

            rows.append({
                "task": f"word_order:{kind}",
                "model": model_label,
                "metric": "pair_ranking_acc",
                "value": round(stats["acc_a"], 4),
                "n": stats["n"],
                "ci_low": round(stats["a_ci_low"], 4),
                "ci_high": round(stats["a_ci_high"], 4),
                "notes": note,
            })

    return rows


def load_pos_and_parsing_rows() -> List[Dict[str, Any]]:
    """Collect Stanza and BERT POS/parsing evaluation rows from results/*.csv."""
    rows: List[Dict[str, Any]] = []

    stanza_csv = ROOT / "results" / "stanza_eval.csv"
    if stanza_csv.exists():
        with open(stanza_csv, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                split = r["split"]
                n_tok = int(r["n_tokens"])
                ver = r.get("stanza_version", "")
                for metric_key, metric_label in [
                    ("upos_acc", "upos_acc"),
                    ("uas", "uas"),
                    ("las", "las"),
                ]:
                    rows.append({
                        "task": f"{metric_label}:{split}",
                        "model": f"Stanza ({ver})".strip(),
                        "metric": metric_label,
                        "value": round(float(r[metric_key]), 4),
                        "n": n_tok,
                        "ci_low": "",
                        "ci_high": "",
                        "notes": f"gold tokenization, {r['n_sentences']} sentences",
                    })

    bert_csv = ROOT / "results" / "bert_pos_eval.csv"
    if bert_csv.exists():
        # Get token counts per split from stanza_eval if available
        split_tokens = {"dev": 662, "test": 721}
        with open(bert_csv, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                split = r["split"]
                rows.append({
                    "task": f"upos_acc:{split}",
                    "model": r["model"],
                    "metric": "upos_acc",
                    "value": round(float(r["upos_acc"]), 4),
                    "n": split_tokens.get(split, ""),
                    "ci_low": "",
                    "ci_high": "",
                    "notes": f"gold tokenization, train_time={r['train_time_sec']}s ({r['hardware']})",
                })

    return rows


def main() -> None:
    pll_models = ["xlm-roberta-base", "google/muril-base-cased"]
    wo_rows = evaluate_word_order_models(pll_models)
    pos_parse_rows = load_pos_and_parsing_rows()

    all_rows = pos_parse_rows + wo_rows
    out_path = ROOT / "results" / "model_comparison.csv"
    fieldnames = ["task", "model", "metric", "value", "n", "ci_low", "ci_high", "notes"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nWrote {len(all_rows)} rows to {out_path}\n")
    print(f"{'TASK':<25} {'MODEL':<30} {'METRIC':<17} {'VAL':>7} {'N':>5} {'CI':>15}  {'NOTES'}")
    print("-" * 120)
    for r in all_rows:
        ci_str = f"[{r['ci_low']:.3f}, {r['ci_high']:.3f}]" if r["ci_low"] != "" else "-"
        print(
            f"{r['task']:<25} {r['model']:<30} {r['metric']:<17} "
            f"{float(r['value']):>7.4f} {str(r['n']):>5} {ci_str:>15}  {r['notes']}"
        )


if __name__ == "__main__":
    main()
