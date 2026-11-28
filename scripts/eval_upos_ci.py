"""Compute sentence-level 95% bootstrap CIs for UPOS accuracy and paired p-value (XLM-R vs Stanza).

Updates only the UPOS accuracy rows in results/model_comparison.csv without re-running
the word-order PLL evaluation.
"""

import csv
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import stanza
import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from grammar_learn import read_conllu  # noqa: E402

SEED = 0
BOOTSTRAP_RESAMPLES = 1000


def score_stanza_per_sentence(
    sents: List[List[Dict[str, Any]]], nlp: Any
) -> List[Tuple[int, int]]:
    """Return (correct_tokens, total_tokens) per sentence for Stanza pretokenized."""
    outcomes: List[Tuple[int, int]] = []
    for sent in sents:
        words = [t["word"] for t in sent]
        gold = [t["pos"] for t in sent]
        doc = nlp([words])
        preds = [w.upos for w in doc.sentences[0].words]
        corr = sum(1 for p, g in zip(preds, gold) if p == g)
        outcomes.append((corr, len(gold)))
    return outcomes


def score_bert_per_sentence(
    sents: List[List[Dict[str, Any]]], model_dir: Path
) -> List[Tuple[int, int]]:
    """Return (correct_tokens, total_tokens) per sentence for a fine-tuned HF token classifier."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForTokenClassification.from_pretrained(model_dir).to(device)
    model.eval()
    id2label = model.config.id2label

    outcomes: List[Tuple[int, int]] = []
    with torch.no_grad():
        for sent in sents:
            words = [t["word"] for t in sent]
            gold = [t["pos"] for t in sent]
            enc = tokenizer(
                words,
                is_split_into_words=True,
                truncation=True,
                max_length=128,
                return_tensors="pt",
            )
            word_ids = enc.word_ids()
            logits = model(
                input_ids=enc["input_ids"].to(device),
                attention_mask=enc["attention_mask"].to(device),
            ).logits[0].cpu()
            pred_ids = torch.argmax(logits, dim=-1).tolist()

            preds_by_word: Dict[int, str] = {}
            prev_wid = None
            for idx, wid in enumerate(word_ids):
                if wid is not None and wid != prev_wid:
                    preds_by_word[wid] = id2label[pred_ids[idx]]
                prev_wid = wid

            corr = sum(1 for wi, g in enumerate(gold) if preds_by_word.get(wi) == g)
            outcomes.append((corr, len(gold)))
    return outcomes


def bootstrap_upos(
    outcomes_a: List[Tuple[int, int]],
    outcomes_b: List[Tuple[int, int]],
    seed: int = SEED,
    n_resamples: int = BOOTSTRAP_RESAMPLES,
) -> Dict[str, float]:
    """Compute sentence-level bootstrap 95% CIs for A, B, and paired p-value (A - B)."""
    assert len(outcomes_a) == len(outcomes_b)
    n_sents = len(outcomes_a)
    acc_a = sum(c for c, _ in outcomes_a) / sum(n for _, n in outcomes_a)
    acc_b = sum(c for c, _ in outcomes_b) / sum(n for _, n in outcomes_b)

    rng = random.Random(seed)
    a_samples, b_samples, diff_samples = [], [], []
    for _ in range(n_resamples):
        idxs = [rng.randrange(n_sents) for _ in range(n_sents)]
        ca = sum(outcomes_a[i][0] for i in idxs)
        na = sum(outcomes_a[i][1] for i in idxs)
        cb = sum(outcomes_b[i][0] for i in idxs)
        nb = sum(outcomes_b[i][1] for i in idxs)
        sa = ca / na
        sb = cb / nb
        a_samples.append(sa)
        b_samples.append(sb)
        diff_samples.append(sa - sb)

    def pct(vals: List[float], q: float) -> float:
        s = sorted(vals)
        return s[round((len(s) - 1) * q)]

    non_pos = sum(d <= 0 for d in diff_samples)
    non_neg = sum(d >= 0 for d in diff_samples)
    p_val = min(1.0, 2 * (min(non_pos, non_neg) + 1) / (n_resamples + 1))

    return {
        "acc_a": acc_a,
        "acc_b": acc_b,
        "a_ci_low": pct(a_samples, 0.025),
        "a_ci_high": pct(a_samples, 0.975),
        "b_ci_low": pct(b_samples, 0.025),
        "b_ci_high": pct(b_samples, 0.975),
        "p_val": p_val,
    }


def main() -> None:
    nlp = stanza.Pipeline(
        "te",
        processors="tokenize,pos,lemma,depparse",
        tokenize_pretokenized=True,
        download_method=None,
        verbose=False,
    )

    stats_by_task_model: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for split in ("dev", "test"):
        sents = read_conllu(str(ROOT / "data" / f"te_{split}.conllu"))
        stanza_out = score_stanza_per_sentence(sents, nlp)
        xlmr_out = score_bert_per_sentence(sents, ROOT / "models" / "xlmr-pos")
        muril_out = score_bert_per_sentence(sents, ROOT / "models" / "muril-pos")

        xlmr_vs_stanza = bootstrap_upos(xlmr_out, stanza_out)
        muril_vs_stanza = bootstrap_upos(muril_out, stanza_out)

        task = f"upos_acc:{split}"
        stats_by_task_model[(task, "Stanza (1.15.1)")] = {
            "acc": xlmr_vs_stanza["acc_b"],
            "ci_low": xlmr_vs_stanza["b_ci_low"],
            "ci_high": xlmr_vs_stanza["b_ci_high"],
            "p_vs_stanza": None,
        }
        stats_by_task_model[(task, "xlm-roberta-base")] = {
            "acc": xlmr_vs_stanza["acc_a"],
            "ci_low": xlmr_vs_stanza["a_ci_low"],
            "ci_high": xlmr_vs_stanza["a_ci_high"],
            "p_vs_stanza": xlmr_vs_stanza["p_val"],
        }
        stats_by_task_model[(task, "google/muril-base-cased")] = {
            "acc": muril_vs_stanza["acc_a"],
            "ci_low": muril_vs_stanza["a_ci_low"],
            "ci_high": muril_vs_stanza["a_ci_high"],
            "p_vs_stanza": muril_vs_stanza["p_val"],
        }

        print(f"=== {split.upper()} UPOS Bootstrap (1000 sentence resamples) ===", flush=True)
        print(
            f"  Stanza (1.15.1):        {xlmr_vs_stanza['acc_b']:.4f} "
            f"[{xlmr_vs_stanza['b_ci_low']:.4f}, {xlmr_vs_stanza['b_ci_high']:.4f}]",
            flush=True,
        )
        print(
            f"  xlm-roberta-base:       {xlmr_vs_stanza['acc_a']:.4f} "
            f"[{xlmr_vs_stanza['a_ci_low']:.4f}, {xlmr_vs_stanza['a_ci_high']:.4f}] "
            f"(paired p vs Stanza = {xlmr_vs_stanza['p_val']:.4f})",
            flush=True,
        )
        print(
            f"  google/muril-base-cased:{muril_vs_stanza['acc_a']:.4f} "
            f"[{muril_vs_stanza['a_ci_low']:.4f}, {muril_vs_stanza['a_ci_high']:.4f}] "
            f"(paired p vs Stanza = {muril_vs_stanza['p_val']:.4f})",
            flush=True,
        )

    csv_path = ROOT / "results" / "model_comparison.csv"
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    for row in rows:
        key = (row["task"], row["model"])
        if key in stats_by_task_model:
            st = stats_by_task_model[key]
            row["ci_low"] = f"{st['ci_low']:.4f}"
            row["ci_high"] = f"{st['ci_high']:.4f}"
            if row["model"] == "xlm-roberta-base" and st["p_vs_stanza"] is not None:
                base_note = row["notes"].split("; paired bootstrap p vs Stanza")[0]
                row["notes"] = f"{base_note}; paired bootstrap p vs Stanza = {st['p_vs_stanza']:.4f}"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nUpdated UPOS CIs and XLM-R vs Stanza p-values in {csv_path}", flush=True)


if __name__ == "__main__":
    main()
