from agreement import build_candidates


def test_candidates_change_person_not_only_number():
    table = [
        {"form": "నేను", "type": "pronoun", "person": "1", "number": "sg", "gender": "", "source": "test", "validated_by": "", "status": "unvalidated"},
        {"form": "ాను", "type": "verb_ending", "person": "1", "number": "sg", "gender": "", "source": "test", "validated_by": "", "status": "unvalidated"},
        {"form": "ావు", "type": "verb_ending", "person": "2", "number": "sg", "gender": "", "source": "test", "validated_by": "", "status": "unvalidated"},
    ]
    sentences = [[
        {"id": 1, "word": "నేను", "pos": "PRON", "head": 2, "rel": "nsubj"},
        {"id": 2, "word": "చేసాను", "pos": "VERB", "head": 0, "rel": "root"},
    ]]

    counts, candidates = build_candidates(sentences, table)

    assert counts == {
        "nsubj_verb_pairs": 1,
        "recognized_pronoun_pairs": 1,
        "recognized_ending_pairs": 1,
        "candidate_pairs": 1,
    }
    assert candidates[0]["bad_ending"] == "ావు"
    assert candidates[0]["validated"] == ""
