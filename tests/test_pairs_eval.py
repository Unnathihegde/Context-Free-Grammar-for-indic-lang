from pairs_eval import make_pairs


def test_make_pairs_never_yields_identical_sequences():
    sentence = [
        {"id": 1, "word": "ఈ", "pos": "DET", "head": 2, "rel": "det"},
        {"id": 2, "word": "పుస్తకం", "pos": "NOUN", "head": 3, "rel": "nsubj"},
        {"id": 3, "word": "ఉంది", "pos": "VERB", "head": 0, "rel": "root"},
    ]

    pairs = list(make_pairs(sentence))

    assert pairs
    assert all(good != bad for _, good, bad in pairs)
