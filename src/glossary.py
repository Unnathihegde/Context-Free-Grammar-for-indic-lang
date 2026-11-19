"""Glossary of Universal Dependencies (UD) Part-of-Speech tags and syntactic relations.

Provides human-readable names, plain-English glosses, and UI color palettes.
"""

from typing import Dict, Tuple

UPOS_NAMES: Dict[str, str] = {
    "ADJ": "Adjective",
    "ADP": "Adposition / Postposition",
    "ADV": "Adverb",
    "AUX": "Auxiliary Verb",
    "CCONJ": "Coordinating Conjunction",
    "DET": "Determiner",
    "INTJ": "Interjection",
    "NOUN": "Noun",
    "NUM": "Numeral",
    "PART": "Particle",
    "PRON": "Pronoun",
    "PROPN": "Proper Noun",
    "PUNCT": "Punctuation",
    "SCONJ": "Subordinating Conjunction",
    "SYM": "Symbol",
    "VERB": "Verb",
    "X": "Other / Unknown",
}

DEPREL_GLOSSES: Dict[str, str] = {
    "root": "Root predicate of sentence",
    "nsubj": "Nominal subject",
    "obj": "Direct object",
    "iobj": "Indirect object",
    "obl": "Oblique argument / circumstantial modifier",
    "obl:tmod": "Temporal oblique modifier",
    "amod": "Adjectival modifier",
    "det": "Determiner",
    "case": "Case marker / postposition",
    "compound": "Compound noun / modifier",
    "compound:lvc": "Light verb compound",
    "compound:svc": "Serial verb compound",
    "mark": "Subordinator / marker",
    "cc": "Coordinating conjunction",
    "conj": "Conjunct in coordination",
    "advmod": "Adverbial modifier",
    "punct": "Punctuation mark",
    "dep": "Unspecified dependency",
    "vocative": "Vocative noun",
    "discourse": "Discourse marker",
    "nummod": "Numeric modifier",
    "acl": "Adnominal clause modifier",
    "advcl": "Adverbial clause modifier",
    "xcomp": "Open clausal complement",
    "ccomp": "Clausal complement",
    "parataxis": "Parataxis (parenthetical / side clause)",
}

# Color palette: (background_hex, text_hex)
UPOS_COLORS: Dict[str, Tuple[str, str]] = {
    "NOUN": ("#E0F2FE", "#0369A1"),
    "VERB": ("#FEE2E2", "#B91C1C"),
    "PROPN": ("#EDE9FE", "#6D28D9"),
    "PRON": ("#FEF3C7", "#B45309"),
    "ADJ": ("#DCFCE7", "#15803D"),
    "ADV": ("#FCE7F3", "#BE185D"),
    "ADP": ("#E0E7FF", "#4338CA"),
    "DET": ("#CFFAFE", "#0E7490"),
    "NUM": ("#FEF9C3", "#A16207"),
    "PART": ("#F3E8FF", "#7E22CE"),
    "CCONJ": ("#F1F5F9", "#475569"),
    "SCONJ": ("#F1F5F9", "#475569"),
    "PUNCT": ("#F4F4F5", "#71717A"),
    "AUX": ("#FFEDD5", "#C2410C"),
    "INTJ": ("#E0E7FF", "#3730A3"),
    "SYM": ("#F3F4F6", "#374151"),
    "X": ("#F3F4F6", "#4B5563"),
}


def get_upos_name(tag: str) -> str:
    """Return full human-readable name for a UPOS tag."""
    return UPOS_NAMES.get(tag, tag or "Unknown")


def get_deprel_gloss(rel: str) -> str:
    """Return plain-English explanation for a UD dependency relation."""
    if rel in DEPREL_GLOSSES:
        return DEPREL_GLOSSES[rel]
    # Check base relation before colon (e.g. obl:tmod -> obl)
    base = rel.split(":")[0] if ":" in rel else rel
    return DEPREL_GLOSSES.get(base, f"Syntactic relation: {rel}")


def get_upos_color(tag: str) -> Tuple[str, str]:
    """Return (bg_color, text_color) tuple for a given UPOS tag."""
    return UPOS_COLORS.get(tag, ("#F3F4F6", "#374151"))
