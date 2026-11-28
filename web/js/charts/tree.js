/**
 * Phrase-structure CFG tree (bracket parser, pure top-down layout, inline SVG).
 */

const SVG_NS = "http://www.w3.org/2000/svg";

/**
 * Parse a bracketed tree string like "[S [VERB_P [PROPN రాము] [VERB వెళ్ళాడు]]]"
 * into a nested { label, isLeaf, children } object.
 */
export function parseBracketedTree(bracketStr) {
  if (!bracketStr || typeof bracketStr !== "string") return null;
  const tokens = [];
  let i = 0;
  while (i < bracketStr.length) {
    const ch = bracketStr[i];
    if (ch === "[" || ch === "]") {
      tokens.push(ch);
      i++;
    } else if (/\s/.test(ch)) {
      i++;
    } else {
      let j = i;
      while (j < bracketStr.length && !/[\s\[\]]/.test(bracketStr[j])) {
        j++;
      }
      tokens.push(bracketStr.slice(i, j));
      i = j;
    }
  }

  let pos = 0;
  function parseNode() {
    if (tokens[pos] !== "[") {
      const leafLabel = tokens[pos++];
      return { label: leafLabel, isLeaf: true, children: [] };
    }
    pos++; // consume '['
    const label = tokens[pos++];
    const children = [];
    while (pos < tokens.length && tokens[pos] !== "]") {
      children.push(parseNode());
    }
    if (tokens[pos] === "]") pos++;
    return { label, isLeaf: children.length === 0, children };
  }

  if (!tokens.length || tokens[0] !== "[") return null;
  return parseNode();
}

/**
 * Pure top-down layout: parents centered over children, leaves evenly spaced.
 */
export function computeTreeLayout(rootNode, options = {}) {
  if (!rootNode) return { width: 360, height: 120, nodes: [], edges: [] };

  const leafSpacing = options.leafSpacing || 112;
  const levelHeight = options.levelHeight || 62;
  const padX = 36;
  const padY = 24;

  let leafCounter = 0;
  let maxDepth = 0;
  const nodes = [];
  const edges = [];

  function layoutNode(node, depth) {
    if (depth > maxDepth) maxDepth = depth;
    const y = padY + depth * levelHeight;

    if (!node.children || node.children.length === 0) {
      const x = padX + leafCounter * leafSpacing + leafSpacing / 2;
      leafCounter++;
      const placed = { label: node.label, isLeaf: true, depth, x, y };
      nodes.push(placed);
      return placed;
    }

    const childPlaced = node.children.map((ch) => layoutNode(ch, depth + 1));
    const minX = childPlaced[0].x;
    const maxX = childPlaced[childPlaced.length - 1].x;
    const x = (minX + maxX) / 2;

    const placed = { label: node.label, isLeaf: false, depth, x, y };
    nodes.push(placed);
    for (const ch of childPlaced) {
      edges.push({ x1: x, y1: y + 12, x2: ch.x, y2: ch.y - 12 });
    }
    return placed;
  }

  layoutNode(rootNode, 0);
  const width = Math.max(360, padX * 2 + leafCounter * leafSpacing);
  const height = padY * 2 + maxDepth * levelHeight + 24;
  return { width, height, nodes, edges };
}

/**
 * Render phrase-structure tree as inline SVG.
 */
export function renderTreeSvg(bracketStr, options = {}) {
  const parsed = parseBracketedTree(bracketStr);
  const layout = computeTreeLayout(parsed, { leafSpacing: 88, ...options });

  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${layout.width} ${layout.height}`);
  svg.setAttribute("width", String(layout.width));
  svg.setAttribute("height", String(layout.height));
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Phrase-structure syntax tree");
  svg.style.display = "block";
  svg.style.maxWidth = "100%";
  svg.style.height = "auto";

  for (const edge of layout.edges) {
    const line = document.createElementNS(SVG_NS, "line");
    line.setAttribute("x1", String(edge.x1));
    line.setAttribute("y1", String(edge.y1));
    line.setAttribute("x2", String(edge.x2));
    line.setAttribute("y2", String(edge.y2));
    line.setAttribute("stroke", "#C5CCD6");
    line.setAttribute("stroke-width", "1");
    svg.appendChild(line);
  }

  for (const node of layout.nodes) {
    if (node.isLeaf) {
      const txt = document.createElementNS(SVG_NS, "text");
      txt.setAttribute("x", String(node.x));
      txt.setAttribute("y", String(node.y + 5));
      txt.setAttribute("text-anchor", "middle");
      txt.setAttribute("font-family", "Noto Sans Telugu, Nirmala UI, Gautami, sans-serif");
      txt.setAttribute("font-size", "15");
      txt.setAttribute("font-weight", "500");
      txt.setAttribute("fill", "#14181F");
      txt.textContent = node.label;
      svg.appendChild(txt);
    } else {
      const chipW = Math.max(34, node.label.length * 7.5 + 14);
      const chipH = 22;
      const rect = document.createElementNS(SVG_NS, "rect");
      rect.setAttribute("x", String(node.x - chipW / 2));
      rect.setAttribute("y", String(node.y - chipH / 2));
      rect.setAttribute("width", String(chipW));
      rect.setAttribute("height", String(chipH));
      rect.setAttribute("rx", "4");
      rect.setAttribute("fill", "#F6F7F9");
      rect.setAttribute("stroke", "#E3E6EB");
      svg.appendChild(rect);

      const txt = document.createElementNS(SVG_NS, "text");
      txt.setAttribute("x", String(node.x));
      txt.setAttribute("y", String(node.y + 4));
      txt.setAttribute("text-anchor", "middle");
      txt.setAttribute("font-size", "11");
      txt.setAttribute("font-weight", "600");
      txt.setAttribute("fill", "#14181F");
      txt.textContent = node.label;
      svg.appendChild(txt);
    }
  }

  return svg;
}
