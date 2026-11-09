from nltk.parse import ViterbiParser

from grammar_learn import induce, parse_prob, pos_seq, prepare


def tiny_sentence():
    return [
        {"id": 1, "word": "నేను", "pos": "PRON", "head": 2, "rel": "nsubj"},
        {"id": 2, "word": "వెళ్ళాను", "pos": "VERB", "head": 0, "rel": "root"},
    ]


def test_usable_tree_leaves_match_its_pos_sequence():
    trees, skipped = prepare([tiny_sentence()])

    assert not skipped
    assert len(trees) == 1
    sentence, tree = trees[0]
    assert tree.leaves() == pos_seq(sentence)


def test_parse_prob_is_zero_for_an_unseen_tag():
    trees, _ = prepare([tiny_sentence()])
    parser = ViterbiParser(induce(trees))

    assert parse_prob(parser, ["x_unseen"]) == 0.0
