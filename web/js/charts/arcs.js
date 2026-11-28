/**
 * Dependency arc diagram (pure layout + inline SVG renderer).
 */

const SVG_NS = "http://www.w3.org/2000/svg";

/**
 * Pure layout function (no DOM) computing word slots, arc curves, and pill positions.
 * @param {Array<{id:number, word:string, upos:string, head_id:number, deprel:string}>} tokens
 * @param {{wordSpacing?:number}} options
 */
export function computeArcLayout(tokens, options = {}) {
  const list = Array.isArray(tokens) ? tokens : [];
  const wordSpacing = options.wordSpacing || 132;
  const padX = 36;
  const width = Math.max(360, padX * 2 + list.length * wordSpacing);

  const idToIdx = new Map();
  list.forEach((t, idx) => idToIdx.set(t.id, idx));

  const arcs = [];
  let maxArcHeight = 52;

  // Track midpoints to stagger overlapping label pills slightly
  const usedMidpoints = [];

  for (let i = 0; i < list.length; i++) {
    const tok = list[i];
    if (!tok.head_id || tok.head_id === 0 || !idToIdx.has(tok.head_id)) {
      continue;
    }
    const headIdx = idToIdx.get(tok.head_id);
    if (headIdx === i) continue;

    const span = Math.abs(headIdx - i);
    let arcHeight = 38 + span * 34;

    const x1 = padX + headIdx * wordSpacing + wordSpacing / 2;
    const x2 = padX + i * wordSpacing + wordSpacing / 2;
    const apexX = (x1 + x2) / 2;

    // Stagger if another arc has a very close apexX and similar height
    for (const prev of usedMidpoints) {
      if (Math.abs(prev.x - apexX) < 42 && Math.abs(prev.h - arcHeight) < 26) {
        arcHeight += 28;
      }
    }
    usedMidpoints.push({ x: apexX, h: arcHeight });
    if (arcHeight > maxArcHeight) maxArcHeight = arcHeight;

    arcs.push({
      id: tok.id,
      headId: tok.head_id,
      deprel: tok.deprel || "",
      x1,
      x2,
      arcHeight,
      apexX,
      pillWidth: Math.max(42, (tok.deprel || "").length * 7.5 + 16),
      pillHeight: 20,
    });
  }

  // Cubic Bezier apex is at y0 - 0.75 * arcHeight
  const topSpace = Math.ceil(maxArcHeight * 0.78) + 46;
  const baselineY = Math.max(112, topSpace);
  const arcBaseY = baselineY - 12;

  const words = list.map((t, idx) => ({
    id: t.id,
    word: t.word,
    upos: t.upos,
    isRoot: t.head_id === 0 || t.deprel === "root",
    x: padX + idx * wordSpacing + wordSpacing / 2,
    wordY: baselineY + 18,
    posY: baselineY + 38,
  }));

  const positionedArcs = arcs.map((a) => ({
    ...a,
    y0: arcBaseY,
    ctrlY: arcBaseY - a.arcHeight,
    apexY: arcBaseY - 0.75 * a.arcHeight,
  }));

  const height = baselineY + 54;
  return { width, height, baselineY, arcBaseY, wordSpacing, words, arcs: positionedArcs };
}

/**
 * Render dependency arc diagram as an inline SVG element.
 */
export function renderDependencyArcsSvg(tokens, options = {}) {
  const layout = computeArcLayout(tokens, options);
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${layout.width} ${layout.height}`);
  svg.setAttribute("width", String(layout.width));
  svg.setAttribute("height", String(layout.height));
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Dependency arc diagram");
  svg.style.display = "block";

  // Arrowhead marker
  const defs = document.createElementNS(SVG_NS, "defs");
  const createMarker = (id, color) => {
    const marker = document.createElementNS(SVG_NS, "marker");
    marker.setAttribute("id", id);
    marker.setAttribute("viewBox", "0 0 10 10");
    marker.setAttribute("refX", "7");
    marker.setAttribute("refY", "5");
    marker.setAttribute("markerWidth", "6");
    marker.setAttribute("markerHeight", "6");
    marker.setAttribute("orient", "auto");
    const path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("d", "M 0 1.5 L 8 5 L 0 8.5 z");
    path.setAttribute("fill", color);
    marker.appendChild(path);
    return marker;
  };
  defs.appendChild(createMarker("dep-arrow", "#5A6372"));
  defs.appendChild(createMarker("dep-arrow-active", "#1F4FD8"));
  svg.appendChild(defs);

  // Root markers
  for (const w of layout.words) {
    if (!w.isRoot) continue;
    const rootLine = document.createElementNS(SVG_NS, "line");
    rootLine.setAttribute("x1", String(w.x));
    rootLine.setAttribute("y1", "22");
    rootLine.setAttribute("x2", String(w.x));
    rootLine.setAttribute("y2", String(layout.arcBaseY - 4));
    rootLine.setAttribute("stroke", "#14181F");
    rootLine.setAttribute("stroke-width", "2");
    rootLine.setAttribute("marker-end", "url(#dep-arrow)");
    svg.appendChild(rootLine);

    const pill = document.createElementNS(SVG_NS, "rect");
    pill.setAttribute("x", String(w.x - 22));
    pill.setAttribute("y", "4");
    pill.setAttribute("width", "44");
    pill.setAttribute("height", "18");
    pill.setAttribute("rx", "4");
    pill.setAttribute("fill", "#F6F7F9");
    pill.setAttribute("stroke", "#E3E6EB");
    svg.appendChild(pill);

    const txt = document.createElementNS(SVG_NS, "text");
    txt.setAttribute("x", String(w.x));
    txt.setAttribute("y", "16");
    txt.setAttribute("text-anchor", "middle");
    txt.setAttribute("font-size", "10");
    txt.setAttribute("font-weight", "600");
    txt.setAttribute("fill", "#14181F");
    txt.textContent = "ROOT";
    svg.appendChild(txt);
  }

  // Arcs (short spans drawn after long spans so hover hits cleanly)
  const sortedArcs = [...layout.arcs].sort((a, b) => b.arcHeight - a.arcHeight);
  for (const arc of sortedArcs) {
    const g = document.createElementNS(SVG_NS, "g");
    g.style.cursor = "pointer";

    const path = document.createElementNS(SVG_NS, "path");
    const d = `M ${arc.x1} ${arc.y0} C ${arc.x1} ${arc.ctrlY}, ${arc.x2} ${arc.ctrlY}, ${arc.x2} ${arc.y0 - 3}`;
    path.setAttribute("d", d);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "#5A6372");
    path.setAttribute("stroke-width", "1.5");
    path.setAttribute("marker-end", "url(#dep-arrow)");
    g.appendChild(path);

    const pill = document.createElementNS(SVG_NS, "rect");
    pill.setAttribute("x", String(arc.apexX - arc.pillWidth / 2));
    pill.setAttribute("y", String(arc.apexY - arc.pillHeight / 2));
    pill.setAttribute("width", String(arc.pillWidth));
    pill.setAttribute("height", String(arc.pillHeight));
    pill.setAttribute("rx", "4");
    pill.setAttribute("fill", "#FFFFFF");
    pill.setAttribute("stroke", "#E3E6EB");
    g.appendChild(pill);

    const label = document.createElementNS(SVG_NS, "text");
    label.setAttribute("x", String(arc.apexX));
    label.setAttribute("y", String(arc.apexY + 4));
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("font-size", "11");
    label.setAttribute("font-weight", "500");
    label.setAttribute("fill", "#14181F");
    label.textContent = arc.deprel;
    g.appendChild(label);

    g.addEventListener("mouseenter", () => {
      path.setAttribute("stroke", "#1F4FD8");
      path.setAttribute("stroke-width", "2.2");
      path.setAttribute("marker-end", "url(#dep-arrow-active)");
      pill.setAttribute("stroke", "#1F4FD8");
      label.setAttribute("fill", "#1F4FD8");
    });
    g.addEventListener("mouseleave", () => {
      path.setAttribute("stroke", "#5A6372");
      path.setAttribute("stroke-width", "1.5");
      path.setAttribute("marker-end", "url(#dep-arrow)");
      pill.setAttribute("stroke", "#E3E6EB");
      label.setAttribute("fill", "#14181F");
    });

    svg.appendChild(g);
  }

  // Words & UPOS tags
  for (const w of layout.words) {
    const wordText = document.createElementNS(SVG_NS, "text");
    wordText.setAttribute("x", String(w.x));
    wordText.setAttribute("y", String(w.wordY));
    wordText.setAttribute("text-anchor", "middle");
    wordText.setAttribute("font-family", "Noto Sans Telugu, Nirmala UI, Gautami, sans-serif");
    wordText.setAttribute("font-size", "16");
    wordText.setAttribute("font-weight", "500");
    wordText.setAttribute("fill", "#14181F");
    wordText.textContent = w.word;
    svg.appendChild(wordText);

    const posText = document.createElementNS(SVG_NS, "text");
    posText.setAttribute("x", String(w.x));
    posText.setAttribute("y", String(w.posY));
    posText.setAttribute("text-anchor", "middle");
    posText.setAttribute("font-size", "11");
    posText.setAttribute("font-weight", "500");
    posText.setAttribute("fill", "#5A6372");
    posText.textContent = w.upos;
    svg.appendChild(posText);
  }

  return svg;
}
