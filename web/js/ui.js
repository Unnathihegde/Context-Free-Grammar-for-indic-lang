/**
 * DOM builders for Telugu Grammar Analyzer (no innerHTML with data).
 */

import { renderPosBarChartSvg } from "./charts/bars.js";

const POS_FAMILIES = {
  NOUN: "chip-pos-noun",
  PROPN: "chip-pos-noun",
  PRON: "chip-pos-noun",
  VERB: "chip-pos-verb",
  AUX: "chip-pos-verb",
  DET: "chip-pos-func",
  ADP: "chip-pos-func",
  CCONJ: "chip-pos-func",
  SCONJ: "chip-pos-func",
  PART: "chip-pos-func",
  ADV: "chip-pos-func",
  ADJ: "chip-pos-func",
  NUM: "chip-pos-func",
};

export function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "className") {
      node.className = v;
    } else if (k === "textContent") {
      node.textContent = v;
    } else if (k.startsWith("on") && typeof v === "function") {
      node.addEventListener(k.slice(2).toLowerCase(), v);
    } else {
      node.setAttribute(k, String(v));
    }
  }
  for (const child of children) {
    if (child === null || child === undefined) continue;
    if (typeof child === "string") {
      node.appendChild(document.createTextNode(child));
    } else {
      node.appendChild(child);
    }
  }
  return node;
}

export function getPosChipClass(upos) {
  return POS_FAMILIES[upos] || "chip-pos-other";
}

export function renderErrorBox(err) {
  const children = [
    el("h3", { className: "error-title", textContent: "Analysis unavailable" }),
    el("p", { textContent: err.message || "An unexpected error occurred." }),
  ];

  if (err.downloadCommand) {
    const copyBtn = el("button", {
      type: "button",
      className: "btn btn-secondary btn-sm",
      textContent: "Copy command",
      onClick: async () => {
        try {
          await navigator.clipboard.writeText(err.downloadCommand);
          copyBtn.textContent = "Copied";
          setTimeout(() => {
            copyBtn.textContent = "Copy command";
          }, 1500);
        } catch {
          copyBtn.textContent = "Copy failed";
        }
      },
    });
    children.push(
      el("div", { className: "cmd-row" }, [
        el("code", { className: "cmd-code", textContent: err.downloadCommand }),
        copyBtn,
      ])
    );
  }

  return el("div", { className: "error-box", role: "alert" }, children);
}

export function renderEmptyState(examples, onSelectExample) {
  const chips = (examples || []).slice(0, 3).map((ex) =>
    el("button", {
      type: "button",
      className: "example-chip",
      textContent: ex,
      onClick: () => onSelectExample(ex),
    })
  );

  return el("div", { className: "empty-state" }, [
    el("h2", { className: "section-title", textContent: "Getting started" }),
    el("p", {
      textContent:
        "Type a Telugu sentence on the left or choose a treebank example to inspect automatic POS tags, dependency links, and pattern checks.",
    }),
    el("p", {
      textContent:
        "All labels are produced automatically by Stanza (UD Telugu-MTG) and may contain errors.",
    }),
    chips.length > 0
      ? el("div", { className: "example-chips" }, chips)
      : null,
  ]);
}

export function renderSummarySection(analysis) {
  const summary = analysis ? analysis.summary : null;
  const rows = [
    { label: "Tokens", value: summary ? String(summary.token_count) : null, te: false },
    { label: "Subject", value: summary ? summary.subject : null, te: true },
    { label: "Object", value: summary ? summary.object : null, te: true },
    { label: "Main verb", value: summary ? summary.main_verb : null, te: true },
    {
      label: "Word order",
      value: summary && summary.word_order && summary.word_order !== "N/A" ? summary.word_order : null,
      te: false,
    },
  ];

  const listItems = rows.map((r) => {
    const valText = r.value || "Not found";
    const valClasses = ["summary-value"];
    if (!r.value) {
      valClasses.push("missing");
    } else if (r.te) {
      valClasses.push("te");
    }
    return el("li", { className: "summary-item" }, [
      el("span", { className: "summary-label", textContent: r.label }),
      el("span", { className: valClasses.join(" "), textContent: valText }),
    ]);
  });

  return el("section", { className: "panel-section" }, [
    el("h2", { className: "section-title", textContent: "Summary" }),
    el("ul", { className: "summary-list" }, listItems),
    el("p", {
      className: "summary-caption",
      textContent: "Automatic summary derived from the dependency parse.",
    }),
  ]);
}

export function renderWordsTab(analysis) {
  const tokens = analysis.tokens || [];
  const thead = el("thead", {}, [
    el("tr", {}, [
      el("th", { className: "num", textContent: "#" }),
      el("th", { textContent: "Word" }),
      el("th", { textContent: "ISO 15919" }),
      el("th", { textContent: "POS" }),
      el("th", { textContent: "Head" }),
      el("th", { textContent: "Relation" }),
      el("th", {}, [
        document.createTextNode("Possible suffix"),
        el("span", { className: "exp-subhead", textContent: "Experimental, unvalidated" }),
      ]),
    ]),
  ]);

  const tbody = el(
    "tbody",
    {},
    tokens.map((tok) => {
      const suffixText = tok.possible_suffix || "-";
      const headDisplay = tok.head_word
        ? `${tok.head_word} (${tok.head_id})`
        : String(tok.head_id);

      return el("tr", {}, [
        el("td", { className: "num", textContent: String(tok.id) }),
        el("td", { className: "word-cell", textContent: tok.word }),
        el("td", { className: "mono", textContent: tok.transliteration_iso15919 || "" }),
        el("td", {}, [
          el("span", {
            className: `chip ${getPosChipClass(tok.upos)}`,
            textContent: tok.upos,
            title: tok.upos_name || tok.upos,
          }),
        ]),
        el("td", { className: "te", style: "white-space: nowrap;", textContent: headDisplay }),
        el("td", {}, [
          el("div", { className: "rel-cell" }, [
            el("span", { className: "rel-code", textContent: tok.deprel }),
            el("span", { className: "rel-gloss", textContent: tok.deprel_gloss || "" }),
          ]),
        ]),
        el("td", { className: "te", style: "white-space: nowrap; font-size: 15px;", textContent: suffixText }),
      ]);
    })
  );

  const tableWrap = el("div", { className: "table-wrap" }, [
    el("table", { className: "data-table" }, [thead, tbody]),
  ]);

  // Compute POS counts for bar chart
  const posCounts = {};
  for (const tok of tokens) {
    posCounts[tok.upos] = (posCounts[tok.upos] || 0) + 1;
  }

  const chartSection = el("div", { className: "chart-section" }, [
    el("h3", { className: "section-title", textContent: "POS tag distribution" }),
    el("div", { className: "chart-wrap" }, [renderPosBarChartSvg(posCounts)]),
  ]);

  return el("div", { className: "tab-panel", role: "tabpanel" }, [tableWrap, chartSection]);
}

export function renderReliabilityStrip(reliability) {
  if (!reliability || !reliability.stanza_eval || !reliability.stanza_eval.data) {
    return null;
  }
  const testRow = reliability.stanza_eval.data.find((r) => r.split === "test");
  if (!testRow) return null;

  const fmtPct = (v) => `${(Number(v) * 100).toFixed(1)}%`;

  return el("div", { className: "reliability-strip" }, [
    el("div", { className: "reliability-metrics" }, [
      el("span", { className: "reliability-label", textContent: "Parser reliability" }),
      el("span", { className: "num", textContent: `UPOS ${fmtPct(testRow.upos_acc)}` }),
      el("span", { className: "num", textContent: `UAS ${fmtPct(testRow.uas)}` }),
      el("span", { className: "num", textContent: `LAS ${fmtPct(testRow.las)}` }),
    ]),
    el("p", {
      className: "reliability-caption",
      textContent:
        "Measured on held-out treebank sentences with gold tokenization. This is not the accuracy for the sentence you typed.",
    }),
  ]);
}

export function formatAnalysisAsText(analysis) {
  const lines = [
    `Sentence: ${analysis.input.cleaned}`,
    `Tokens: ${analysis.summary.token_count}`,
    `Subject: ${analysis.summary.subject || "Not found"}`,
    `Object: ${analysis.summary.object || "Not found"}`,
    `Main verb: ${analysis.summary.main_verb || "Not found"}`,
    `Word order: ${analysis.summary.word_order || "Not found"}`,
    "",
    "ID\tWord\tISO15919\tUPOS\tHead\tRelation\tPossibleSuffix",
  ];
  for (const t of analysis.tokens || []) {
    lines.push(
      `${t.id}\t${t.word}\t${t.transliteration_iso15919}\t${t.upos}\t${t.head_id}\t${t.deprel}\t${t.possible_suffix || "-"}`
    );
  }
  return lines.join("\n");
}
