/**
 * Horizontal POS-count bar chart (pure layout + SVG renderer).
 */

const SVG_NS = "http://www.w3.org/2000/svg";

/**
 * Pure layout function (no DOM) computing bar geometry for POS counts.
 * @param {Record<string, number>} posCounts
 * @param {number} width
 */
export function computePosBarLayout(posCounts, width = 560) {
  const entries = Object.entries(posCounts || {}).sort(
    (a, b) => b[1] - a[1] || a[0].localeCompare(b[0])
  );
  const labelWidth = 80;
  const rightPad = 48;
  const rowHeight = 28;
  const barHeight = 16;
  const topPad = 8;
  const bottomPad = 8;
  const maxBarWidth = Math.max(80, width - labelWidth - rightPad);
  const maxCount = entries.reduce((m, [, c]) => Math.max(m, c), 1);

  const bars = entries.map(([pos, count], idx) => {
    const y = topPad + idx * rowHeight;
    const barW = Math.max(4, Math.round((count / maxCount) * maxBarWidth));
    return {
      pos,
      count,
      y,
      barY: y + Math.floor((rowHeight - barHeight) / 2),
      barX: labelWidth,
      barWidth: barW,
      barHeight,
      valueX: labelWidth + barW + 8,
      textY: y + Math.floor(rowHeight / 2) + 4,
    };
  });

  const height = topPad + entries.length * rowHeight + bottomPad;
  return { width, height, labelWidth, maxCount, bars };
}

/**
 * Render an inline SVG horizontal bar chart using createElementNS.
 * @param {Record<string, number>} posCounts
 */
export function renderPosBarChartSvg(posCounts) {
  const layout = computePosBarLayout(posCounts, 420);
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${layout.width} ${layout.height}`);
  svg.setAttribute("width", "100%");
  svg.setAttribute("height", String(layout.height));
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Part-of-speech tag frequency bar chart");
  svg.style.maxWidth = `${layout.width}px`;
  svg.style.display = "block";

  for (const bar of layout.bars) {
    const label = document.createElementNS(SVG_NS, "text");
    label.setAttribute("x", String(layout.labelWidth - 10));
    label.setAttribute("y", String(bar.textY));
    label.setAttribute("text-anchor", "end");
    label.setAttribute("font-size", "12");
    label.setAttribute("font-weight", "500");
    label.setAttribute("fill", "#14181F");
    label.textContent = bar.pos;
    svg.appendChild(label);

    const rect = document.createElementNS(SVG_NS, "rect");
    rect.setAttribute("x", String(bar.barX));
    rect.setAttribute("y", String(bar.barY));
    rect.setAttribute("width", String(bar.barWidth));
    rect.setAttribute("height", String(bar.barHeight));
    rect.setAttribute("rx", "3");
    rect.setAttribute("fill", "#1F4FD8");
    rect.setAttribute("fill-opacity", "0.85");
    svg.appendChild(rect);

    const val = document.createElementNS(SVG_NS, "text");
    val.setAttribute("x", String(bar.valueX));
    val.setAttribute("y", String(bar.textY));
    val.setAttribute("font-size", "12");
    val.setAttribute("fill", "#5A6372");
    val.textContent = String(bar.count);
    svg.appendChild(val);
  }

  return svg;
}
