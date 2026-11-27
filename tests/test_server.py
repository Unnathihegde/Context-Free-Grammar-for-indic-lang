"""Unit and integration tests for FastAPI backend server (app/server.py)."""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.server import app


@pytest.fixture(scope="module")
def client():
    """Create a TestClient with Stanza model mocked so fast tests don't load PyTorch."""
    mock_pipeline = MagicMock()
    with patch("app.server.load_stanza_pipeline", return_value=mock_pipeline):
        with TestClient(app) as test_client:
            test_client.app.state.model_loaded = True
            test_client.app.state.nlp = mock_pipeline
            yield test_client


def test_health_endpoint(client):
    """Test health check returns proper structure and stanza version."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "model_loaded" in data
    assert "stanza_version" in data
    assert "model_error" in data


def test_examples_endpoint(client):
    """Test examples endpoint returns list loaded from dev/test treebank files."""
    response = client.get("/api/examples")
    assert response.status_code == 200
    examples = response.json()
    assert isinstance(examples, list)
    assert len(examples) > 0
    assert len(examples) <= 40
    # Every example is a non-empty string
    for ex in examples:
        assert isinstance(ex, str)
        assert len(ex.strip()) > 0


def test_analyze_empty_input_rejected(client):
    """Input validation: empty sentence returns 400 with friendly message."""
    response = client.post("/api/analyze", json={"sentence": "   "})
    assert response.status_code == 400
    data = response.json()
    assert "message" in data
    assert "empty" in data["message"].lower()


def test_analyze_overlength_input_rejected(client):
    """Input validation: sentence exceeding 300 characters returns 400."""
    long_sentence = "రాము " * 100  # > 400 characters
    assert len(long_sentence) > 300
    response = client.post("/api/analyze", json={"sentence": long_sentence})
    assert response.status_code == 400
    data = response.json()
    assert "message" in data
    assert "300" in data["message"]


def test_analyze_zero_width_hidden_chars_removed(client):
    """Input with zero-width characters has them stripped and notes flagged."""
    # Mock analyzer to return a minimal valid analysis structure
    mock_res = {
        "text": "రాము వెళ్ళాడు",
        "tokens": [
            {
                "id": 1,
                "text": "రాము",
                "translit": "rāmu",
                "upos": "PROPN",
                "upos_name": "Proper Noun",
                "head": 2,
                "head_text": "వెళ్ళాడు",
                "deprel": "nsubj",
                "deprel_gloss": "Nominal subject",
            },
            {
                "id": 2,
                "text": "వెళ్ళాడు",
                "translit": "veḷḷāḍu",
                "upos": "VERB",
                "upos_name": "Verb",
                "head": 0,
                "head_text": "ROOT",
                "deprel": "root",
                "deprel_gloss": "Root predicate",
            },
        ],
        "token_count": 2,
        "main_verb": "వెళ్ళాడు",
        "subject": "రాము",
        "object": None,
        "word_order": "S-V",
        "pos_counts": {"PROPN": 1, "VERB": 1},
        "tree_tuple": ("S", ("VERB_P", ("PROPN", "రాము"), ("VERB", "వెళ్ళాడు"))),
        "bracket_words": "[S [PROPN రాము] [VERB వెళ్ళాడు]]",
        "bracket_pos": "(S (propn రాము) (verb వెళ్ళాడు))",
        "pcfg_eval": {"covered": False, "probability": None, "rules": []},
        "checks": [
            {
                "check_id": "verb_final",
                "name": "Verb in sentence-final position",
                "status": "consistent",
                "explanation": "Root verb appears at the end.",
                "badge": None,
            }
        ],
    }

    with patch("app.server.analyze_sentence", return_value=mock_res):
        # Force model_loaded to True for testing this endpoint
        orig_loaded = app.state.model_loaded
        orig_nlp = app.state.nlp
        app.state.model_loaded = True
        app.state.nlp = "mock_nlp"
        try:
            # Sentence with U+200C zero-width non-joiner
            dirty_input = "రాము\u200c వెళ్ళాడు"
            resp = client.post("/api/analyze", json={"sentence": dirty_input})
            assert resp.status_code == 200
            data = resp.json()
            assert data["input"]["original"] == dirty_input
            assert data["input"]["cleaned"] == "రాము వెళ్ళాడు"
            assert data["input"]["removed_hidden_chars"] is True
            assert any("Hidden characters" in note for note in data["notes"])
        finally:
            app.state.model_loaded = orig_loaded
            app.state.nlp = orig_nlp


def test_analyze_output_schema_shape(client):
    """Verify that /api/analyze conforms exactly to the required JSON schema."""
    mock_res = {
        "text": "నేను పుస్తకం చదివాను",
        "tokens": [
            {
                "id": 1,
                "text": "నేను",
                "translit": "nēnu",
                "upos": "PRON",
                "upos_name": "Pronoun",
                "head": 3,
                "head_text": "చదివాను",
                "deprel": "nsubj",
                "deprel_gloss": "Nominal subject",
            },
            {
                "id": 2,
                "text": "పుస్తకం",
                "translit": "pustakaṁ",
                "upos": "NOUN",
                "upos_name": "Noun",
                "head": 3,
                "head_text": "చదివాను",
                "deprel": "obj",
                "deprel_gloss": "Direct object",
            },
            {
                "id": 3,
                "text": "చదివాను",
                "translit": "cadivānu",
                "upos": "VERB",
                "upos_name": "Verb",
                "head": 0,
                "head_text": "ROOT",
                "deprel": "root",
                "deprel_gloss": "Root predicate",
            },
        ],
        "token_count": 3,
        "main_verb": "చదివాను",
        "subject": "నేను",
        "object": "పుస్తకం",
        "word_order": "S-O-V",
        "pos_counts": {"PRON": 1, "NOUN": 1, "VERB": 1},
        "tree_tuple": None,
        "bracket_words": "[S [PRON నేను] [NOUN పుస్తకం] [VERB చదివాను]]",
        "bracket_pos": None,
        "pcfg_eval": {
            "covered": True,
            "probability": 0.05,
            "rules": ["S -> NP_P VP_P [0.5]", "VP_P -> VERB [1.0]"],
        },
        "checks": [
            {
                "check_id": "verb_final",
                "name": "Verb in sentence-final position",
                "status": "consistent",
                "explanation": "Root verb appears at the end.",
                "badge": None,
            },
            {
                "check_id": "subject_verb_agreement",
                "name": "Subject-verb agreement (experimental)",
                "status": "consistent",
                "explanation": "1sg pronoun matches -ాను ending.",
                "badge": "Experimental, unvalidated",
            },
        ],
    }

    with patch("app.server.analyze_sentence", return_value=mock_res):
        orig_loaded = app.state.model_loaded
        orig_nlp = app.state.nlp
        app.state.model_loaded = True
        app.state.nlp = "mock_nlp"
        try:
            resp = client.post("/api/analyze", json={"sentence": "నేను పుస్తకం చదివాను"})
            assert resp.status_code == 200
            data = resp.json()

            # Top-level keys
            for key in ["input", "tokens", "summary", "checks", "tree", "treebank_match", "notes"]:
                assert key in data

            # Tokens schema
            assert len(data["tokens"]) == 3
            tok0 = data["tokens"][0]
            for field in [
                "id", "word", "transliteration_iso15919", "upos", "upos_name",
                "head_id", "head_word", "deprel", "deprel_gloss", "possible_suffix"
            ]:
                assert field in tok0

            # Summary schema
            summary = data["summary"]
            assert summary["token_count"] == 3
            assert summary["subject"] == "నేను"
            assert summary["object"] == "పుస్తకం"
            assert summary["main_verb"] == "చదివాను"
            assert summary["word_order"] == "S-O-V"

            # Checks schema
            checks = data["checks"]
            assert len(checks) == 2
            assert checks[0]["key"] == "verb_final"
            assert checks[0]["experimental"] is False
            assert checks[1]["key"] == "subject_verb_agreement"
            assert checks[1]["experimental"] is True

            # Tree schema
            tree = data["tree"]
            assert tree["pcfg_covered"] is True
            assert tree["viterbi_prob"] == 0.05
            assert len(tree["productions"]) == 2
            assert tree["productions"][0]["rule"] == "S -> NP_P VP_P"
            assert tree["productions"][0]["prob"] == 0.5

            # Treebank match schema
            tm = data["treebank_match"]
            assert "found" in tm
            assert "split" in tm
            assert "gold" in tm
            assert "metrics" in tm
        finally:
            app.state.model_loaded = orig_loaded
            app.state.nlp = orig_nlp


def test_missing_model_returns_503(client):
    """When the Stanza model is not loaded, /api/analyze returns 503 with download command."""
    orig_loaded = app.state.model_loaded
    orig_nlp = app.state.nlp
    app.state.model_loaded = False
    app.state.nlp = None
    try:
        resp = client.post("/api/analyze", json={"sentence": "రాము వెళ్ళాడు"})
        assert resp.status_code == 503
        data = resp.json()
        assert "message" in data
        assert "stanza.download('te')" in data.get("download_command", "")
    finally:
        app.state.model_loaded = orig_loaded
        app.state.nlp = orig_nlp


def test_reliability_endpoint(client):
    """Test /api/reliability returns evaluation tables and reportability flags."""
    resp = client.get("/api/reliability")
    assert resp.status_code == 200
    data = resp.json()

    for sec in ["stanza_eval", "stanza_eval_details", "wordorder_results", "agreement_results", "datasize_curve", "findings"]:
        assert sec in data

    # Check findings
    assert "word_order" in data["findings"]
    assert "agreement" in data["findings"]

    # Check reportable flags
    assert "reportable" in data["wordorder_results"]
    assert "reportable" in data["agreement_results"]
    assert "reportable" in data["datasize_curve"]


def test_reliability_missing_file_handling():
    """Verify that _read_csv_as_json_records returns null and message for missing files."""
    from app.server import _read_csv_as_json_records
    records, msg = _read_csv_as_json_records("results/nonexistent_file_xyz.csv")
    assert records is None
    assert "not found" in msg.lower()


@pytest.mark.slow
def test_real_server_analysis_slow():
    """Live integration test: analyze a real Telugu sentence using Stanza."""
    from src.analyzer import load_stanza_pipeline
    with TestClient(app) as live_client:
        live_client.app.state.nlp = load_stanza_pipeline()
        live_client.app.state.model_loaded = True
        resp = live_client.post("/api/analyze", json={"sentence": "రాము ఇంట్లోకి వెళ్ళాడు"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["input"]["cleaned"] == "రాము ఇంట్లోకి వెళ్ళాడు"
        assert len(data["tokens"]) == 3
        # Check that root verb has ending -ాడు detected
        verb_tok = [t for t in data["tokens"] if t["word"] == "వెళ్ళాడు"][0]
        assert verb_tok["possible_suffix"] == "-ాడు"
        assert data["summary"]["word_order"] in ["S-V", "S-O-V", "N/A"]
