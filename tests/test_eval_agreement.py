from eval_agreement import split_by_sentence, table_status


def test_sentence_split_keeps_all_variants_of_one_good_sentence_together():
    rows = [
        {"good_sentence": "same sentence", "bad_sentence": "bad one"},
        {"good_sentence": "same sentence", "bad_sentence": "bad two"},
        {"good_sentence": "other sentence", "bad_sentence": "bad three"},
    ]

    validation, test = split_by_sentence(rows)

    validation_good = {row["good_sentence"] for row in validation}
    test_good = {row["good_sentence"] for row in test}
    assert validation_good.isdisjoint(test_good)
    assert len(validation) + len(test) == len(rows)


def test_table_must_have_every_row_validated_to_be_reportable():
    assert table_status([{"status": "validated"}]) == "validated"
    assert table_status([{"status": "validated"}, {"status": "unvalidated"}]) == "unvalidated"
