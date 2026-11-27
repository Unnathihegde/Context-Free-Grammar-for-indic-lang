"""Fine-tune transformer UPOS taggers (XLM-RoBERTa / MuRIL) on UD Telugu-MTG.

Trains on data/te_train.conllu, selects best checkpoint by dev UPOS accuracy,
evaluates on dev and test with gold tokens and first-subword label alignment,
saves best checkpoints under models/, and writes results/bert_pos_eval.csv.
"""

import csv
import json
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from grammar_learn import read_conllu  # noqa: E402

SEED = 42
EPOCHS = 6
BATCH_SIZE = 16
LEARNING_RATE = 3e-5
MAX_LEN = 128

MODELS_TO_TRAIN = [
    ("xlm-roberta-base", ROOT / "models" / "xlmr-pos"),
    ("google/muril-base-cased", ROOT / "models" / "muril-pos"),
]


def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def get_hardware_desc() -> str:
    if torch.cuda.is_available():
        return f"GPU ({torch.cuda.get_device_name(0)})"
    return f"CPU ({os.cpu_count() or 1} cores)"


class ConlluPosDataset(Dataset):
    """Tokenized CoNLL-U dataset with first-subword label alignment."""

    def __init__(
        self,
        sentences: List[List[Dict[str, Any]]],
        tokenizer: Any,
        label2id: Dict[str, int],
        max_len: int = MAX_LEN,
    ) -> None:
        self.items: List[Dict[str, Any]] = []
        for sent in sentences:
            words = [t["word"] for t in sent]
            tags = [t["pos"] for t in sent]
            enc = tokenizer(
                words,
                is_split_into_words=True,
                truncation=True,
                max_length=max_len,
            )
            word_ids = enc.word_ids()
            labels: List[int] = []
            prev_wid = None
            for wid in word_ids:
                if wid is None:
                    labels.append(-100)
                elif wid != prev_wid:
                    labels.append(label2id[tags[wid]])
                else:
                    labels.append(-100)
                prev_wid = wid

            self.items.append({
                "input_ids": enc["input_ids"],
                "attention_mask": enc["attention_mask"],
                "labels": labels,
                "word_ids": word_ids,
                "gold_tags": tags,
            })

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        return self.items[idx]


def collate_fn(batch: List[Dict[str, Any]], pad_token_id: int) -> Dict[str, Any]:
    max_len = max(len(x["input_ids"]) for x in batch)
    input_ids, attention_mask, labels = [], [], []
    for x in batch:
        pad_len = max_len - len(x["input_ids"])
        input_ids.append(x["input_ids"] + [pad_token_id] * pad_len)
        attention_mask.append(x["attention_mask"] + [0] * pad_len)
        labels.append(x["labels"] + [-100] * pad_len)
    return {
        "input_ids": torch.tensor(input_ids, dtype=torch.long),
        "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
        "labels": torch.tensor(labels, dtype=torch.long),
    }


def evaluate_dataset(
    model: Any,
    dataset: ConlluPosDataset,
    id2label: Dict[int, str],
    pad_token_id: int,
    device: torch.device,
) -> Tuple[float, Dict[str, Dict[str, Any]]]:
    """Evaluate token-level UPOS accuracy and per-tag accuracy on gold tokens."""
    model.eval()
    loader = DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        collate_fn=lambda b: collate_fn(b, pad_token_id),
    )

    all_preds: List[int] = []
    all_golds: List[int] = []
    with torch.no_grad():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"]
            logits = model(input_ids=input_ids, attention_mask=attention_mask).logits
            preds = torch.argmax(logits, dim=-1).cpu()

            for p_row, l_row in zip(preds, labels):
                for p_id, l_id in zip(p_row.tolist(), l_row.tolist()):
                    if l_id != -100:
                        all_preds.append(p_id)
                        all_golds.append(l_id)

    total = len(all_golds)
    correct = sum(1 for p, g in zip(all_preds, all_golds) if p == g)
    overall_acc = correct / total if total else 0.0

    tag_total: Counter = Counter()
    tag_correct: Counter = Counter()
    for p, g in zip(all_preds, all_golds):
        g_tag = id2label[g]
        tag_total[g_tag] += 1
        if p == g:
            tag_correct[g_tag] += 1

    per_tag: Dict[str, Dict[str, Any]] = {}
    for tag in sorted(tag_total.keys()):
        n_t = tag_total[tag]
        c_t = tag_correct[tag]
        per_tag[tag] = {
            "correct": c_t,
            "total": n_t,
            "acc": round(c_t / n_t, 4) if n_t else 0.0,
        }

    return overall_acc, per_tag


def train_and_evaluate(
    model_name: str,
    save_dir: Path,
    train_sents: List[List[Dict[str, Any]]],
    dev_sents: List[List[Dict[str, Any]]],
    test_sents: List[List[Dict[str, Any]]],
    label_list: List[str],
) -> List[Dict[str, Any]]:
    """Train one transformer UPOS tagger and return dev/test evaluation rows."""
    set_seed(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    hardware = get_hardware_desc()

    label2id = {lbl: i for i, lbl in enumerate(label_list)}
    id2label = {i: lbl for i, lbl in enumerate(label_list)}

    print(f"\n=== Fine-tuning {model_name} on {hardware} ===")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForTokenClassification.from_pretrained(
        model_name,
        num_labels=len(label_list),
        id2label=id2label,
        label2id=label2id,
    )
    model.to(device)

    pad_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else 0
    train_ds = ConlluPosDataset(train_sents, tokenizer, label2id)
    dev_ds = ConlluPosDataset(dev_sents, tokenizer, label2id)
    test_ds = ConlluPosDataset(test_sents, tokenizer, label2id)

    train_loader = DataLoader(
        train_ds,
        batch_size=BATCH_SIZE,
        shuffle=True,
        collate_fn=lambda b: collate_fn(b, pad_id),
    )

    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=0.01)
    total_steps = len(train_loader) * EPOCHS
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=max(1, int(0.1 * total_steps)),
        num_training_steps=total_steps,
    )

    best_dev_acc = -1.0
    save_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss = 0.0
        for batch in train_loader:
            optimizer.zero_grad()
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)
            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            total_loss += float(loss.item())

        dev_acc, _ = evaluate_dataset(model, dev_ds, id2label, pad_id, device)
        avg_loss = total_loss / max(1, len(train_loader))
        print(f"  Epoch {epoch}/{EPOCHS} | loss={avg_loss:.4f} | dev_upos_acc={dev_acc:.4f}")

        if dev_acc > best_dev_acc:
            best_dev_acc = dev_acc
            model.save_pretrained(save_dir)
            tokenizer.save_pretrained(save_dir)

    train_time = time.time() - t_start
    print(f"  Best dev_upos_acc={best_dev_acc:.4f} | train_time={train_time:.1f}s | saved to {save_dir}")

    # Reload best checkpoint and evaluate dev & test
    best_model = AutoModelForTokenClassification.from_pretrained(save_dir).to(device)
    rows: List[Dict[str, Any]] = []
    for split_name, ds in [("dev", dev_ds), ("test", test_ds)]:
        acc, per_tag = evaluate_dataset(best_model, ds, id2label, pad_id, device)
        print(f"  [{model_name}] {split_name} upos_acc={acc:.4f}")
        rows.append({
            "model": model_name,
            "split": split_name,
            "upos_acc": round(acc, 4),
            "per_tag_accuracy": json.dumps(per_tag, ensure_ascii=False),
            "train_time_sec": round(train_time, 1),
            "hardware": hardware,
        })
    return rows


def main() -> None:
    train_sents = read_conllu(str(ROOT / "data" / "te_train.conllu"))
    dev_sents = read_conllu(str(ROOT / "data" / "te_dev.conllu"))
    test_sents = read_conllu(str(ROOT / "data" / "te_test.conllu"))

    all_tags = sorted({
        t["pos"]
        for sents in (train_sents, dev_sents, test_sents)
        for s in sents
        for t in s
    })
    print(f"Loaded train={len(train_sents)}, dev={len(dev_sents)}, test={len(test_sents)} | {len(all_tags)} UPOS tags")

    all_rows: List[Dict[str, Any]] = []
    for model_name, save_dir in MODELS_TO_TRAIN:
        try:
            rows = train_and_evaluate(model_name, save_dir, train_sents, dev_sents, test_sents, all_tags)
            all_rows.extend(rows)
        except Exception as exc:
            print(f"Warning: skipping {model_name} due to error: {exc}", file=sys.stderr)

    out_path = ROOT / "results" / "bert_pos_eval.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["model", "split", "upos_acc", "per_tag_accuracy", "train_time_sec", "hardware"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\nWrote {len(all_rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
