import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import stanza
from src.analyzer import analyze_sentence

sentences = [
    ("Sentence 1 (Brief target)", "రాము ఇంట్లోకి వెళ్ళాడు"),
    ("Sentence 2 (Treebank Dev 1)", "మనం ఎందుకు అన్నం తింటాం ?"),
    ("Sentence 3 (Treebank Dev 2)", "నువ్వు పని చెయ్యాలి ."),
    ("Sentence 4 (Pronoun subject)", "నేను పుస్తకం చదివాను ."),
    ("Sentence 5 (Postposition)", "అతను బల్ల మీద పుస్తకం ఉంచాడు ."),
    ("Sentence 6 (8+ words, Dev treebank)", "రాము నేను రేపు వెళ్తాను అని కమలతో చెప్పేడు ."),
]

for label, sent in sentences:
    print("=" * 75)
    print(f"{label}: {sent}")
    res = analyze_sentence(sent)
    full_iso = " ".join(t["translit"] for t in res["tokens"])
    print(f"ISO 15919: {full_iso}")
    print(f"Summary: Subj={res['subject']} | Obj={res['object']} | RootVerb={res['main_verb']} | Order={res['word_order']}")
    print(f"Phrase tree: {res['bracket_words']}")
    print("Tokens:")
    for t in res["tokens"]:
        print(f"  {t['id']:2d} | {t['text']:12s} | {t['translit']:16s} | {t['upos']:6s} | head={t['head']:2d} ({t['head_text']:10s}) | {t['deprel']:10s} | {t['deprel_gloss']}")
    print("Checks:")
    for c in res["checks"]:
        print(f"  * {c['name']}: {c['status']} -> {c['explanation']}")
