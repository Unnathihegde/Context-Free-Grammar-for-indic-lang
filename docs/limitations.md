# Project Limitations

This document candidly outlines the methodological, data, and linguistic limitations of the Telugu PCFG and hybrid language modeling study.

---

## 1. Treebank Limitations

### 1.1 Tiny Treebank Size
The Universal Dependencies Telugu-MTG treebank is exceptionally small:
- Total sentences: **1,328** (6,465 tokens; 1,326 usable after removing multi-root and non-projective trees).
- Average sentence length: **~4.9 tokens**.
- For comparison, major UD treebanks (e.g., English, German, Hindi) contain tens of thousands of sentences. Inducing grammars from approximately 6,000 tokens yields high variance and sparse rule coverage for complex constructions.

### 1.2 Textbook / Pedagogical Domain
The sentences in Telugu-MTG stem primarily from pedagogical grammar examples and introductory instructional material. They exhibit:
- Repetitive lexical choices and syntactic patterns.
- Absence of colloquial idioms, dialectal variations, or compound sentence embeddings common in natural discourse.
- Minimal structural ambiguity.

### 1.3 Empty Morphological Features
In the Telugu-MTG treebank, the `LEMMA` and `FEATS` columns are entirely unpopulated (`_`). Consequently:
- Morphological agreement features (gender, number, person, case) cannot be induced directly from the treebank annotations.
- The induced PCFG operates exclusively over coarse Universal POS (UPOS) tags.

---

## 2. Grammar & Representation Constraints

### 2.1 Permissive POS-Level PCFG
Because the PCFG rules are induced over coarse POS tags (e.g., `NOUN`, `VERB`, `PRON`), the grammar:
- Yields a high held-out parse coverage of **96.4%** (1,278 / 1,326 sentences).
- Is overly permissive: it accepts many syntactically illicit word combinations as long as the POS sequence roughly mirrors known patterns.
- Lacks lexicalization, meaning it cannot detect selectional restriction violations or semantic anomalies.

### 2.2 Approximate Dependency-to-Phrase Conversion
- The head-outward conversion heuristic maps dependency arcs into projective phrase structures (`X_P -> left_dependents + X + right_dependents`).
- This projection is a structural approximation. Non-projective dependency relations cannot be natively represented in standard context-free trees and are discarded.

---

## 3. Linguistic & Modeling Findings

### 3.1 Head-Final Order is a Local Pattern
- Telugu is canonically a head-final, SOV language with postpositions.
- Canonical word order constraints (e.g., verbs appearing sentence-finally, determiners preceding nouns, case markers following nominal stems) are largely **local bigram transitions**.
- In experimental evaluations on 1,118 minimal pairs, a simple **add-$k$ smoothed POS-bigram model outperformed the hierarchical PCFG** (0.967 overall accuracy for POS-bigram vs. 0.944 for PCFG, $p \le 0.002$ (smallest value resolvable with 1,000 bootstrap resamples)).
- While the PCFG showed higher nominal accuracy on the `case_before` perturbation subset (0.821 for PCFG vs. 0.696 for POS-bigram across 56 pairs), this difference is not statistically significant ($p = 0.058$).
- **Conclusion**: Context-free hierarchical grammar is unneeded for capturing local canonical order in small Telugu sentences; local n-gram transitions already encode head-final tendencies effectively.

### 3.2 Imbalanced Perturbation Types
The distribution of minimal pairs across perturbation categories is heavily skewed:
- `verb_first`: **853 pairs (76.3%)**
- `det_after`: **140 pairs (12.5%)**
- `amod_after`: **69 pairs (6.2%)**
- `case_before`: **56 pairs (5.0%)**

Because `verb_first` dominates, aggregate metrics primarily reflect the model's ability to penalize sentence-initial verbs. Small sample sizes in `case_before` (56 pairs) and `amod_after` (69 pairs) limit statistical confidence for those specific linguistic phenomena.

### 3.3 Non-Independent Pair Observations
Multiple minimal pairs are frequently derived from a single sentence. Because perturbations from the same sentence share lexical and syntactic context, they violate the assumption of independent and identically distributed (i.i.d.) observations. Cluster-bootstrapping by sentence is required to avoid severely deflating error margins.

---

## 4. Agreement & Language Modeling Caveats

### 4.1 Unvalidated Candidate Agreement Table
- `data/agreement/agreement_table.csv` and the resulting 293 candidate pairs were derived heuristically.
- Telugu verbal morphology involves complex sandhi rules, tense-aspect-mood (TAM) markers, and honorific plural distinctions.
- These rules **have not yet been vetted by a native Telugu speaker**. Until a Telugu speaker validates them, all agreement results are strictly unvalidated and non-reportable.

### 4.2 By-Construction Artifact in Generated Pairs
- Candidate ungrammatical sentences are generated using the exact same mapping table used by the rule checker $G$.
- High agreement detection on these pairs is guaranteed by construction and does not serve as empirical validation of linguistic efficacy.

### 4.3 Domain Mismatch with External Corpora
- When an external LM training corpus (`data/raw/telugu_corpus.txt`) is provided (e.g., from Wikipedia, news corpora, or OSCAR), its vocabulary and genre will inevitably diverge from the pedagogical sentences in the MTG treebank.
- Out-of-vocabulary (OOV) rates and domain divergence will significantly affect the baseline trigram model's scores.

