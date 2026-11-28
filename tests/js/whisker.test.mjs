import test from "node:test";
import assert from "node:assert/strict";
import { computeWhiskerLayout } from "../../web/js/charts/whisker.js";

test("computeWhiskerLayout orders CI low <= value <= high within plot bounds", () => {
  const groups = [
    {
      groupLabel: "ALL",
      items: [
        { label: "POS-bigram (POS)", value: 0.9669, ciLow: 0.9566, ciHigh: 0.9768 },
        { label: "Learned PCFG (POS)", value: 0.9441, ciLow: 0.9312, ciHigh: 0.9564 },
      ],
    },
  ];
  const layout = computeWhiskerLayout(groups, { width: 680 });
  assert.equal(layout.rows.length, 2);
  for (const r of layout.rows) {
    assert.ok(r.xLow <= r.xVal && r.xVal <= r.xHigh);
    assert.ok(r.xLow >= layout.plotLeft && r.xHigh <= layout.plotRight + 0.5);
  }
  assert.equal(layout.ticks.length, 5);
});
