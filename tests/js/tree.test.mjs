import test from "node:test";
import assert from "node:assert/strict";
import { computeTreeLayout, parseBracketedTree } from "../../web/js/charts/tree.js";

test("parseBracketedTree parses nested CFG brackets with Telugu leaves", () => {
  const tree = parseBracketedTree("[S [VERB_P [PROPN రాము] [NOUN ఇంట్లోకి] [VERB వెళ్ళాడు]]]");
  assert.equal(tree.label, "S");
  assert.equal(tree.children.length, 1);
  assert.equal(tree.children[0].label, "VERB_P");
  assert.equal(tree.children[0].children.length, 3);
  assert.equal(tree.children[0].children[0].label, "PROPN");
  assert.equal(tree.children[0].children[0].children[0].label, "రాము");
  assert.equal(tree.children[0].children[0].children[0].isLeaf, true);
});

test("computeTreeLayout centers parents over children", () => {
  const tree = parseBracketedTree("[S [PROPN రాము] [VERB వెళ్ళాడు]]");
  const layout = computeTreeLayout(tree);
  const root = layout.nodes.find((n) => n.label === "S");
  const leaves = layout.nodes.filter((n) => n.isLeaf);
  assert.equal(leaves.length, 2);
  const expectedCenter = (leaves[0].x + leaves[1].x) / 2;
  assert.equal(root.x, expectedCenter);
  assert.equal(layout.edges.length, 4);
});
