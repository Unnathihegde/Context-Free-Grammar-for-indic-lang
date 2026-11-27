"""Analyzer module orchestrating Stanza dependency parsing, ISO 15919 transliteration,
PCFG phrase-structure derivation, and syntactic pattern checks for Telugu.
"""

from typing import Any, Dict, List, Optional, Tuple
import os
import sys

from indic_transliteration import sanscript
from nltk.parse import ViterbiParser
import stanza

from src.checks import run_all_checks
from src.glossary import get_deprel_gloss, get_upos_name
from src.grammar_learn import drop_punct, induce, load_all, prepare, to_tree


class ModelNotInstalledError(RuntimeError):
    """Raised when Stanza's Telugu model is not installed locally."""
    pass


_CACHED_NLP = None
_CACHED_PCFG = None
_CACHED_PARSER = None


def get_default_model_dir() -> Optional[str]:
    """Retrieve Stanza's default model cache directory."""
    return getattr(stanza.resources.common, "DEFAULT_MODEL_DIR", None)


def load_stanza_pipeline(dirpath: Optional[str] = None) -> stanza.Pipeline:
    """Load Stanza Telugu pipeline with tokenize, pos, identity lemma, and depparse."""
    global _CACHED_NLP
    if _CACHED_NLP is not None:
        return _CACHED_NLP

    target_dir = dirpath or get_default_model_dir()

    try:
        nlp = stanza.Pipeline(
            "te",
            dir=target_dir,
            processors="tokenize,pos,lemma,depparse",
            download_method=None,
            verbose=False,
        )
        _CACHED_NLP = nlp
        return nlp
    except Exception as exc:
        raise ModelNotInstalledError(
            "Stanza Telugu model is not installed or resources.json is missing.\n"
            "Please install the model by running:\n"
            '    python -c "import stanza; stanza.download(\'te\')"'
        ) from exc


def load_pcfg_parser() -> Tuple[Any, Any]:
    """Induce and cache PCFG grammar and Viterbi parser from treebank data."""
    global _CACHED_PCFG, _CACHED_PARSER
    if _CACHED_PCFG is not None and _CACHED_PARSER is not None:
        return _CACHED_PCFG, _CACHED_PARSER

    try:
        trees, _ = prepare(load_all())
        pcfg = induce(trees)
        parser = ViterbiParser(pcfg)
        _CACHED_PCFG = pcfg
        _CACHED_PARSER = parser
        return pcfg, parser
    except Exception as e:
        print(f"Warning: could not induce PCFG: {e}", file=sys.stderr)
        return None, None


def transliterate_to_iso(text: str) -> str:
    """Transliterate Telugu script to ISO 15919 romanization."""
    if not text:
        return ""
    try:
        return sanscript.transliterate(text, sanscript.TELUGU, sanscript.ISO)
    except Exception:
        return text


def detect_word_order(
    subj_token: Optional[Dict[str, Any]],
    obj_token: Optional[Dict[str, Any]],
    verb_token: Optional[Dict[str, Any]],
) -> str:
    """Detect constituent order (e.g. S-O-V, S-V, O-V) from token positions."""
    constituents = []
    if subj_token:
        constituents.append((subj_token.get("id", 0), "S"))
    if obj_token:
        constituents.append((obj_token.get("id", 0), "O"))
    if verb_token:
        constituents.append((verb_token.get("id", 0), "V"))

    if not constituents:
        return "N/A"

    constituents.sort(key=lambda x: x[0])
    return "-".join(c[1] for c in constituents)


def convert_dependency_to_phrase_tree(
    tokens: List[Dict[str, Any]]
) -> Tuple[Optional[Any], Optional[str], Optional[str]]:
    """Convert dependency parse to phrase-structure tree (word-level and POS-level).

    Returns:
        (tree_tuple_for_svgling, bracketed_words_str, bracketed_pos_str)
    """
    conllu_format = [
        {
            "id": t.get("id", i + 1),
            "word": t.get("text", ""),
            "pos": t.get("upos", "X"),
            "head": t.get("head", 0),
            "rel": t.get("deprel", "dep"),
        }
        for i, t in enumerate(tokens)
    ]

    filtered = drop_punct(conllu_format)
    if not filtered:
        return None, None, None

    # Build head-outward tree mapping
    roots = [t for t in filtered if t["head"] == 0]
    if len(roots) != 1:
        return None, None, None

    kids: Dict[int, List[int]] = {t["id"]: [] for t in filtered}
    for t in filtered:
        if t["head"] != 0 and t["head"] in kids:
            kids[t["head"]].append(t["id"])
    by_id = {t["id"]: t for t in filtered}

    def build_tuple(node_id: int) -> Tuple[Any, ...]:
        tok = by_id[node_id]
        pos = tok["pos"]
        word = tok["word"]
        leaf = (pos, word)
        left = [build_tuple(c) for c in sorted(kids[node_id]) if c < node_id]
        right = [build_tuple(c) for c in sorted(kids[node_id]) if c > node_id]
        if not left and not right:
            return leaf
        phrase_label = f"{pos}_P"
        return (phrase_label, *left, leaf, *right)

    def to_bracket_str(tup: Any) -> str:
        if isinstance(tup, tuple):
            label = tup[0]
            children_str = " ".join(to_bracket_str(c) for c in tup[1:])
            return f"[{label} {children_str}]"
        return str(tup)

    tree_tuple = ("S", build_tuple(roots[0]["id"]))
    bracket_words = to_bracket_str(tree_tuple)

    # Standard POS-level tree from grammar_learn.to_tree
    nltk_pos_tree = to_tree(filtered)
    bracket_pos = nltk_pos_tree.pformat(margin=1000) if nltk_pos_tree else None

    return tree_tuple, bracket_words, bracket_pos


def evaluate_pcfg_coverage(
    tokens: List[Dict[str, Any]], parser: Optional[ViterbiParser]
) -> Dict[str, Any]:
    """Test if predicted POS sequence is parseable by the learned treebank PCFG."""
    if parser is None:
        return {
            "covered": False,
            "probability": None,
            "rules": [],
            "message": "PCFG parser not loaded.",
        }

    non_punct = [t for t in tokens if t.get("upos") != "PUNCT"]
    pos_seq = [t.get("upos", "").lower() for t in non_punct]

    if not pos_seq:
        return {
            "covered": False,
            "probability": None,
            "rules": [],
            "message": "No non-punctuation tokens to parse.",
        }

    try:
        parses = list(parser.parse(pos_seq))
        if parses and parses[0].prob() > 0:
            best = parses[0]
            rules = [str(prod) for prod in best.productions()]
            return {
                "covered": True,
                "probability": best.prob(),
                "rules": rules,
                "message": "POS sequence successfully parsed by learned PCFG.",
            }
    except Exception:
        pass

    return {
        "covered": False,
        "probability": None,
        "rules": [],
        "message": "This POS sequence is not covered by the learned grammar (not an error).",
    }


def analyze_sentence(
    text: str,
    nlp: Optional[stanza.Pipeline] = None,
    parser: Optional[ViterbiParser] = None,
    agreement_rows: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Analyze a single Telugu sentence and return structured linguistic data."""
    clean_text = text.strip()
    if not clean_text:
        return {"error": "Input sentence is empty."}

    if nlp is None:
        nlp = load_stanza_pipeline()

    if parser is None:
        _, parser = load_pcfg_parser()

    # Parse sentence via Stanza
    doc = nlp(clean_text)
    if not doc.sentences:
        return {"error": "No sentences detected by the tokenizer."}

    # Focus on first sentence (brief specifies 1 sentence input)
    sent = doc.sentences[0]

    # Build token representation
    tokens: List[Dict[str, Any]] = []
    by_id: Dict[int, Dict[str, Any]] = {}

    for w in sent.words:
        token_data = {
            "id": w.id,
            "text": w.text,
            "translit": transliterate_to_iso(w.text),
            "upos": w.upos,
            "upos_name": get_upos_name(w.upos),
            "head": w.head,
            "head_text": "",
            "deprel": w.deprel,
            "deprel_gloss": get_deprel_gloss(w.deprel),
        }
        tokens.append(token_data)
        by_id[w.id] = token_data

    # Fill head_text
    for t in tokens:
        head_id = t["head"]
        if head_id == 0:
            t["head_text"] = "ROOT"
        elif head_id in by_id:
            t["head_text"] = by_id[head_id]["text"]
        else:
            t["head_text"] = f"[{head_id}]"

    # Summary constituent identification
    root_verbs = [t for t in tokens if (t["deprel"] == "root" or t["head"] == 0) and t["upos"] == "VERB"]
    nsubjs = [t for t in tokens if t["deprel"] == "nsubj"]
    objs = [t for t in tokens if t["deprel"] in {"obj", "iobj"}]

    main_verb = root_verbs[0] if root_verbs else None
    subject = nsubjs[0] if nsubjs else None
    obj = objs[0] if objs else None

    word_order = detect_word_order(subject, obj, main_verb)

    # POS counts
    pos_counts: Dict[str, int] = {}
    for t in tokens:
        pos_counts[t["upos"]] = pos_counts.get(t["upos"], 0) + 1

    # Phrase-structure tree
    tree_tuple, bracket_words, bracket_pos = convert_dependency_to_phrase_tree(tokens)

    # PCFG coverage
    pcfg_eval = evaluate_pcfg_coverage(tokens, parser)

    # Syntactic pattern checks
    checks = run_all_checks(tokens, agreement_rows=agreement_rows)

    return {
        "text": clean_text,
        "tokens": tokens,
        "token_count": len(tokens),
        "main_verb": main_verb["text"] if main_verb else None,
        "subject": subject["text"] if subject else None,
        "object": obj["text"] if obj else None,
        "word_order": word_order,
        "pos_counts": pos_counts,
        "tree_tuple": tree_tuple,
        "bracket_words": bracket_words,
        "bracket_pos": bracket_pos,
        "pcfg_eval": pcfg_eval,
        "checks": checks,
    }
