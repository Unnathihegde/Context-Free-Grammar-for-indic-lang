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
    assert candidates[0]["ending_variants"] == "ావు"
    assert candidates[0]["risk_note"] == ""
    assert candidates[0]["validated"] == ""


def test_spelling_variants_collapse_and_honorific_risk_note():
    table = [
        {"form": "నువ్వు", "type": "pronoun", "person": "2", "number": "sg", "gender": "", "source": "test", "validated_by": "", "status": "unvalidated"},
        {"form": "ావు", "type": "verb_ending", "person": "2", "number": "sg", "gender": "", "source": "test", "validated_by": "", "status": "unvalidated"},
        {"form": "ాం", "type": "verb_ending", "person": "1", "number": "pl", "gender": "", "source": "test", "validated_by": "", "status": "unvalidated"},
        {"form": "ాము", "type": "verb_ending", "person": "1", "number": "pl", "gender": "", "source": "test", "validated_by": "", "status": "unvalidated"},
        {"form": "ారు", "type": "verb_ending", "person": "3", "number": "pl", "gender": "", "source": "test", "validated_by": "", "status": "unvalidated"},
    ]
    sentences = [[
        {"id": 1, "word": "నువ్వు", "pos": "PRON", "head": 2, "rel": "nsubj"},
        {"id": 2, "word": "చూసావు", "pos": "VERB", "head": 0, "rel": "root"},
    ]]

    counts, candidates = build_candidates(sentences, table)

    # 2 bad ending classes: 1st person plural (ాం/ాము collapsed into 1), and 3rd person plural (ారు)
    assert counts["candidate_pairs"] == 2

    # Check the collapsed spelling variant pair
    pair_1pl = next(c for c in candidates if c["bad_ending"] == "ాం")
    assert pair_1pl["ending_variants"] == "ాం, ాము"
    assert pair_1pl["risk_note"] == ""

    # Check the honorific possible pair
    pair_aru = next(c for c in candidates if c["bad_ending"] == "ారు")
    assert pair_aru["risk_note"] == "honorific_possible"
