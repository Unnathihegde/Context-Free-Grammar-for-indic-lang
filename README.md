# Context-Free Grammar for Indic–Dravidian Languages

Telugu case study: a probabilistic context-free grammar (PCFG), induced from the
UD Telugu-MTG treebank, is evaluated alongside simple language-model baselines.

## Setup

```bash
python -m venv .venv
# Windows PowerShell
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

The UD Telugu-MTG `.conllu` splits belong in `data/`. Do not commit a language
model corpus: place it at `data/raw/telugu_corpus.txt`, one sentence per line.

## Current commands

```bash
python src/grammar_learn.py
python src/pairs_eval.py
```

## Data and licensing

The UD Telugu-MTG licensing text has been reported inconsistently as CC BY-SA
4.0 and CC BY-NC-SA 3.0. Confirm the applicable license with the dataset source
before redistribution.

## Project status

The initial PCFG and word-order evaluation code is in place. Agreement resources,
the word-level language model, hybrid scoring, app, and full documentation will be
added task by task. Agreement candidates remain unvalidated until reviewed by a
Telugu speaker.
