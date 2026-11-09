"""A POS-bigram baseline with additive smoothing.

The baseline deliberately operates only on POS sequences.  It is trained inside
each cross-validation fold by the word-order runner; it never sees the held-out
sentences that produce evaluation pairs.
"""

import math
from collections import Counter


START = "<s>"
END = "</s>"


class PosBigramModel:
    """Add-k smoothed POS-bigram language model."""

    def __init__(self, add_k=0.1):
        if add_k <= 0:
            raise ValueError("add_k must be positive")
        self.add_k = add_k
        self.bigram_counts = Counter()
        self.context_counts = Counter()
        self.vocabulary = set()

    def fit(self, sequences):
        """Fit on an iterable of POS-tag sequences."""
        for sequence in sequences:
            self.vocabulary.update(sequence)
            events = [START, *sequence, END]
            for previous, current in zip(events, events[1:]):
                self.bigram_counts[previous, current] += 1
                self.context_counts[previous] += 1
        self.vocabulary.add(END)
        if len(self.vocabulary) == 1:
            raise ValueError("at least one non-empty sequence is required")
        return self

    def log_prob(self, sequence):
        """Return the log probability of a complete POS sequence."""
        if not self.vocabulary:
            raise ValueError("fit the model before scoring")
        vocab_size = len(self.vocabulary)
        events = [START, *sequence, END]
        score = 0.0
        for previous, current in zip(events, events[1:]):
            numerator = self.bigram_counts[previous, current] + self.add_k
            denominator = self.context_counts[previous] + self.add_k * vocab_size
            score += math.log(numerator / denominator)
        return score

    def normalized_score(self, sequence):
        """Length-normalized log probability, for comparing sentence scores."""
        if not sequence:
            raise ValueError("cannot score an empty sequence")
        return self.log_prob(sequence) / len(sequence)
