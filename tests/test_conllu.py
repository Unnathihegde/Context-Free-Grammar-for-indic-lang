from grammar_learn import read_conllu


def test_read_conllu_loads_handmade_sentences(tmp_path):
    corpus = tmp_path / "tiny.conllu"
    corpus.write_text(
        "# sent_id = 1\n"
        "1\tనేను\t_\tPRON\t_\t_\t2\tnsubj\t_\t_\n"
        "2\tవెళ్ళాను\t_\tVERB\t_\t_\t0\troot\t_\t_\n\n"
        "1-2\tignored\t_\t_\t_\t_\t_\t_\t_\t_\n"
        "1\tఆమె\t_\tPRON\t_\t_\t2\tnsubj\t_\t_\n"
        "2\tవచ్చింది\t_\tVERB\t_\t_\t0\troot\t_\t_\n",
        encoding="utf8",
    )

    sentences = read_conllu(corpus)

    assert len(sentences) == 2
    assert sentences[0][0] == {
        "id": 1, "word": "నేను", "pos": "PRON", "head": 2, "rel": "nsubj"
    }
