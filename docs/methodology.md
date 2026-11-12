# Methodology

This document details the experimental pipeline, dataset splits, data leakage controls, evaluation metrics, and validation criteria for the Telugu Context-Free Grammar (PCFG) project.

---

## 1. Experimental Pipeline

The project investigates whether explicit hierarchical grammatical structure learned from a small dependency treebank can assist language models in distinguishing grammatical from ungrammatical sentences in Telugu (an agglutinative, SOV Dravidian language).

The pipeline comprises the following stages:

```
UD Telugu-MTG Treebank (.conllu)
           │
           ├── Head-outward projection (punctuation removed)
           ▼
     Phrase Structure Trees
           │
           ├── PCFG Induction over UPOS tags (Viterbi Parser)
           │
           ├── Word-Order Minimal Pairs Generation (Held-out CV)
           ▼
     Evaluation vs. POS-Bigram Baseline
```

Separately, an agreement evaluation module tests pronoun–verb agreement:
```
UD Telugu-MTG Treebank & agreement_table.csv
           │
           ├── Candidate Pair Generation (nsubj -> VERB person mismatches)
           ▼
     Agreement Pairs (source: generated vs speaker_written)
           │
           ├── Sentence-grouped Split (Validation / Test)
           ├── Lambda tuning on Validation (grid: 0, 0.1, 0.5, 1, 2, 5, 10)
           ├── Trigram LM (B1) trained with evaluation sentences excluded
           ├── Agreement Checker (G) counting person violations
           ▼
     Hybrid Score H = B1 - lambda * violations
```

---

## 2. Grammar Induction & Baseline Models

### 2.1 PCFG (Hierarchical Model)
- **Data Source**: Universal Dependencies Telugu-MTG treebank (1,328 sentences).
- **Tree Conversion**: Head-outward projection mapping dependency relations into projective phrase structures (`S -> X_P`). Punctuation tokens (`PUNCT`) are removed and token indices re-aligned. Multi-root and non-projective trees are discarded (2 sentences skipped; 1,326 usable).
- **Grammar Learning**: Trees are converted to Chomsky Normal Form (`horzMarkov=1`) with collapsed unaries, yielding an induced PCFG over UPOS tags (375 rules across the full treebank).
- **Scoring**: Sentences are scored by Viterbi parse probability $P(w_1 \dots w_n)$ over POS tag sequences. Unparseable sequences receive probability 0.0.

### 2.2 POS-Bigram Baseline
- **Model**: Add-$k$ smoothed bigram model ($k = 0.1$) trained strictly on POS tag sequences from the training folds.
- **Scoring**: Length-normalized log probability:
  $$\text{Score}(S) = \frac{1}{|S|} \sum_{i=1}^{|S|+1} \log P(t_i \mid t_{i-1})$$

### 2.3 Word-Level Trigram Language Model ($B_1$)
- **Model**: Interpolated absolute-discounting trigram model ($d = 0.75$, minimum count threshold 1) with an explicit `<unk>` token class.
- **Corpus**: Intended to be trained on an external Telugu corpus (`data/raw/telugu_corpus.txt`). When absent, a 3-sentence toy demo corpus is used, triggering `lm_mode: "demo"`.

### 2.4 Agreement Rule Checker ($G$)
- **Mechanism**: Inspects pronoun subjects and verb suffixes against an agreement mapping table. Returns the number of person mismatches $V \in \mathbb{N}$, or abstains ($V = \text{None}$) if no recognized subject–verb pair is present.

### 2.5 Hybrid Model ($H$)
- Combines the normalized word LM score $B_1$ with agreement violation counts $V$:
  $$H(S) = \begin{cases} B_1(S) - \lambda \cdot V(S), & \text{if } V(S) \neq \text{None} \\ B_1(S), & \text{if } V(S) = \text{None} \end{cases}$$
- The penalty hyperparameter $\lambda \ge 0$ is tuned strictly on validation fold pairs.

---

## 3. Data Leakage Controls

Rigorous boundary isolation prevents optimistic bias:
1. **Cross-Validation Isolation**: PCFG grammars and POS-bigram taggers are fit exclusively on the $k-1$ training folds. Minimal pairs are derived exclusively from sentences in the held-out test fold.
2. **Corpus Leakage Elimination**: Before fitting the word-level trigram LM, every evaluation sentence (both the grammatical "good" sentence and ungrammatical "bad" sentence) is NFC-normalized and strictly filtered out of the training corpus (`load_training_sentences`).
3. **Sentence-Level Clustered Splits**: For agreement pair evaluations, multiple pair variations derived from the same base sentence are kept strictly together in either validation or test folds (`split_by_sentence`), never divided across splits.
4. **Validation-Only Tuning**: The hybrid weight $\lambda$ is selected exclusively on the validation fold; the test fold is evaluated once using the chosen parameter.

---

## 4. Evaluation Metrics & Statistical Testing

- **Minimal-Pair Ranking Accuracy**:
  $$\text{Accuracy} = \frac{\text{Good Wins} + 0.5 \times \text{Ties}}{N}$$
  where a "Good Win" occurs when the model assigns a higher probability/score to the grammatical sentence than to the perturbed counterpart.
- **Clustered Bootstrap Resampling**:
  Because multiple minimal pairs can originate from the same sentence, observations within a sentence are not independent. Standard confidence intervals would underestimate standard errors.
  - Uncertainty is quantified using **sentence-clustered bootstrapping** (1,000 resamples). Complete sentence clusters are sampled with replacement.
  - Two-sided paired bootstrap $p$-values with finite-sample $+1$ correction are computed to test whether score differences ($H - B_1$ or PCFG vs. Bigram) are statistically significant.

---

## 5. Agreement Pair Sources & The By-Construction Caveat

Pairs for agreement evaluation are classified into two strictly segregated sources:

| Source | Generation Method | Status / Purpose |
| :--- | :--- | :--- |
| `generated` | Semi-automatically created by perturbing verb suffixes on treebank sentences using `agreement_table.csv`. | **Formative / Exploratory only.** |
| `speaker_written` | Independently authored and verified by native Telugu speakers. | **Target for reportable conclusions.** |

### The By-Construction Caveat (Critical)
> [!WARNING]
> In `generated` pairs, the bad sentences were produced by substituting verb endings defined in `data/agreement/agreement_table.csv`. The rule checker $G$ evaluates sentences using the **exact same table**. Consequently, $G$ detects these errors **by construction**.
> High performance of $G$ or $H$ on `generated` pairs must **never** be presented as empirical evidence that the grammar improves language modeling. Validated conclusions require independently authored `speaker_written` pairs.

---

## 6. Reportability Criteria

A result row in `agreement_results.csv` or `datasize_curve.csv` is marked `reportable = True` **only if all of the following conditions are satisfied**:
1. At least 30 validated pairs exist for that source (`n_validated >= 30`).
2. The agreement table is fully validated by a Telugu speaker (`table_status == "validated"`).
3. The real external LM corpus is present (`lm_mode == "corpus"`).
4. Held-out test pairs exist (`n_test_pairs > 0`).

If any condition fails, the pipeline sets `reportable = False`, logs a warning to the console, and displays a prominent warning in the user interface.

