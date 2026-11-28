import test from "node:test";
import assert from "node:assert/strict";
import { computePosBarLayout } from "../../web/js/charts/bars.js";

test("computePosBarLayout sorts by count descending and scales bars within width", () => {
  const layout = computePosBarLayout({ NOUN: 4, VERB: 2, PROPN: 1 }, 560);
  assert.equal(layout.bars.length, 3);
  assert.equal(layout.bars[0].pos, "NOUN");
  assert.equal(layout.bars[0].count, 4);
  assert.equal(layout.bars[1].pos, "VERB");
  assert.equal(layout.bars[2].pos, "PROPN");
  assert.ok(layout.bars[0].barWidth > layout.bars[1].barWidth);
  assert.ok(layout.bars[1].barWidth > layout.bars[2].barWidth);
  assert.ok(layout.bars[0].valueX < layout.width);
});

test("computePosBarLayout handles empty input", () => {
  const layout = computePosBarLayout({}, 400);
  assert.equal(layout.bars.length, 0);
  assert.ok(layout.height > 0);
});
