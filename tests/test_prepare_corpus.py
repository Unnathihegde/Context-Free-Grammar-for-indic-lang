"""Tests for the corpus preparation script."""

import subprocess
import sys
from pathlib import Path

from scripts.prepare_corpus import is_mostly_telugu, process_corpus


def test_is_mostly_telugu():
    telugu_text = "నేను బడికి వెళ్ళాను మరియు చదివాను"
    english_text = "This is an English sentence in the text"
    mixed_mostly_telugu = "నేను college కి వెళ్ళాను"

    assert is_mostly_telugu(telugu_text) is True
    assert is_mostly_telugu(english_text) is False
    assert is_mostly_telugu(mixed_mostly_telugu, threshold=0.5) is True


def test_process_corpus_pipeline():
    treebank_leak = "అతను ఇంత చిన్న ఇంట్లో ఉన్నాడు"
    raw_input = (
        "ఇది చాలా చిన్నది.\n"  # 3 words -> dropped (< 4 words)
        "నేను ఈ రోజు బడికి వెళ్ళాను మరియు చదివాను. "  # 7 words Telugu -> kept
        "This English sentence has more than four words! "  # English -> dropped
        "అతను ఇంత చిన్న ఇంట్లో ఉన్నాడు? "  # In treebank -> dropped
        "నేను ఈ రోజు బడికి వెళ్ళాను మరియు చదివాను। "  # Duplicate -> dropped
        "ఆమె రేపు మా ఇంటికి వస్తుంది అని చెప్పింది.\n"  # 7 words Telugu -> kept
    )

    sentences, counts = process_corpus(raw_input, treebank_set={treebank_leak})

    assert counts["raw_sentences"] == 6
    assert counts["length_filtered"] == 5  # "ఇది చాలా చిన్నది" dropped
    assert counts["script_filtered"] == 4  # English dropped
    assert counts["deduplicated"] == 3     # duplicate dropped
    assert counts["treebank_filtered"] == 2  # treebank leak dropped

    assert len(sentences) == 2
    assert sentences[0] == "నేను ఈ రోజు బడికి వెళ్ళాను మరియు చదివాను"
    assert sentences[1] == "ఆమె రేపు మా ఇంటికి వస్తుంది అని చెప్పింది"


def test_prepare_corpus_cli(tmp_path):
    input_file = tmp_path / "raw.txt"
    output_file = tmp_path / "clean.txt"

    input_file.write_text(
        "నేను రేపు కాలేజీకి తప్పకుండా వెళ్తాను మరియు పరీక్ష రాస్తాను.\n",
        encoding="utf8",
    )

    cmd = [
        sys.executable,
        "scripts/prepare_corpus.py",
        str(input_file),
        "--output",
        str(output_file),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)

    assert "Corpus preparation counts" in res.stdout
    assert output_file.is_file()
    lines = output_file.read_text(encoding="utf8").strip().splitlines()
    assert len(lines) == 1
    assert "నేను రేపు కాలేజీకి" in lines[0]

