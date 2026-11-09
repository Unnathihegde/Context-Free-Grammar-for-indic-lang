from pos_bigram import PosBigramModel


def test_add_k_model_prefers_seen_pos_order():
    model = PosBigramModel(add_k=0.1).fit([
        ["pron", "verb"],
        ["pron", "verb"],
    ])

    assert model.normalized_score(["pron", "verb"]) > model.normalized_score(["verb", "pron"])
