"""Pseudo-log-likelihood (PLL) scorer using masked language models.

Computes sentence pseudo-log-likelihood by masking each subword token in turn,
summing log-probabilities of the original tokens, and normalizing by token count.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import threading

import torch
import torch.nn.functional as F
from transformers import AutoModelForMaskedLM, AutoTokenizer

SUPPORTED_PLL_MODELS = [
    "xlm-roberta-base",
    "google/muril-base-cased",
]

_MODEL_CACHE: Dict[str, Tuple[Any, Any]] = {}
_CACHE_LOCK = threading.Lock()


def get_device() -> torch.device:
    """Return CUDA device if available, otherwise CPU."""
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_mlm(model_name: str = "xlm-roberta-base") -> Tuple[Any, Any]:
    """Load and cache a masked language model and its tokenizer."""
    with _CACHE_LOCK:
        if model_name in _MODEL_CACHE:
            return _MODEL_CACHE[model_name]

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForMaskedLM.from_pretrained(model_name)
        model.to(get_device())
        model.eval()
        _MODEL_CACHE[model_name] = (tokenizer, model)
        return tokenizer, model


def score_pll(
    sentence: Union[str, List[str]],
    model_name: str = "xlm-roberta-base",
    batch_size: int = 32,
    max_words: int = 40,
    tokenizer_and_model: Optional[Tuple[Any, Any]] = None,
) -> Dict[str, Any]:
    """Compute pseudo-log-likelihood (total and per-token normalized) for a sentence.

    Args:
        sentence: Input string or list of pre-tokenized words.
        model_name: Hugging Face masked LM identifier.
        batch_size: Number of masked sequences to evaluate per forward pass.
        max_words: Maximum number of whitespace-delimited words supported.
        tokenizer_and_model: Optional pre-loaded (tokenizer, model) tuple for testing.

    Returns:
        Dictionary with total_pll, normalized_pll, n_words, n_subwords, model, text.
    """
    if isinstance(sentence, list):
        words = [str(w) for w in sentence if str(w).strip()]
        text = " ".join(words)
    else:
        text = str(sentence).strip()
        words = text.split() if text else []

    if not words:
        raise ValueError("Input sentence cannot be empty.")
    if len(words) > max_words:
        raise ValueError(
            f"Sentence has {len(words)} words, exceeding the maximum of {max_words} tokens."
        )

    if tokenizer_and_model is not None:
        tokenizer, model = tokenizer_and_model
    else:
        tokenizer, model = load_mlm(model_name)

    encoded = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=256,
    )
    input_ids = encoded["input_ids"][0]  # [seq_len]
    attention_mask = encoded["attention_mask"][0]  # [seq_len]

    special_mask = tokenizer.get_special_tokens_mask(
        input_ids.tolist(), already_has_special_tokens=True
    )
    target_positions = [i for i, is_special in enumerate(special_mask) if is_special == 0]

    if not target_positions:
        return {
            "model": model_name,
            "text": text,
            "n_words": len(words),
            "n_subwords": 0,
            "total_pll": 0.0,
            "normalized_pll": 0.0,
        }

    mask_token_id = tokenizer.mask_token_id
    if mask_token_id is None:
        raise ValueError(f"Tokenizer for '{model_name}' does not define a mask_token_id.")

    device = next(model.parameters()).device if hasattr(model, "parameters") else get_device()
    n_masks = len(target_positions)

    # Build all masked copies: shape [n_masks, seq_len]
    masked_batch = input_ids.unsqueeze(0).repeat(n_masks, 1)
    attn_batch = attention_mask.unsqueeze(0).repeat(n_masks, 1)
    target_ids = []
    for row_idx, pos in enumerate(target_positions):
        target_ids.append(int(input_ids[pos].item()))
        masked_batch[row_idx, pos] = mask_token_id

    total_pll = 0.0
    with torch.no_grad():
        for start in range(0, n_masks, batch_size):
            end = min(start + batch_size, n_masks)
            b_ids = masked_batch[start:end].to(device)
            b_attn = attn_batch[start:end].to(device)
            outputs = model(input_ids=b_ids, attention_mask=b_attn)
            logits = outputs.logits  # [b, seq_len, vocab]

            for offset in range(end - start):
                pos = target_positions[start + offset]
                tid = target_ids[start + offset]
                log_probs = F.log_softmax(logits[offset, pos], dim=-1)
                total_pll += float(log_probs[tid].item())

    normalized_pll = total_pll / n_masks
    return {
        "model": model_name,
        "text": text,
        "n_words": len(words),
        "n_subwords": n_masks,
        "total_pll": total_pll,
        "normalized_pll": normalized_pll,
    }
