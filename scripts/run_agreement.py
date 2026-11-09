"""Run validated agreement evaluation; warnings are expected until validation is complete."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from eval_agreement import RESULTS_PATH, write_results  # noqa: E402


if __name__ == "__main__":
    rows, metadata = write_results()
    if metadata["lm_mode"] == "demo":
        print("WARNING: DEMO MODE — data/raw/telugu_corpus.txt is missing; results are not reportable.")
    for row in rows:
        print(f"{row['source']}: n_pairs={row['n_pairs']} n_validated={row['n_validated']} "
              f"reportable={row['reportable']}")
        if not row["reportable"]:
            print(f"WARNING [{row['source']}]: {row['reportability_reason']}")
    print(f"wrote: {RESULTS_PATH}")
