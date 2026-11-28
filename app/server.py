"""FastAPI backend server for Telugu Grammar Analyzer.

Provides REST API endpoints for automatic dependency parsing, PCFG phrase-structure
analysis, syntactic pattern checks, and empirical evaluation metrics. Serves the static
web interface from web/.
"""

from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
import asyncio
import os
import sys
import threading
import unicodedata

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
import stanza

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.agreement import (
    clean_for_matching,
    get_known_non_verbs,
    get_possible_verb_suffix,
    load_agreement_table,
)
from src.analyzer import (
    ModelNotInstalledError,
    analyze_sentence,
    load_pcfg_parser,
    load_stanza_pipeline,
)
from src.checks import load_train_treebank_vocab
from src.grammar_learn import read_conllu

ZERO_WIDTH_CHARS = str.maketrans("", "", "\u200b\u200c\u200d\ufeff")
STANZA_DOWNLOAD_CMD = 'python -c "import stanza; stanza.download(\'te\')"'

# Lock guarding Stanza's PyTorch pipeline across threads
nlp_lock = threading.Lock()


def load_treebank_examples(max_count: int = 40) -> List[str]:
    """Load example sentences dynamically from dev and test splits."""
    examples: List[str] = []
    seen = set()

    for fn in ("data/te_dev.conllu", "data/te_test.conllu"):
        fpath = os.path.join(PROJECT_ROOT, fn)
        if not os.path.exists(fpath):
            continue
        try:
            sents = read_conllu(fpath)
            for s in sents:
                text = " ".join(t["word"] for t in s).strip()
                if 3 <= len(s) <= 12 and text not in seen:
                    seen.add(text)
                    examples.append(text)
                    if len(examples) >= max_count:
                        return examples
        except Exception:
            pass

    return examples[:max_count]


def load_treebank_lookup_map() -> Dict[str, tuple[str, List[Dict[str, Any]]]]:
    """Build a lookup map of NFC-normalized sentence text to (split, tokens)."""
    lookup: Dict[str, tuple[str, List[Dict[str, Any]]]] = {}
    splits = [
        ("train", "data/te_train.conllu"),
        ("dev", "data/te_dev.conllu"),
        ("test", "data/te_test.conllu"),
    ]
    for split_name, rel_path in splits:
        fpath = os.path.join(PROJECT_ROOT, rel_path)
        if not os.path.exists(fpath):
            continue
        try:
            for s in read_conllu(fpath):
                norm_text = unicodedata.normalize("NFC", " ".join(t["word"] for t in s)).strip()
                if norm_text and norm_text not in lookup:
                    lookup[norm_text] = (split_name, s)
        except Exception:
            pass
    return lookup


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager: loads models, grammars, and lookup tables once at startup."""
    app.state.model_loaded = False
    app.state.model_error = None
    app.state.nlp = None
    app.state.parser = None
    app.state.pcfg = None

    # 1. Load Stanza Telugu pipeline
    try:
        app.state.nlp = load_stanza_pipeline()
        app.state.model_loaded = True
    except ModelNotInstalledError as exc:
        app.state.model_error = (
            f"Stanza Telugu model is not installed. Download command: {STANZA_DOWNLOAD_CMD}"
        )
    except Exception as exc:
        app.state.model_error = str(exc)

    # 2. Load PCFG grammar & parser
    app.state.pcfg_prob_map = {}
    try:
        pcfg, parser = load_pcfg_parser()
        app.state.pcfg = pcfg
        app.state.parser = parser
        if pcfg is not None:
            for prod in pcfg.productions():
                rhs_str = " ".join(
                    repr(s) if isinstance(s, str) else str(s) for s in prod.rhs()
                )
                app.state.pcfg_prob_map[f"{prod.lhs()} -> {rhs_str}"] = float(prod.prob())
    except Exception as exc:
        app.state.pcfg = None
        app.state.parser = None

    # 3. Load agreement table & known non-verbs
    try:
        app.state.agreement_table = load_agreement_table()
    except Exception:
        app.state.agreement_table = []

    try:
        app.state.known_non_verbs = get_known_non_verbs()
    except Exception:
        app.state.known_non_verbs = set()

    # 4. Load training treebank vocabulary
    try:
        app.state.train_vocab = load_train_treebank_vocab()
    except Exception:
        app.state.train_vocab = set()

    # 5. Load dynamic example sentences (max 40)
    app.state.examples = load_treebank_examples(max_count=40)

    # 6. Load treebank lookup index
    app.state.treebank_lookup = load_treebank_lookup_map()

    yield


app = FastAPI(
    title="Telugu Grammar Analyzer API",
    description="Automatic grammatical analysis for Telugu sentences",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/api/health")
async def get_health():
    """Health check endpoint indicating model readiness and environment info."""
    return {
        "status": "ok" if app.state.model_loaded else "degraded",
        "model_loaded": bool(app.state.model_loaded),
        "stanza_version": stanza.__version__,
        "model_error": app.state.model_error,
    }


@app.get("/api/examples")
async def get_examples():
    """Retrieve dynamic example sentences extracted from dev/test treebank splits."""
    return app.state.examples


@app.post("/api/analyze")
async def post_analyze(payload: Dict[str, Any] = Body(...)):
    """Analyze a single Telugu sentence and return structured linguistic data."""
    if not app.state.model_loaded or app.state.nlp is None:
        return JSONResponse(
            status_code=503,
            content={
                "message": (
                    "Stanza Telugu model is not installed or could not be loaded. "
                    f"Please install it using: {STANZA_DOWNLOAD_CMD}"
                ),
                "download_command": STANZA_DOWNLOAD_CMD,
            },
        )

    raw_sentence = payload.get("sentence", "")
    if not isinstance(raw_sentence, str):
        return JSONResponse(
            status_code=400,
            content={"message": "Input 'sentence' must be a string."},
        )

    # Input validation
    stripped = raw_sentence.strip()
    if not stripped:
        return JSONResponse(
            status_code=400,
            content={"message": "Input sentence cannot be empty."},
        )

    if len(raw_sentence) > 300:
        return JSONResponse(
            status_code=400,
            content={"message": "Input sentence exceeds the maximum allowed length of 300 characters."},
        )

    # Normalize unicode and strip hidden zero-width characters
    nfc_text = unicodedata.normalize("NFC", raw_sentence)
    cleaned_text = nfc_text.translate(ZERO_WIDTH_CHARS).strip()
    had_hidden = (nfc_text.strip() != cleaned_text)

    if not cleaned_text:
        return JSONResponse(
            status_code=400,
            content={"message": "Input sentence contains only whitespace or hidden characters."},
        )

    # Perform automatic analysis with thread lock
    def _sync_analysis(text: str) -> Dict[str, Any]:
        with nlp_lock:
            return analyze_sentence(
                text,
                nlp=app.state.nlp,
                parser=app.state.parser,
                agreement_rows=app.state.agreement_table,
            )

    try:
        raw_res = await asyncio.to_thread(_sync_analysis, cleaned_text)
    except Exception as exc:
        return JSONResponse(
            status_code=400,
            content={"message": f"Automatic analysis failed: {str(exc)}"},
        )

    if "error" in raw_res:
        return JSONResponse(
            status_code=400,
            content={"message": raw_res["error"]},
        )

    # Transform tokens to match API schema
    tokens: List[Dict[str, Any]] = []
    for t in raw_res.get("tokens", []):
        word_text = t.get("text", "")
        upos = t.get("upos", "")
        possible_suffix = get_possible_verb_suffix(
            word_text,
            upos=upos,
            agreement_rows=app.state.agreement_table,
            known_non_verbs=app.state.known_non_verbs,
        )
        tokens.append({
            "id": t.get("id"),
            "word": word_text,
            "transliteration_iso15919": t.get("translit", ""),
            "upos": upos,
            "upos_name": t.get("upos_name", ""),
            "head_id": t.get("head"),
            "head_word": t.get("head_text", ""),
            "deprel": t.get("deprel", ""),
            "deprel_gloss": t.get("deprel_gloss", ""),
            "possible_suffix": possible_suffix,
        })

    # Summary constituent structure
    summary = {
        "token_count": raw_res.get("token_count", len(tokens)),
        "subject": raw_res.get("subject"),
        "object": raw_res.get("object"),
        "main_verb": raw_res.get("main_verb"),
        "word_order": raw_res.get("word_order"),
    }

    # Syntactic pattern checks
    checks: List[Dict[str, Any]] = []
    for c in raw_res.get("checks", []):
        is_experimental = bool(
            c.get("badge") is not None or c.get("check_id") == "subject_verb_agreement"
        )
        checks.append({
            "key": c.get("check_id"),
            "label": c.get("name"),
            "status": c.get("status"),
            "explanation": c.get("explanation"),
            "experimental": is_experimental,
        })

    # Phrase-structure tree & PCFG productions
    pcfg_eval = raw_res.get("pcfg_eval", {})
    pcfg_prob_map = getattr(app.state, "pcfg_prob_map", {}) or {}
    productions: List[Dict[str, Any]] = []
    for rule_str in pcfg_eval.get("rules", []):
        if "[" in rule_str and rule_str.endswith("]"):
            base_rule, prob_part = rule_str.rsplit("[", 1)
            base_rule = base_rule.strip()
            try:
                p_val = float(prob_part.rstrip("] ").strip())
            except ValueError:
                p_val = None
            productions.append({"rule": base_rule, "prob": p_val})
        else:
            base_rule = rule_str.strip()
            if base_rule in pcfg_prob_map:
                productions.append({"rule": base_rule, "prob": pcfg_prob_map[base_rule]})
            else:
                productions.append({
                    "rule": base_rule,
                    "prob": None,
                    "reason": "Production not found in induced PCFG grammar.",
                })

    tree = {
        "bracketed": raw_res.get("bracket_words"),
        "productions": productions,
        "pcfg_covered": bool(pcfg_eval.get("covered", False)),
        "viterbi_prob": pcfg_eval.get("probability"),
    }

    # Treebank comparison
    norm_cleaned = unicodedata.normalize("NFC", cleaned_text).strip()
    match_entry = app.state.treebank_lookup.get(norm_cleaned)

    notes: List[str] = []
    if had_hidden:
        notes.append("Hidden characters (such as zero-width spaces or joiners) were removed before analysis.")

    if match_entry is not None:
        split_name, gold_sent = match_entry
        gold_tokens = [
            {
                "id": g["id"],
                "word": g["word"],
                "pos": g["pos"],
                "head": g["head"],
                "rel": g["rel"],
            }
            for g in gold_sent
        ]
        upos_matches = sum(
            1 for i, g in enumerate(gold_sent)
            if i < len(tokens) and tokens[i]["upos"] == g["pos"]
        )
        head_matches = sum(
            1 for i, g in enumerate(gold_sent)
            if i < len(tokens) and tokens[i]["head_id"] == g["head"]
        )
        las_matches = sum(
            1 for i, g in enumerate(gold_sent)
            if i < len(tokens)
            and tokens[i]["upos"] == g["pos"]
            and tokens[i]["head_id"] == g["head"]
            and tokens[i]["deprel"] == g["rel"]
        )
        total = len(gold_sent)
        metrics = {
            "total_tokens": total,
            "upos_matches": upos_matches,
            "head_matches": head_matches,
            "las_matches": las_matches,
            "upos_accuracy": round(upos_matches / total, 4) if total > 0 else 0.0,
            "uas": round(head_matches / total, 4) if total > 0 else 0.0,
            "las": round(las_matches / total, 4) if total > 0 else 0.0,
        }
        treebank_match = {
            "found": True,
            "split": split_name,
            "gold": gold_tokens,
            "metrics": metrics,
        }
        if split_name == "train":
            notes.append("This sentence was in the model's training data, so these scores do not measure accuracy.")
    else:
        treebank_match = {
            "found": False,
            "split": None,
            "gold": None,
            "metrics": None,
        }

    return {
        "input": {
            "original": raw_sentence,
            "cleaned": cleaned_text,
            "removed_hidden_chars": had_hidden,
        },
        "tokens": tokens,
        "summary": summary,
        "checks": checks,
        "tree": tree,
        "treebank_match": treebank_match,
        "notes": notes,
    }


import math


def _clean_val(val: Any) -> Any:
    if isinstance(val, float) and (math.isnan(val) or val != val):
        return None
    return val


def _read_csv_as_json_records(rel_path: str) -> tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """Helper to read a CSV file into JSON-serializable records."""
    fpath = os.path.join(PROJECT_ROOT, rel_path)
    if not os.path.exists(fpath):
        return None, f"File {rel_path} not found."
    try:
        df = pd.read_csv(fpath)
        records = [
            {k: _clean_val(v) for k, v in row.items()}
            for row in df.to_dict(orient="records")
        ]
        return records, None
    except Exception as exc:
        return None, f"Error reading {rel_path}: {str(exc)}"


@app.get("/api/reliability")
async def get_reliability():
    """Return model reliability evaluation results from results/*.csv."""
    stanza_eval_data, stanza_eval_msg = _read_csv_as_json_records("results/stanza_eval.csv")
    details_data, details_msg = _read_csv_as_json_records("results/stanza_eval_details.csv")
    wordorder_data, wordorder_msg = _read_csv_as_json_records("results/wordorder_results.csv")
    agreement_data, agreement_msg = _read_csv_as_json_records("results/agreement_results.csv")
    datasize_data, datasize_msg = _read_csv_as_json_records("results/datasize_curve.csv")

    # Word order reportability
    wo_reportable = bool(
        wordorder_data and all(r.get("reportable") is True for r in wordorder_data)
    )

    # Agreement reportability
    ag_reportable = bool(
        agreement_data and agreement_data[0].get("reportable") is True
    )
    ag_reason = agreement_data[0].get("reportability_reason") if agreement_data else None

    # Data size curve reportability
    ds_reportable = bool(
        datasize_data and datasize_data[0].get("reportable") is True
    )
    ds_reason = datasize_data[0].get("reportability_reason") if datasize_data else None

    return {
        "stanza_eval": {
            "data": stanza_eval_data,
            "message": stanza_eval_msg,
        },
        "stanza_eval_details": {
            "data": details_data,
            "message": details_msg,
        },
        "wordorder_results": {
            "data": wordorder_data,
            "reportable": wo_reportable,
            "message": wordorder_msg,
        },
        "agreement_results": {
            "data": agreement_data,
            "reportable": ag_reportable,
            "reportability_reason": ag_reason,
            "message": agreement_msg,
        },
        "datasize_curve": {
            "data": datasize_data,
            "reportable": ds_reportable,
            "reportability_reason": ds_reason,
            "message": datasize_msg,
        },
        "findings": {
            "word_order": (
                "The learned POS-level PCFG did not outperform a simple POS-bigram baseline "
                "overall on word-order pairs (0.944 vs 0.967; paired bootstrap p <= 0.002). "
                "A context-free grammar does not improve discrimination over the baseline."
            ),
            "agreement": (
                "Experimental, unvalidated. The subject-verb agreement table was inducted "
                "heuristically and has not completed double-annotated native speaker validation. "
                "Results are presented for exploratory purposes only."
            ),
        },
    }


def _extract_limitations_caveats() -> Dict[str, Optional[str]]:
    """Read caveat sections directly from docs/limitations.md (never hard-coded)."""
    fpath = os.path.join(PROJECT_ROOT, "docs", "limitations.md")
    result: Dict[str, Optional[str]] = {
        "pretraining_leakage": None,
        "multiple_comparisons": None,
        "small_tag_counts": None,
        "muril_rare_tags": None,
    }
    if not os.path.exists(fpath):
        return result

    with open(fpath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    sections: Dict[str, List[str]] = {}
    current_key: Optional[str] = None
    heading_map = {
        "### 5.1": "pretraining_leakage",
        "### 5.2": "multiple_comparisons",
        "### 5.3": "small_tag_counts",
        "### 5.4": "muril_rare_tags",
    }

    for line in lines:
        stripped = line.strip()
        matched_heading = False
        for prefix, key in heading_map.items():
            if stripped.startswith(prefix):
                current_key = key
                sections[current_key] = []
                matched_heading = True
                break
        if matched_heading:
            continue
        if stripped.startswith("## ") or stripped.startswith("### ") or stripped == "---":
            current_key = None
            continue
        if current_key is not None and stripped:
            # Strip leading markdown bullet "- " for clean display text
            clean_line = stripped[2:].strip() if stripped.startswith("- ") else stripped
            sections[current_key].append(clean_line)

    for key, text_lines in sections.items():
        if text_lines:
            result[key] = " ".join(text_lines)
    return result


@app.get("/api/models")
async def get_models():
    """Return model comparison rows from results/model_comparison.csv and caveats from docs/limitations.md."""
    rows, msg = _read_csv_as_json_records("results/model_comparison.csv")
    caveats = _extract_limitations_caveats()
    return {
        "rows": rows,
        "message": msg,
        "caveats": caveats,
    }


# Mount static files for the web front end (declared after API routes)
WEB_DIR = os.path.join(PROJECT_ROOT, "web")
if os.path.exists(WEB_DIR):
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="static")
