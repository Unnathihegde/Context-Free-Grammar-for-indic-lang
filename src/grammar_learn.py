import random
from collections import Counter

from nltk import Nonterminal, Tree, induce_pcfg
from nltk.parse import ViterbiParser

FILES = ["data/te_train.conllu", "data/te_dev.conllu", "data/te_test.conllu"]


def read_conllu(fn):
    sents, cur = [], []
    for line in open(fn, encoding="utf8"):
        line = line.rstrip("\n")
        if not line:
            if cur:
                sents.append(cur)
                cur = []
        elif not line.startswith("#"):
            f = line.split("\t")
            if "-" in f[0] or "." in f[0]:
                continue
            cur.append({"id": int(f[0]), "word": f[1], "pos": f[3],
                        "head": int(f[6]), "rel": f[7]})
    if cur:
        sents.append(cur)
    return sents


def load_all():
    out = []
    for fn in FILES:
        out += read_conllu(fn)
    return out


def drop_punct(sent):
    keep = [t for t in sent if t["pos"] != "PUNCT"]
    if not keep:
        return None
    new_id = {t["id"]: i + 1 for i, t in enumerate(keep)}
    out = []
    for t in keep:
        if t["head"] != 0 and t["head"] not in new_id:
            return None
        out.append({**t, "id": new_id[t["id"]],
                    "head": 0 if t["head"] == 0 else new_id[t["head"]]})
    return out


def to_tree(sent):
    roots = [t for t in sent if t["head"] == 0]
    if len(roots) != 1:
        return None
    kids = {t["id"]: [] for t in sent}
    for t in sent:
        if t["head"] != 0:
            kids[t["head"]].append(t["id"])
    by_id = {t["id"]: t for t in sent}

    def build(i):
        t = by_id[i]
        leaf = Tree(t["pos"], [t["pos"].lower()])
        left = [build(c) for c in sorted(kids[i]) if c < i]
        right = [build(c) for c in sorted(kids[i]) if c > i]
        if not left and not right:
            return leaf
        return Tree(t["pos"] + "_P", left + [leaf] + right)

    tree = build(roots[0]["id"])
    if [x.lower() for x in tree.leaves()] != [t["pos"].lower() for t in sent]:
        return None
    return Tree("S", [tree])


def prepare(sents):
    trees, skipped = [], Counter()
    for s in sents:
        s2 = drop_punct(s)
        if s2 is None:
            skipped["punct-head or empty"] += 1
            continue
        t = to_tree(s2)
        if t is None:
            skipped["multi-root or non-projective"] += 1
            continue
        trees.append((s2, t))
    return trees, skipped


def induce(trees):
    prods = []
    for _, t in trees:
        t = t.copy(deep=True)
        t.chomsky_normal_form(horzMarkov=1)
        t.collapse_unary(collapsePOS=False)
        prods += t.productions()
    return induce_pcfg(Nonterminal("S"), prods)


def pos_seq(sent):
    return [t["pos"].lower() for t in sent]


def parse_prob(parser, seq):
    try:
        for tr in parser.parse(seq):
            return tr.prob()
    except ValueError:
        return 0.0
    return 0.0


def cv_coverage(trees, k=5, seed=0, max_len=20):
    idx = list(range(len(trees)))
    random.Random(seed).shuffle(idx)
    folds = [idx[i::k] for i in range(k)]
    res = []
    for f in range(k):
        test = set(folds[f])
        parser = ViterbiParser(induce([trees[i] for i in idx if i not in test]))
        cov = n = 0
        for i in folds[f]:
            s = trees[i][0]
            if len(s) > max_len:
                continue
            n += 1
            cov += parse_prob(parser, pos_seq(s)) > 0
        res.append((cov, n))
    return res


if __name__ == "__main__":
    trees, skipped = prepare(load_all())
    print("usable trees:", len(trees), "| skipped:", dict(skipped))
    print("rules:", len(induce(trees).productions()))
    res = cv_coverage(trees)
    c, n = sum(a for a, _ in res), sum(b for _, b in res)
    print(f"held-out coverage: {c}/{n} = {c/n:.1%}")
