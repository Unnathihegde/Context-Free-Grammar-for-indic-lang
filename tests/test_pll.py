"""Unit tests for src/pll.py and word-level pair generation."""

from types import SimpleNamespace
import pytest
import torch

from src.pairs_eval import make_word_pairs
from src.pll import score_pll


class DummyTokenizer:
    mask_token_id = 99
    pad_token_id = 0

    def __call__(self, text, return_tensors="pt", truncation=True, max_length=256):
        words = text.split()
        # [CLS]=1, word_ids=[10, 11, ...], [SEP]=2
        ids = [1] + [10 + i for i in range(len(words))] + [2]
        mask = [1] * len(ids)
        return {
            "input_ids": torch.tensor([ids], dtype=torch.long),
            "attention_mask": torch.tensor([mask], dtype=torch.long),
        }

    def get_special_tokens_mask(self, ids_list, already_has_special_tokens=True):
        return [1 if x in (1, 2) else 0 for x in ids_list]


class DummyMLM(torch.nn.Module):
    def __init__(self, vocab_size=120):
        super().__init__()
        self.vocab_size = vocab_size
        self.dummy_param = torch.nn.Parameter(torch.zeros(1))

    def forward(self, input_ids, attention_mask=None):
        bsz, seq_len = input_ids.shape
        # Deterministic logits favoring id 10, 11, 12...
        logits = torch.zeros((bsz, seq_len, self.vocab_size), dtype=torch.float32)
        for p in range(seq_len):
            logits[:, p, 10] = 2.0
            logits[:, p, 11] = 1.0
        return SimpleNamespace(logits=logits)


def test_score_pll_mocked():
    tok = DummyTokenizer()
    model = DummyMLM()
    res = score_pll("రాము వెళ్ళాడు", model_name="dummy", batch_size=1, tokenizer_and_model=(tok, model))
    assert res["n_words"] == 2
    assert res["n_subwords"] == 2
    assert res["total_pll"] < 0.0
    assert abs(res["normalized_pll"] - res["total_pll"] / 2.0) < 1e-6


def test_score_pll_rejects_empty_and_overlength():
    tok = DummyTokenizer()
    model = DummyMLM()
    with pytest.raises(ValueError):
        score_pll("   ", tokenizer_and_model=(tok, model))
    with pytest.raises(ValueError):
        score_pll("పదం " * 41, max_words=40, tokenizer_and_model=(tok, model))


def test_make_word_pairs_preserves_words():
    sent = [
        {"id": 1, "word": "రాము", "pos": "PROPN", "head": 3, "rel": "nsubj"},
        {"id": 2, "word": "ఇంట్లోకి", "pos": "NOUN", "head": 3, "rel": "obl"},
        {"id": 3, "word": "వెళ్ళాడు", "pos": "VERB", "head": 0, "rel": "root"},
    ]
    pairs = list(make_word_pairs(sent))
    assert len(pairs) == 1
    kind, g_pos, b_pos, g_words, b_words = pairs[0]
    assert kind == "verb_first"
    assert g_words == ["రాము", "ఇంట్లోకి", "వెళ్ళాడు"]
    assert b_words == ["వెళ్ళాడు", "రాము", "ఇంట్లోకి"]
    assert g_pos == ["propn", "noun", "verb"]
    assert b_pos == ["verb", "propn", "noun"]
