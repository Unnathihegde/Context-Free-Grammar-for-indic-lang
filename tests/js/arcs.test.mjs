import test from "node:test";
import assert from "node:assert/strict";
import { computeArcLayout, computeHeadOffsets } from "../../web/js/charts/arcs.js";

test("computeArcLayout positions words and non-colliding arcs", () => {
  const tokens = [
    { id: 1, word: "రాము", upos: "PROPN", head_id: 3, deprel: "nsubj" },
    { id: 2, word: "ఇంట్లోకి", upos: "NOUN", head_id: 3, deprel: "obl" },
    { id: 3, word: "వెళ్ళాడు", upos: "VERB", head_id: 0, deprel: "root" },
  ];
  const layout = computeArcLayout(tokens);
  assert.equal(layout.words.length, 3);
  assert.equal(layout.arcs.length, 2);
  assert.ok(layout.words[0].x < layout.words[1].x);
  assert.ok(layout.words[1].x < layout.words[2].x);
  assert.ok(layout.words[2].isRoot);
  // All arc apexes must stay inside positive SVG y coordinates
  for (const arc of layout.arcs) {
    assert.ok(arc.apexY > 10, `apexY ${arc.apexY} should leave top room`);
  }
});

test("computeArcLayout handles empty token list", () => {
  const layout = computeArcLayout([]);
  assert.equal(layout.words.length, 0);
  assert.equal(layout.arcs.length, 0);
  assert.ok(layout.width >= 360);
});

test("computeHeadOffsets spreads multiple arcs sharing the same head word", () => {
  const arcs = [
    { id: 1, headId: 3, span: 2, depIdx: 0 },
    { id: 2, headId: 3, span: 1, depIdx: 1 },
    { id: 4, headId: 3, span: 1, depIdx: 3 },
  ];
  const offsets = computeHeadOffsets(arcs, 8);
  assert.equal(offsets.size, 3);
  const vals = Array.from(offsets.values());
  // All three offsets must be distinct and symmetric around 0
  assert.equal(new Set(vals).size, 3);
  assert.equal(vals.reduce((a, b) => a + b, 0), 0);
});
