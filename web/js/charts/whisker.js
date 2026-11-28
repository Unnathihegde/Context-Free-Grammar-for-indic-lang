/**
 * Dot-and-whisker confidence interval chart (pure layout + inline SVG renderer).
 */

const SVG_NS = "http://www.w3.org/2000/svg";

export const MODEL_COLORS = {
  "POS-bigram (POS)": "#1F4FD8",
  "Learned PCFG (POS)": "#A33F14",
  "PLL (xlm-roberta-base)": "#17673F",
  "PLL (google/muril-base-cased)": "#7A5B06",
  "Stanza (1.15.1)": "#1F4FD8",
  "xlm-roberta-base": "#17673F",
  "google/muril-base-cased": "#7A5B06",
};

/**
 * Pure layout function (no DOM) computing dot-and-whisker coordinates.
 */
export function computeWhiskerLayout(groups, options = {}) {
  const width = options.width || 680;
  const labelWidth = options.labelWidth || 170;
  const rightPad = options.rightPad || 56;
  const topPad = 16;
  const bottomPad = 34;
  const rowHeight = options.rowHeight || 22;
  const groupGap = options.groupGap || 12;

  const allVals = [];
  for (const g of groups) {
    for (const item of g.items) {
      allVals.push(item.value);
      if (item.ciLow !== null && item.ciLow !== undefined) allVals.push(item.ciLow);
      if (item.ciHigh !== null && item.ciHigh !== undefined) allVals.push(item.ciHigh);
    }
  }

  const rawMin = allVals.length ? Math.min(...allVals) : 0.5;
  const minDomain = options.minDomain !== undefined
    ? options.minDomain
    : Math.max(0, Math.floor((rawMin - 0.03) * 20) / 20);
  const maxDomain = options.maxDomain !== undefined ? options.maxDomain : 1.0;
  const plotLeft = labelWidth;
  const plotWidth = Math.max(140, width - labelWidth - rightPad);

  const scaleX = (v) =>
    plotLeft + ((v - minDomain) / Math.max(1e-6, maxDomain - minDomain)) * plotWidth;

  let y = topPad;
  const rows = [];
  const groupHeaders = [];

  for (let gi = 0; gi < groups.length; gi++) {
    const g = groups[gi];
    if (g.groupLabel) {
      groupHeaders.push({
        label: g.groupLabel,
        y: y + 13,
      });
      y += 20;
    }

    for (const item of g.items) {
      const cy = y + Math.floor(rowHeight / 2);
      rows.push({
        label: item.label,
        value: item.value,
        ciLow: item.ciLow,
        ciHigh: item.ciHigh,
        color: item.color || MODEL_COLORS[item.label] || "#1F4FD8",
        cy,
        xVal: scaleX(item.value),
        xLow: item.ciLow !== null && item.ciLow !== undefined ? scaleX(item.ciLow) : null,
        xHigh: item.ciHigh !== null && item.ciHigh !== undefined ? scaleX(item.ciHigh) : null,
      });
      y += rowHeight;
    }

    if (gi < groups.length - 1) {
      y += groupGap;
    }
  }

  const axisY = y + 8;
  const height = axisY + bottomPad;

  // Generate 5 evenly spaced ticks
  const ticks = [];
  const nTicks = 5;
  for (let i = 0; i < nTicks; i++) {
    const tVal = minDomain + (i / (nTicks - 1)) * (maxDomain - minDomain);
    ticks.push({
      value: tVal,
      label: tVal.toFixed(2),
      x: scaleX(tVal),
    });
  }

  return {
    width,
    height,
    labelWidth,
    plotLeft,
    plotRight: plotLeft + plotWidth,
    axisY,
    minDomain,
    maxDomain,
    groupHeaders,
    rows,
    ticks,
  };
}

/**
 * Render dot-and-whisker chart as inline SVG.
 */
export function renderWhiskerChartSvg(groups, options = {}) {
  const layout = computeWhiskerLayout(groups, options);
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${layout.width} ${layout.height}`);
  svg.setAttribute("width", String(layout.width));
  svg.setAttribute("height", String(layout.height));
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", options.ariaLabel || "Model comparison confidence intervals");
  svg.style.display = "block";

  // Vertical grid lines and axis ticks
  for (const tick of layout.ticks) {
    const grid = document.createElementNS(SVG_NS, "line");
    grid.setAttribute("x1", String(tick.x));
    grid.setAttribute("y1", "8");
    grid.setAttribute("x2", String(tick.x));
    grid.setAttribute("y2", String(layout.axisY));
    grid.setAttribute("stroke", "#EEF0F3");
    grid.setAttribute("stroke-width", "1");
    svg.appendChild(grid);

    const lbl = document.createElementNS(SVG_NS, "text");
    lbl.setAttribute("x", String(tick.x));
    lbl.setAttribute("y", String(layout.axisY + 16));
    lbl.setAttribute("text-anchor", "middle");
    lbl.setAttribute("font-size", "11");
    lbl.setAttribute("fill", "#5A6372");
    lbl.textContent = tick.label;
    svg.appendChild(lbl);
  }

  // Axis baseline
  const axis = document.createElementNS(SVG_NS, "line");
  axis.setAttribute("x1", String(layout.plotLeft));
  axis.setAttribute("y1", String(layout.axisY));
  axis.setAttribute("x2", String(layout.plotRight));
  axis.setAttribute("y2", String(layout.axisY));
  axis.setAttribute("stroke", "#E3E6EB");
  axis.setAttribute("stroke-width", "1");
  svg.appendChild(axis);

  // Group headers
  for (const gh of layout.groupHeaders) {
    const txt = document.createElementNS(SVG_NS, "text");
    txt.setAttribute("x", String(layout.labelWidth - 10));
    txt.setAttribute("y", String(gh.y));
    txt.setAttribute("text-anchor", "end");
    txt.setAttribute("font-size", "12");
    txt.setAttribute("font-weight", "600");
    txt.setAttribute("fill", "#14181F");
    txt.textContent = gh.label;
    svg.appendChild(txt);
  }

  // Rows: label + whisker + dot + numeric value
  for (const r of layout.rows) {
    const lbl = document.createElementNS(SVG_NS, "text");
    lbl.setAttribute("x", String(layout.labelWidth - 10));
    lbl.setAttribute("y", String(r.cy + 4));
    lbl.setAttribute("text-anchor", "end");
    lbl.setAttribute("font-size", "11");
    lbl.setAttribute("fill", "#5A6372");
    lbl.textContent = r.label;
    svg.appendChild(lbl);

    if (r.xLow !== null && r.xHigh !== null) {
      const line = document.createElementNS(SVG_NS, "line");
      line.setAttribute("x1", String(r.xLow));
      line.setAttribute("y1", String(r.cy));
      line.setAttribute("x2", String(r.xHigh));
      line.setAttribute("y2", String(r.cy));
      line.setAttribute("stroke", r.color);
      line.setAttribute("stroke-width", "1.5");
      svg.appendChild(line);

      for (const capX of [r.xLow, r.xHigh]) {
        const cap = document.createElementNS(SVG_NS, "line");
        cap.setAttribute("x1", String(capX));
        cap.setAttribute("y1", String(r.cy - 4));
        cap.setAttribute("x2", String(capX));
        cap.setAttribute("y2", String(r.cy + 4));
        cap.setAttribute("stroke", r.color);
        cap.setAttribute("stroke-width", "1.5");
        svg.appendChild(cap);
      }
    }

    const dot = document.createElementNS(SVG_NS, "circle");
    dot.setAttribute("cx", String(r.xVal));
    dot.setAttribute("cy", String(r.cy));
    dot.setAttribute("r", "4");
    dot.setAttribute("fill", r.color);
    svg.appendChild(dot);

    const valTxt = document.createElementNS(SVG_NS, "text");
    valTxt.setAttribute("x", String(layout.plotRight + 8));
    valTxt.setAttribute("y", String(r.cy + 4));
    valTxt.setAttribute("font-size", "11");
    valTxt.setAttribute("fill", "#14181F");
    valTxt.textContent = r.value.toFixed(3);
    svg.appendChild(valTxt);
  }

  return svg;
}
