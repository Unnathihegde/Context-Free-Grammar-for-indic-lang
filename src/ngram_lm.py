"""A small interpolated absolute-discounting word trigram language model."""

import math
import unicodedata
from collections import Counter
from pathlib import Path


START = "<s>"
END = "</s>"
UNK = "<unk>"
DEFAULT_CORPUS = Path("data/raw/telugu_corpus.txt")


def normalize_sentence(sentence):
    """Normalize Unicode and whitespace before comparing or tokenizing text."""
    return " ".join(unicodedata.normalize("NFC", sentence).split())


def load_training_sentences(corpus_path=DEFAULT_CORPUS, evaluation_sentences=(), max_sentences=None):
    """Load corpus lines, excluding NFC-normalized held-out evaluation sentences."""
    corpus_path = Path(corpus_path)
    if not corpus_path.is_file():
        raise FileNotFoundError(
            f"Telugu LM corpus not found: {corpus_path}. "
            "Provide data/raw/telugu_corpus.txt (one sentence per line)."
        )
    evaluation_set = {normalize_sentence(sentence) for sentence in evaluation_sentences}
    sentences = []
    with corpus_path.open(encoding="utf8") as corpus_file:
        for line in corpus_file:
            sentence = normalize_sentence(line)
            if not sentence or sentence in evaluation_set:
                continue
            sentences.append(sentence.split())
            if max_sentences is not None and len(sentences) >= max_sentences:
                break
    return sentences


class TrigramLanguageModel:
    """Interpolated absolute-discounting trigram model over whitespace tokens."""

    def __init__(self, discount=0.75, min_count=1):
        if not 0 < discount < 1:
            raise ValueError("discount must be between zero and one")
        if min_count < 1:
            raise ValueError("min_count must be at least one")
        self.discount = discount
        self.min_count = min_count
        self.vocabulary = set()
        self.unigram_counts = Counter()
        self.bigram_counts = Counter()
        self.trigram_counts = Counter()
        self.bigram_context_counts = Counter()
        self.trigram_context_counts = Counter()
        self.bigram_successors = Counter()
        self.trigram_successors = Counter()

    def fit(self, sentences):
        """Fit from tokenized sentences, retaining a dedicated unknown-token class."""
        sentences = [list(sentence) for sentence in sentences if sentence]
        if not sentences:
            raise ValueError("at least one non-empty training sentence is required")
        raw_counts = Counter(token for sentence in sentences for token in sentence)
        self.vocabulary = {token for token, count in raw_counts.items() if count >= self.min_count}
        self.vocabulary.update({UNK, END})

        for sentence in sentences:
            mapped = [token if token in self.vocabulary else UNK for token in sentence]
            events = [START, START, *mapped, END]
            for position in range(2, len(events)):
                previous_two, previous_one, current = events[position - 2:position + 1]
                self.unigram_counts[current] += 1
                self.bigram_counts[previous_one, current] += 1
                self.trigram_counts[previous_two, previous_one, current] += 1
                self.bigram_context_counts[previous_one] += 1
                self.trigram_context_counts[previous_two, previous_one] += 1
        for previous, current in self.bigram_counts:
            self.bigram_successors[previous] += 1
        for previous_two, previous_one, current in self.trigram_counts:
            self.trigram_successors[previous_two, previous_one] += 1
        return self

    def _map_token(self, token):
        return token if token in self.vocabulary else UNK

    def _unigram_probability(self, token):
        vocabulary_size = len(self.vocabulary)
        total = sum(self.unigram_counts.values())
        return (self.unigram_counts[token] + 1) / (total + vocabulary_size)

    def _bigram_probability(self, previous, current):
        context_count = self.bigram_context_counts[previous]
        if not context_count:
            return self._unigram_probability(current)
        observed = self.bigram_counts[previous, current]
        first_term = max(observed - self.discount, 0) / context_count
        backoff_weight = self.discount * self.bigram_successors[previous] / context_count
        return first_term + backoff_weight * self._unigram_probability(current)

    def _trigram_probability(self, previous_two, previous_one, current):
        context = previous_two, previous_one
        context_count = self.trigram_context_counts[context]
        if not context_count:
            return self._bigram_probability(previous_one, current)
        observed = self.trigram_counts[previous_two, previous_one, current]
        first_term = max(observed - self.discount, 0) / context_count
        backoff_weight = self.discount * self.trigram_successors[context] / context_count
        return first_term + backoff_weight * self._bigram_probability(previous_one, current)

    def normalized_score(self, sentence):
        """Return sentence log probability normalized by its lexical-token count."""
        if not self.vocabulary:
            raise ValueError("fit the model before scoring")
        if isinstance(sentence, str):
            tokens = normalize_sentence(sentence).split()
        else:
            tokens = [unicodedata.normalize("NFC", token) for token in sentence]
        if not tokens:
            raise ValueError("cannot score an empty sentence")
        events = [START, START, *(self._map_token(token) for token in tokens), END]
        score = 0.0
        for position in range(2, len(events)):
            probability = self._trigram_probability(*events[position - 2:position + 1])
            score += math.log(probability)
        return score / len(tokens)


def train_from_corpus(corpus_path=DEFAULT_CORPUS, evaluation_sentences=(), max_sentences=None,
                      discount=0.75, min_count=1):
    sentences = load_training_sentences(corpus_path, evaluation_sentences, max_sentences)
    return TrigramLanguageModel(discount=discount, min_count=min_count).fit(sentences)


if __name__ == "__main__":
    try:
        model = train_from_corpus()
    except (FileNotFoundError, ValueError) as error:
        raise SystemExit(f"Cannot train word LM: {error}")
    print(f"trained trigram LM on {sum(model.unigram_counts.values())} predicted tokens")
