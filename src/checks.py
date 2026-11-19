"""Syntactic pattern checks for Telugu sentences based on automatic parses.

Evaluates word order, head-modifier relations, and agreement heuristics.
Each check returns a status ("consistent", "not consistent", "not applicable")
and a neutral, objective explanation.
"""

from typing import Any, Dict, List, Optional
import os

from src.agreement import (
    clean_for_matching,
    ending_forms,
    get_known_non_verbs,
    load_agreement_table,
)

_TABLE_CACHE = None


def get_cached_agreement_table():
    global _TABLE_CACHE
    if _TABLE_CACHE is None:
        try:
            _TABLE_CACHE = load_agreement_table()
        except Exception:
            _TABLE_CACHE = []
    return _TABLE_CACHE


def check_verb_final(tokens: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Check if the root verb appears in sentence-final position (ignoring punctuation)."""
    if not tokens:
        return {
            "check_id": "verb_final",
            "name": "Verb in sentence-final position",
            "status": "not applicable",
            "explanation": "Sentence contains no tokens.",
            "badge": None,
        }

    # Non-punctuation tokens
    non_punct = [t for t in tokens if t.get("upos") != "PUNCT"]
    if not non_punct:
        return {
            "check_id": "verb_final",
            "name": "Verb in sentence-final position",
            "status": "not applicable",
            "explanation": "Sentence contains only punctuation.",
            "badge": None,
        }

    # Find root token(s)
    roots = [t for t in non_punct if t.get("deprel") == "root" or t.get("head") == 0]
    if not roots:
        return {
            "check_id": "verb_final",
            "name": "Verb in sentence-final position",
            "status": "not applicable",
            "explanation": "No root predicate detected.",
            "badge": None,
        }

    root = roots[0]
    if root.get("upos") != "VERB":
        return {
            "check_id": "verb_final",
            "name": "Verb in sentence-final position",
            "status": "not applicable",
            "explanation": f"Root predicate '{root.get('text')}' is tagged as {root.get('upos')} rather than VERB (e.g. nominal predicate).",
            "badge": None,
        }

    last_token = non_punct[-1]
    if root.get("id") == last_token.get("id"):
        return {
            "check_id": "verb_final",
            "name": "Verb in sentence-final position",
            "status": "consistent",
            "explanation": f"Root verb '{root.get('text')}' appears in sentence-final position (SOV pattern).",
            "badge": None,
        }
    else:
        root_idx = non_punct.index(root) + 1
        return {
            "check_id": "verb_final",
            "name": "Verb in sentence-final position",
            "status": "not consistent",
            "explanation": f"Root verb '{root.get('text')}' is at position {root_idx} of {len(non_punct)}, followed by non-punctuation dependents.",
            "badge": None,
        }


def check_det_before_noun(tokens: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Check if determiners precede their head nouns."""
    dets = [t for t in tokens if t.get("deprel") == "det"]
    if not dets:
        return {
            "check_id": "det_before_noun",
            "name": "Determiners before head noun",
            "status": "not applicable",
            "explanation": "No determiners (det) found in the parse.",
            "badge": None,
        }

    violating = [d for d in dets if d.get("head", 0) > 0 and d.get("id", 0) > d.get("head", 0)]
    if not violating:
        return {
            "check_id": "det_before_noun",
            "name": "Determiners before head noun",
            "status": "consistent",
            "explanation": f"All {len(dets)} determiner(s) precede their head noun.",
            "badge": None,
        }
    else:
        examples = ", ".join(f"'{d.get('text')}' (after head)" for d in violating)
        return {
            "check_id": "det_before_noun",
            "name": "Determiners before head noun",
            "status": "not consistent",
            "explanation": f"Determiner(s) appearing after head noun: {examples}.",
            "badge": None,
        }


def check_amod_before_noun(tokens: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Check if adjectival modifiers precede their head nouns."""
    amods = [t for t in tokens if t.get("deprel") == "amod"]
    if not amods:
        return {
            "check_id": "amod_before_noun",
            "name": "Adjectives before head noun",
            "status": "not applicable",
            "explanation": "No adjectival modifiers (amod) found in the parse.",
            "badge": None,
        }

    violating = [a for a in amods if a.get("head", 0) > 0 and a.get("id", 0) > a.get("head", 0)]
    if not violating:
        return {
            "check_id": "amod_before_noun",
            "name": "Adjectives before head noun",
            "status": "consistent",
            "explanation": f"All {len(amods)} adjective modifier(s) precede their head noun.",
            "badge": None,
        }
    else:
        examples = ", ".join(f"'{a.get('text')}' (after head)" for a in violating)
        return {
            "check_id": "amod_before_noun",
            "name": "Adjectives before head noun",
            "status": "not consistent",
            "explanation": f"Adjective modifier(s) appearing after head noun: {examples}.",
            "badge": None,
        }


def check_case_after_noun(tokens: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Check if postpositions/case markers follow their head nouns."""
    cases = [t for t in tokens if t.get("deprel") == "case" or t.get("upos") == "ADP"]
    if not cases:
        return {
            "check_id": "case_after_noun",
            "name": "Postpositions after head noun",
            "status": "not applicable",
            "explanation": "No postpositions or case markers found in the parse.",
            "badge": None,
        }

    violating = [c for c in cases if c.get("head", 0) > 0 and c.get("id", 0) < c.get("head", 0)]
    if not violating:
        return {
            "check_id": "case_after_noun",
            "name": "Postpositions after head noun",
            "status": "consistent",
            "explanation": f"All {len(cases)} postposition(s)/case marker(s) follow their head noun.",
            "badge": None,
        }
    else:
        examples = ", ".join(f"'{c.get('text')}' (before head)" for c in violating)
        return {
            "check_id": "case_after_noun",
            "name": "Postpositions after head noun",
            "status": "not consistent",
            "explanation": f"Postposition(s) appearing before head noun: {examples}.",
            "badge": None,
        }


def is_gender_compatible(g1: str, g2: str) -> bool:
    """Check if two gender annotations are compatible. Empty matches any."""
    if not g1 or not g2:
        return True
    g1_set = set(g1.split("/"))
    g2_set = set(g2.split("/"))
    return bool(g1_set.intersection(g2_set))


def check_subject_verb_agreement(
    tokens: List[Dict[str, Any]],
    agreement_rows: Optional[List[Dict[str, str]]] = None,
    known_non_verbs: Optional[set] = None,
) -> Dict[str, Any]:
    """Check subject-verb agreement against the unvalidated agreement table.

    Compares person, number, and gender (where annotated, e.g. 3sg masculine vs feminine/neuter).
    """
    badge = "EXPERIMENTAL, UNVALIDATED"

    if agreement_rows is None:
        agreement_rows = get_cached_agreement_table()

    if known_non_verbs is None:
        known_non_verbs = get_known_non_verbs()

    pronoun_map: Dict[str, List[Dict[str, str]]] = {}
    ending_rows: List[Dict[str, str]] = []
    for r in agreement_rows:
        if r["type"] == "pronoun":
            pronoun_map.setdefault(clean_for_matching(r["form"]), []).append(r)
        elif r["type"] == "verb_ending":
            ending_rows.append(r)

    by_id = {t.get("id"): t for t in tokens}
    nsubjs = [t for t in tokens if t.get("deprel") == "nsubj"]

    if not nsubjs:
        return {
            "check_id": "subject_verb_agreement",
            "name": "Subject-verb agreement",
            "status": "not applicable",
            "explanation": "No nominal subject (nsubj) found in the parse.",
            "badge": badge,
        }

    for subj in nsubjs:
        subj_text = subj.get("text", "")
        clean_subj = clean_for_matching(subj_text)

        if clean_subj not in pronoun_map:
            return {
                "check_id": "subject_verb_agreement",
                "name": "Subject-verb agreement",
                "status": "not applicable",
                "explanation": f"Subject '{subj_text}' is not a personal pronoun in the pronoun table (e.g. noun/proper name); rule abstains.",
                "badge": badge,
            }

        # Subject is a known pronoun
        subj_entries = pronoun_map[clean_subj]
        head_id = subj.get("head")
        verb = by_id.get(head_id)

        if not verb or verb.get("upos") != "VERB":
            return {
                "check_id": "subject_verb_agreement",
                "name": "Subject-verb agreement",
                "status": "not applicable",
                "explanation": f"Subject '{subj_text}' does not attach to a VERB head (head is {verb.get('upos') if verb else 'missing'}).",
                "badge": badge,
            }

        verb_text = verb.get("text", "")
        matched_endings = ending_forms(verb_text, ending_rows, known_non_verbs)
        if not matched_endings:
            return {
                "check_id": "subject_verb_agreement",
                "name": "Subject-verb agreement",
                "status": "not applicable",
                "explanation": f"Verb '{verb_text}' ending is not recognized in the agreement table.",
                "badge": badge,
            }

        # Look up ending entries for matched ending forms
        matched_ending_entries = [
            e for e in ending_rows if clean_for_matching(e["form"]) in [clean_for_matching(m) for m in matched_endings]
        ]

        # Check compatibility across person, number, and gender
        matching_pairs = []
        for se in subj_entries:
            for ve in matched_ending_entries:
                p_match = (se.get("person") == ve.get("person"))
                n_match = (se.get("number") == ve.get("number"))
                g_match = is_gender_compatible(se.get("gender", ""), ve.get("gender", ""))
                if p_match and n_match and g_match:
                    matching_pairs.append((se, ve))

        best_match = matched_endings[0]
        if matching_pairs:
            se, ve = matching_pairs[0]
            g_str = f", gender: {se.get('gender')}" if se.get("gender") else ""
            desc = f"{se.get('person')}/{se.get('number')}{g_str}"
            return {
                "check_id": "subject_verb_agreement",
                "name": "Subject-verb agreement",
                "status": "consistent",
                "explanation": f"Subject '{subj_text}' agrees with verb '{verb_text}' (ending -{best_match}, {desc}).",
                "badge": badge,
            }
        else:
            # Check if person/number matched but gender failed
            pn_matched = any(
                se.get("person") == ve.get("person") and se.get("number") == ve.get("number")
                for se in subj_entries for ve in matched_ending_entries
            )
            subj_desc = "/".join(
                f"{e.get('person')} {e.get('number')}" + (f" ({e.get('gender')})" if e.get("gender") else "")
                for e in subj_entries
            )
            verb_desc = "/".join(
                f"{e.get('person')} {e.get('number')}" + (f" ({e.get('gender')})" if e.get("gender") else "")
                for e in matched_ending_entries
            )
            if pn_matched:
                reason = "due to gender mismatch"
            else:
                reason = "person/number mismatch"
            return {
                "check_id": "subject_verb_agreement",
                "name": "Subject-verb agreement",
                "status": "not consistent",
                "explanation": f"Subject '{subj_text}' ({subj_desc}) does not match verb ending -{best_match} ({verb_desc}) [{reason}].",
                "badge": badge,
            }

    return {
        "check_id": "subject_verb_agreement",
        "name": "Subject-verb agreement",
        "status": "not applicable",
        "explanation": "No applicable subject-verb pair.",
        "badge": badge,
    }


_TRAIN_TREEBANK_VOCAB = None


def load_train_treebank_vocab(path: str = "data/te_train.conllu") -> set:
    """Build vocabulary set of words seen in data/te_train.conllu (excluding PUNCT)."""
    global _TRAIN_TREEBANK_VOCAB
    if _TRAIN_TREEBANK_VOCAB is not None:
        return _TRAIN_TREEBANK_VOCAB
    vocab = set()
    if os.path.exists(path):
        try:
            from src.grammar_learn import read_conllu
            for s in read_conllu(path):
                for t in s:
                    if t.get("pos") != "PUNCT":
                        vocab.add(clean_for_matching(t["word"]))
        except Exception:
            pass
    _TRAIN_TREEBANK_VOCAB = vocab
    return vocab


def check_unseen_training_tokens(
    tokens: List[Dict[str, Any]],
    train_vocab: Optional[set] = None,
) -> Dict[str, Any]:
    """Check for words not seen in the training treebank (data/te_train.conllu)."""
    if train_vocab is None:
        train_vocab = load_train_treebank_vocab()

    unseen = []
    for t in tokens:
        if t.get("upos") != "PUNCT":
            clean_w = clean_for_matching(t.get("text", ""))
            if clean_w not in train_vocab:
                unseen.append(t.get("text", ""))

    if not unseen:
        return {
            "check_id": "unseen_training_tokens",
            "name": "Words not seen in the training treebank",
            "status": "none unseen",
            "explanation": "All words in this sentence were observed in the UD Telugu-MTG training treebank.",
            "badge": None,
        }
    else:
        unique_unseen = list(dict.fromkeys(unseen))
        return {
            "check_id": "unseen_training_tokens",
            "name": "Words not seen in the training treebank",
            "status": "some unseen",
            "explanation": f"Words not seen in training treebank (UNKNOWN to the model): {', '.join(unique_unseen)}.",
            "badge": None,
        }


def run_all_checks(
    tokens: List[Dict[str, Any]],
    agreement_rows: Optional[List[Dict[str, str]]] = None,
    train_vocab: Optional[set] = None,
) -> List[Dict[str, Any]]:
    """Run all grammatical pattern checks on the sentence tokens."""
    return [
        check_verb_final(tokens),
        check_det_before_noun(tokens),
        check_amod_before_noun(tokens),
        check_case_after_noun(tokens),
        check_subject_verb_agreement(tokens, agreement_rows=agreement_rows),
        check_unseen_training_tokens(tokens, train_vocab=train_vocab),
    ]
