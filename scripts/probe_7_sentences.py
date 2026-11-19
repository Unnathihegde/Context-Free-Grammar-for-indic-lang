"""Probe 7 everyday Telugu sentences through the real Stanza pipeline and syntactic checks."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.analyzer import analyze_sentence

test_sentences = [
    "నేను రేపు ఇంటికి వెళ్తాను",
    "ఆమె పుస్తకం చదివింది",
    "వారు బడికి వెళ్ళారు",
    "అతను అన్నం తిన్నాడు",
    "మేము సినిమా చూశాము",
    "పిల్లలు ఆడుకుంటున్నారు",
    "నువ్వు ఎక్కడికి వెళ్తున్నావు ?",
]

for idx, sent in enumerate(test_sentences, 1):
    print("=" * 80)
    print(f"SENTENCE {idx}: {sent}")
    print("=" * 80)
    res = analyze_sentence(sent)
    tokens = res["tokens"]
    full_iso = " ".join(t["translit"] for t in tokens)
    print(f"ISO 15919: {full_iso}")
    print(f"Summary: Subject={res['subject']} | Object={res['object']} | MainVerb={res['main_verb']} | Order={res['word_order']}")
    print(f"Phrase tree: {res['bracket_words']}")
    print("\nTokens:")
    for t in tokens:
        print(f"  {t['id']:2d} | {t['text']:14s} | {t['translit']:16s} | {t['upos']:6s} | head={t['head']:2d} ({t['head_text']:10s}) | {t['deprel']:10s} | {t['deprel_gloss']}")

    print("\nChecks:")
    for c in res["checks"]:
        print(f"  * {c['name']:40s}: {c['status']:15s} -> {c['explanation']}")
    print()
