import random
from collections import Counter, defaultdict

from nltk.parse import ViterbiParser

from grammar_learn import induce, load_all, parse_prob, pos_seq, prepare


def make_pairs(sent):
    good, n = pos_seq(sent), len(sent)
    for i, t in enumerate(sent):
        h = t["head"]
        if h == 0:
            continue
        hi = h - 1
        if t["rel"] in ("det", "amod") and hi == i + 1:
            bad = good[:]
            bad[i], bad[hi] = bad[hi], bad[i]
            yield ("det_after" if t["rel"] == "det" else "amod_after"), good, bad
        if t["rel"] == "case" and hi == i - 1:
            bad = good[:]
            bad[i], bad[hi] = bad[hi], bad[i]
            yield "case_before", good, bad
    roots = [i for i, t in enumerate(sent) if t["head"] == 0]
    if n >= 3 and roots and roots[0] == n - 1 and sent[-1]["pos"] == "VERB":
        yield "verb_first", good, [good[-1]] + good[:-1]


def run(k=5, seed=0, max_len=20):
    trees, _ = prepare(load_all())
    idx = list(range(len(trees)))
    random.Random(seed).shuffle(idx)
    folds = [idx[i::k] for i in range(k)]
    stats = defaultdict(Counter)
    for f in range(k):
        test = set(folds[f])
        parser = ViterbiParser(induce([trees[i] for i in idx if i not in test]))
        for i in folds[f]:
            sent = trees[i][0]
            if len(sent) > max_len:
                continue
            for kind, good, bad in make_pairs(sent):
                if good == bad:
                    continue
                pg, pb = parse_prob(parser, good), parse_prob(parser, bad)
                stats[kind]["good wins" if pg > pb else "bad wins" if pg < pb else "tie"] += 1
    return stats


if __name__ == "__main__":
    tot = Counter()
    for kind, c in run().items():
        n = sum(c.values())
        tot.update(c)
        print(f"{kind:12s} pairs={n:4d} acc(ties=0.5)={(c['good wins']+.5*c['tie'])/n:.2f}")
    n = sum(tot.values())
    print(f"ALL          pairs={n:4d} acc(ties=0.5)={(tot['good wins']+.5*tot['tie'])/n:.2f}")
