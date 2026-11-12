# Telugu Agreement Validation Instructions

Thank you for helping validate sentence pairs for the Telugu grammar project. 

The file `docs/validation_sheet.csv` contains 293 candidate minimal pairs generated automatically by swapping verb endings to induce subject–verb agreement errors. We need a native or fluent Telugu speaker to independently verify whether each pair represents a true grammatical contrast.

---

## Evaluation Columns

In `docs/validation_sheet.csv`, please review each row and fill in the **`validated`** and **`validator_notes`** columns:

- **`pair_id`**: Identifier for the pair (do not edit).
- **`good_sentence`**: Original sentence from the Telugu treebank.
- **`bad_sentence`**: Perturbed candidate sentence with a swapped verb ending.
- **`validated`**: Your judgment (`yes` or `no`).
- **`validator_notes`**: Optional comments explaining your judgment or flagging edge cases.

---

## Validation Guidelines

1. **Mark `yes` only if:**
   - The first sentence (`good_sentence`) is **natural and grammatically correct** in Telugu.
   - AND the second sentence (`bad_sentence`) is **clearly ungrammatical / wrong** due to a subject–verb agreement clash.

2. **Mark `no` if:**
   - The second sentence (`bad_sentence`) could be **acceptable in any register** (including colloquial, formal, literary, dialectal, polite, or honorific forms).
   - For example, if a plural or polite verbal ending (like `-aru` / ారు) can grammatically apply to a singular subject in a respectful or honorific context, do **not** mark it as an error; mark `no`.
   - OR if the first sentence itself is unnatural or questionable.

3. **Add a note in `validator_notes` if unsure:**
   - If an example feels ambiguous, borderline, dependent on specific context, or involves dialectal variation, please leave a short note in `validator_notes`.

---

## Authoring New Speaker-Written Pairs

In addition to reviewing candidate rows, the project requires **at least 30 independent pairs** authored by a Telugu speaker (to be stored in `data/agreement/agreement_pairs_validated.csv` with `source=speaker_written`). 

When writing new pairs:
- Write natural Telugu sentences with clear subject–verb person/number agreement.
- Create a minimal pair by modifying only the verb ending so that it creates an unambiguous agreement violation.
- Ensure pairs cover a variety of pronouns (`నేను`, `మేము`, `నువ్వు`, `మీరు`, `అతను`, `ఆమె`, `వారు`) and tenses.
