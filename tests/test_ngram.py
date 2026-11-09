import pytest

from ngram_lm import TrigramLanguageModel, load_training_sentences


def test_loader_normalizes_and_excludes_evaluation_sentences(tmp_path):
    corpus = tmp_path / "toy.txt"
    corpus.write_text("cafe\u0301 test\nkeep this\nthird line\n", encoding="utf8")

    sentences = load_training_sentences(corpus, evaluation_sentences=["café test"], max_sentences=1)

    assert sentences == [["keep", "this"]]


def test_loader_reports_a_clear_missing_corpus_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="Telugu LM corpus not found"):
        load_training_sentences(tmp_path / "missing.txt")


def test_trigram_prefers_seen_token_order_and_scores_unknown_words():
    model = TrigramLanguageModel().fit([
        ["నేను", "వెళ్ళాను"],
        ["నేను", "వెళ్ళాను"],
    ])

    assert model.normalized_score("నేను వెళ్ళాను") > model.normalized_score("వెళ్ళాను నేను")
    assert isinstance(model.normalized_score("తెలియని పదం"), float)
