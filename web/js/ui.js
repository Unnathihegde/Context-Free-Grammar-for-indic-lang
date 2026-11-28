/**
 * DOM builders for Telugu Grammar Analyzer (no innerHTML with data).
 */

import { renderDependencyArcsSvg } from "./charts/arcs.js";
import { renderPosBarChartSvg } from "./charts/bars.js";
import { renderTreeSvg } from "./charts/tree.js";
import { MODEL_COLORS, renderWhiskerChartSvg } from "./charts/whisker.js";

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

export function renderDependencyTab(analysis) {
  const tokens = analysis.tokens || [];
  let spacing = tokens.length > 5 ? 92 : 132;
  const scrollWrap = el("div", { className: "svg-scroll-wrap" });

  const redraw = (opts = {}) => {
    let targetSpacing = spacing;
    if (opts.fit && tokens.length > 0) {
      const avail = Math.max(320, scrollWrap.clientWidth - 72);
      targetSpacing = Math.max(88, Math.min(160, Math.floor(avail / tokens.length)));
      spacing = targetSpacing;
    }
    scrollWrap.replaceChildren(renderDependencyArcsSvg(tokens, { wordSpacing: targetSpacing }));
  };

  const controls = el("div", { className: "svg-controls" }, [
    el("button", {
      type: "button",
      className: "btn btn-secondary btn-sm",
      textContent: "Smaller",
      onClick: () => {
        spacing = Math.max(84, spacing - 20);
        redraw();
      },
    }),
    el("button", {
      type: "button",
      className: "btn btn-secondary btn-sm",
      textContent: "Larger",
      onClick: () => {
        spacing = Math.min(200, spacing + 20);
        redraw();
      },
    }),
    el("button", {
      type: "button",
      className: "btn btn-secondary btn-sm",
      textContent: "Fit",
      onClick: () => redraw({ fit: true }),
    }),
  ]);

  redraw();

  // Relation legend for relations present in this sentence
  const seenRels = new Map();
  for (const t of tokens) {
    if (t.deprel && !seenRels.has(t.deprel)) {
      seenRels.set(t.deprel, t.deprel_gloss || "");
    }
  }
  const legendItems = Array.from(seenRels.entries()).map(([code, gloss]) =>
    el("li", { className: "legend-item" }, [
      el("span", { className: "rel-code", textContent: code }),
      el("span", { className: "rel-gloss", textContent: gloss }),
    ])
  );

  const legendSection = el("div", { className: "chart-section" }, [
    el("h3", { className: "section-title", textContent: "Relations in this sentence" }),
    el("ul", { className: "legend-list" }, legendItems),
  ]);

  return el("div", { className: "tab-panel", role: "tabpanel" }, [
    controls,
    scrollWrap,
    legendSection,
  ]);
}

export function renderTreeTab(analysis) {
  const tree = analysis.tree || {};
  const coveredText = tree.pcfg_covered
    ? `Covered by the learned grammar (Viterbi probability: ${
        tree.viterbi_prob !== null && tree.viterbi_prob !== undefined
          ? Number(tree.viterbi_prob).toExponential(3)
          : "N/A"
      }).`
    : "Not covered by the learned grammar (not an error).";

  const statusChipClass = tree.pcfg_covered ? "chip-consistent" : "chip-na";
  const coverageLine = el("div", { className: "coverage-line" }, [
    el("span", {
      className: `chip ${statusChipClass}`,
      textContent: tree.pcfg_covered ? "Covered" : "Not covered",
    }),
    el("span", { textContent: coveredText }),
  ]);

  const explanation = el("p", {
    className: "muted-note",
    textContent:
      "A Context-Free Grammar (CFG) tree groups words into nested phrases projected from the dependency parse. Non-terminal labels show phrase types (such as VERB_P), and leaves show the Telugu words.",
  });

  const treeBox = tree.bracketed
    ? el("div", { className: "svg-scroll-wrap" }, [renderTreeSvg(tree.bracketed)])
    : el("div", { className: "notice-box", textContent: "No projective phrase-structure tree available for this sentence." });

  const bracketDetails = tree.bracketed
    ? el("details", { className: "bracket-details" }, [
        el("summary", { textContent: "Bracketed form" }),
        el("pre", { className: "mono bracket-pre", textContent: tree.bracketed }),
      ])
    : null;

  const productions = tree.productions || [];
  let rulesSection = null;
  if (productions.length > 0) {
    const thead = el("thead", {}, [
      el("tr", {}, [
        el("th", { textContent: "Rule" }),
        el("th", { className: "num", textContent: "Probability" }),
      ]),
    ]);
    const tbody = el(
      "tbody",
      {},
      productions.map((p) =>
        el("tr", {}, [
          el("td", { className: "mono", textContent: p.rule }),
          el("td", {
            className: "num",
            textContent:
              p.prob !== null && p.prob !== undefined
                ? Number(p.prob).toFixed(5)
                : p.reason || "null",
          }),
        ])
      )
    );
    rulesSection = el("div", { className: "chart-section" }, [
      el("h3", { className: "section-title", textContent: "Rules used" }),
      el("div", { className: "table-wrap" }, [
        el("table", { className: "data-table" }, [thead, tbody]),
      ]),
    ]);
  }

  return el("div", { className: "tab-panel", role: "tabpanel" }, [
    coverageLine,
    explanation,
    treeBox,
    bracketDetails,
    rulesSection,
  ]);
}

function getCheckStatusInfo(status) {
  const s = (status || "").toLowerCase();
  if (s === "consistent" || s === "none missing") {
    return { cls: "chip-consistent", label: s === "consistent" ? "Consistent" : "None missing" };
  }
  if (s === "not consistent") {
    return { cls: "chip-not-consistent", label: "Not consistent" };
  }
  if (s === "some missing") {
    return { cls: "chip-unknown", label: "Some missing" };
  }
  return { cls: "chip-na", label: "Not applicable" };
}

export function renderChecksTab(analysis) {
  const checks = analysis.checks || [];
  const caveat = el("p", {
    className: "muted-note",
    textContent:
      "These are pattern checks learned from a small treebank. They are not a full grammar checker, and a sentence that is not consistent with a pattern is not necessarily wrong (Telugu word order is flexible).",
  });

  const thead = el("thead", {}, [
    el("tr", {}, [
      el("th", { textContent: "Check" }),
      el("th", { textContent: "Status" }),
      el("th", { textContent: "Explanation" }),
    ]),
  ]);

  const tbody = el(
    "tbody",
    {},
    checks.map((chk) => {
      const st = getCheckStatusInfo(chk.status);
      const labelCell = chk.experimental
        ? el("td", {}, [
            el("div", { textContent: chk.label }),
            el("span", { className: "exp-subhead", textContent: "Experimental, unvalidated" }),
          ])
        : el("td", { textContent: chk.label });

      return el("tr", {}, [
        labelCell,
        el("td", {}, [el("span", { className: `chip ${st.cls}`, textContent: st.label })]),
        el("td", { textContent: chk.explanation }),
      ]);
    })
  );

  return el("div", { className: "tab-panel", role: "tabpanel" }, [
    caveat,
    el("div", { className: "table-wrap" }, [
      el("table", { className: "data-table" }, [thead, tbody]),
    ]),
  ]);
}

export function renderTreebankTab(analysis) {
  const tm = analysis.treebank_match;
  if (!tm || !tm.found) {
    return el("div", { className: "tab-panel", role: "tabpanel" }, [
      el("div", {
        className: "notice-box",
        textContent: "Available for treebank sentences only.",
      }),
    ]);
  }

  const children = [
    el("div", { className: "coverage-line" }, [
      el("span", { className: "chip chip-consistent", textContent: `Split: ${tm.split}` }),
      el("span", {
        className: "num",
        textContent: `UPOS ${(tm.metrics.upos_accuracy * 100).toFixed(1)}% | UAS ${(tm.metrics.uas * 100).toFixed(1)}% | LAS ${(tm.metrics.las * 100).toFixed(1)}%`,
      }),
    ]),
  ];

  if (tm.split === "train") {
    children.push(
      el("div", {
        className: "notice-box",
        textContent:
          "This sentence was in the model's training data, so these scores do not measure accuracy.",
      })
    );
  }

  const predTokens = analysis.tokens || [];
  const thead = el("thead", {}, [
    el("tr", {}, [
      el("th", { className: "num", textContent: "#" }),
      el("th", { textContent: "Word" }),
      el("th", { textContent: "Gold POS" }),
      el("th", { textContent: "Pred POS" }),
      el("th", { className: "num", textContent: "Gold Head" }),
      el("th", { className: "num", textContent: "Pred Head" }),
      el("th", { textContent: "Gold Rel" }),
      el("th", { textContent: "Pred Rel" }),
    ]),
  ]);

  const makePredCell = (predVal, goldVal, isNum = false) => {
    const differs = String(predVal) !== String(goldVal);
    const cls = [isNum ? "num" : "", differs ? "cell-diff" : ""].filter(Boolean).join(" ");
    if (!differs) {
      return el("td", { className: cls, textContent: String(predVal) });
    }
    return el("td", { className: cls }, [
      el("span", { textContent: String(predVal) }),
      el("span", { className: "diff-badge", textContent: "differs" }),
    ]);
  };

  const tbody = el(
    "tbody",
    {},
    (tm.gold || []).map((g, idx) => {
      const pred = predTokens[idx] || {};
      return el("tr", {}, [
        el("td", { className: "num", textContent: String(g.id) }),
        el("td", { className: "word-cell", textContent: g.word }),
        el("td", { textContent: g.pos }),
        makePredCell(pred.upos ?? "-", g.pos),
        el("td", { className: "num", textContent: String(g.head) }),
        makePredCell(pred.head_id ?? "-", g.head, true),
        el("td", { textContent: g.rel }),
        makePredCell(pred.deprel ?? "-", g.rel),
      ]);
    })
  );

  children.push(
    el("div", { className: "table-wrap", style: "margin-top: 12px;" }, [
      el("table", { className: "data-table" }, [thead, tbody]),
    ])
  );

  return el("div", { className: "tab-panel", role: "tabpanel" }, children);
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

function fmtCi(low, high) {
  if (low === null || low === undefined || high === null || high === undefined) {
    return "-";
  }
  return `[${Number(low).toFixed(3)}, ${Number(high).toFixed(3)}]`;
}

export function renderModelsPage(modelsData, reliabilityData) {
  if (!modelsData || !modelsData.rows) {
    return el("div", { className: "notice-box" }, [
      el("p", {
        textContent:
          (modelsData && modelsData.message) ||
          "Model comparison results are not available yet.",
      }),
    ]);
  }

  const rows = modelsData.rows || [];
  const caveats = modelsData.caveats || {};

  // 1. Part-of-speech tagging section
  const posRows = rows.filter((r) => r.metric === "upos_acc");
  const testPosRows = posRows.filter((r) => r.task === "upos_acc:test");
  const posChartGroups = [
    {
      groupLabel: "Test UPOS (n = 721)",
      items: testPosRows.map((r) => ({
        label: r.model,
        value: Number(r.value),
        ciLow: r.ci_low !== null ? Number(r.ci_low) : null,
        ciHigh: r.ci_high !== null ? Number(r.ci_high) : null,
      })),
    },
  ];

  const extractShortPosNote = (notesStr) => {
    const s = String(notesStr || "");
    const parts = [];
    if (s.includes("gold tokenization")) parts.push("gold tokenization");
    const pMatch = s.match(/paired bootstrap p vs Stanza\s*=\s*([0-9.]+)/);
    if (pMatch) parts.push(`paired p vs Stanza = ${pMatch[1]}`);
    return parts.join("; ") || s;
  };

  const trainingDetails = [];
  for (const r of posRows) {
    const tMatch = String(r.notes || "").match(/train_time=([^\s;]+(?:\s*\([^)]+\))?)/);
    if (tMatch && !trainingDetails.some((d) => d.startsWith(r.model))) {
      trainingDetails.push(`${r.model}: ${tMatch[1]}`);
    }
  }

  const posTable = el("div", { className: "table-wrap" }, [
    el("table", { className: "data-table" }, [
      el("thead", {}, [
        el("tr", {}, [
          el("th", { textContent: "Model" }),
          el("th", { textContent: "Split" }),
          el("th", { className: "num", textContent: "UPOS" }),
          el("th", { textContent: "95% CI" }),
          el("th", { className: "num", textContent: "n" }),
          el("th", { textContent: "Notes" }),
        ]),
      ]),
      el(
        "tbody",
        {},
        posRows.map((r) =>
          el("tr", {}, [
            el("td", { textContent: r.model }),
            el("td", { textContent: r.task.replace("upos_acc:", "") }),
            el("td", { className: "num", textContent: Number(r.value).toFixed(4) }),
            el("td", { className: "ci-cell", textContent: fmtCi(r.ci_low, r.ci_high) }),
            el("td", { className: "num", textContent: String(r.n) }),
            el("td", { textContent: extractShortPosNote(r.notes) }),
          ])
        )
      ),
    ]),
  ]);

  const trainingDetailsEl = trainingDetails.length
    ? el("details", { className: "bracket-details" }, [
        el("summary", { textContent: "Training details" }),
        el("p", { className: "muted-note", style: "margin-top: 6px;", textContent: trainingDetails.join(" | ") }),
      ])
    : null;

  const findPosRow = (modelSubstr, split) =>
    posRows.find((r) => r.task === `upos_acc:${split}` && r.model.includes(modelSubstr));
  const extractP = (row) => {
    const m = String((row && row.notes) || "").match(/paired bootstrap p vs Stanza\s*=\s*([0-9.]+)/);
    return m ? m[1] : null;
  };

  const stanzaTest = findPosRow("Stanza", "test");
  const xlmrTest = findPosRow("xlm-roberta", "test");
  const murilDev = findPosRow("muril", "dev");
  const murilTest = findPosRow("muril", "test");

  let posInterp =
    "On held-out test tokens with gold tokenization, fine-tuned xlm-roberta-base and Stanza achieve similar UPOS accuracy with overlapping 95% confidence intervals.";
  if (stanzaTest && xlmrTest && murilDev && murilTest) {
    const pXlmr = extractP(xlmrTest);
    const pMurilDev = extractP(murilDev);
    const pMurilTest = extractP(murilTest);
    posInterp =
      `On held-out test tokens with gold tokenization, xlm-roberta-base (${Number(xlmrTest.value).toFixed(4)}) and Stanza (${Number(stanzaTest.value).toFixed(4)}) achieve similar UPOS accuracy with overlapping 95% confidence intervals` +
      (pXlmr ? ` (paired p = ${pXlmr}). ` : ". ") +
      `google/muril-base-cased reaches ${Number(murilTest.value).toFixed(4)} on test` +
      (pMurilDev && pMurilTest
        ? ` (paired p vs Stanza = ${pMurilDev} on dev, ${pMurilTest} on test).`
        : ".");
  }

  const posSection = el("section", { className: "page-section" }, [
    el("h2", { className: "section-title", textContent: "Part-of-speech tagging" }),
    el("div", { className: "chart-wrap", style: "margin-bottom: 16px;" }, [
      renderWhiskerChartSvg(posChartGroups, {
        width: 920,
        minDomain: 0.85,
        maxDomain: 1.0,
        xAxisLabel: "Test UPOS accuracy",
        ariaLabel: "Test UPOS accuracy with 95% confidence intervals",
      }),
    ]),
    posTable,
    trainingDetailsEl,
    el("p", {
      className: "muted-note",
      style: "margin-top: 12px;",
      textContent: posInterp,
    }),
  ]);

  // 2. Word-order pairs section
  const woRows = rows.filter((r) => r.task.startsWith("word_order:"));
  const kindOrder = ["amod_after", "case_before", "det_after", "verb_first", "ALL"];
  const woGroups = kindOrder
    .map((kind) => {
      const kRows = woRows.filter((r) => r.task === `word_order:${kind}`);
      return {
        groupLabel: kind,
        items: kRows.map((r) => ({
          label: r.model,
          value: Number(r.value),
          ciLow: r.ci_low !== null ? Number(r.ci_low) : null,
          ciHigh: r.ci_high !== null ? Number(r.ci_high) : null,
        })),
      };
    })
    .filter((g) => g.items.length > 0);

  const legendItems = Object.entries({
    "POS-bigram (POS)": MODEL_COLORS["POS-bigram (POS)"],
    "Learned PCFG (POS)": MODEL_COLORS["Learned PCFG (POS)"],
    "PLL (xlm-roberta-base)": MODEL_COLORS["PLL (xlm-roberta-base)"],
    "PLL (google/muril-base-cased)": MODEL_COLORS["PLL (google/muril-base-cased)"],
  }).map(([name, color]) =>
    el("span", { className: "whisker-legend-item" }, [
      el("span", { className: "whisker-swatch", style: `background: ${color};` }),
      el("span", { textContent: name }),
    ])
  );

  const woTable = el("div", { className: "table-wrap" }, [
    el("table", { className: "data-table" }, [
      el("thead", {}, [
        el("tr", {}, [
          el("th", { textContent: "Kind" }),
          el("th", { textContent: "Model" }),
          el("th", { className: "num", textContent: "Accuracy" }),
          el("th", { textContent: "95% CI" }),
          el("th", { className: "num", textContent: "n" }),
          el("th", { textContent: "Notes / p-value" }),
        ]),
      ]),
      el(
        "tbody",
        {},
        woRows.map((r) =>
          el("tr", {}, [
            el("td", { className: "mono", textContent: r.task.replace("word_order:", "") }),
            el("td", { textContent: r.model }),
            el("td", { className: "num", textContent: Number(r.value).toFixed(4) }),
            el("td", { className: "ci-cell", textContent: fmtCi(r.ci_low, r.ci_high) }),
            el("td", { className: "num", textContent: String(r.n) }),
            el("td", { textContent: r.notes || "" }),
          ])
        )
      ),
    ]),
  ]);

  const cleanCaveat = (txt) =>
    String(txt || "")
      .replace(/\*\*/g, "")
      .replace(/`/g, "")
      .replace(/\$([^$]+)\$/g, "$1");

  const caveatKeys = [
    ["Pretraining leakage caveat", caveats.pretraining_leakage],
    ["Multiple comparisons", caveats.multiple_comparisons],
    ["Small per-tag counts", caveats.small_tag_counts],
    ["MuRIL rare-tag accuracy", caveats.muril_rare_tags],
  ]
    .filter(([, txt]) => Boolean(txt))
    .map(([title, txt]) => [title, cleanCaveat(txt)]);

  const caveatBlock = caveatKeys.length
    ? el(
        "div",
        { className: "notice-box", style: "margin-top: 16px;" },
        caveatKeys.map(([title, txt]) =>
          el("p", { style: "margin: 0 0 8px 0;" }, [
            el("strong", { textContent: `${title}: ` }),
            el("span", { textContent: txt }),
          ])
        )
      )
    : null;

  const woSection = el("section", { className: "page-section" }, [
    el("h2", { className: "section-title", textContent: "Word-order pairs" }),
    el("div", { className: "whisker-legend" }, legendItems),
    el("div", { className: "chart-wrap", style: "margin-bottom: 16px;" }, [
      renderWhiskerChartSvg(woGroups, {
        width: 720,
        minDomain: 0.55,
        maxDomain: 1.0,
        ariaLabel: "Word-order pair ranking accuracy with 95% confidence intervals",
      }),
    ]),
    woTable,
    el("p", {
      className: "muted-note",
      style: "margin-top: 12px;",
      textContent:
        "Across all 1,118 minimal pairs, the local POS-bigram baseline outperforms the hierarchical PCFG and both masked-LM PLL scorers, driven by verb_first pairs (n = 853); PLL scores higher on case_before (n = 56) but may reflect pretraining exposure.",
    }),
    caveatBlock,
  ]);

  // 3. Agreement & data-size section from /api/reliability
  const relChildren = [
    el("h2", { className: "section-title", textContent: "Agreement and data-size results" }),
  ];

  if (reliabilityData) {
    const ag = reliabilityData.agreement_results || {};
    const ds = reliabilityData.datasize_curve || {};

    relChildren.push(
      el("div", { className: "notice-box", style: "margin-bottom: 12px;" }, [
        el("span", {
          className: `chip ${ag.reportable ? "chip-consistent" : "chip-unknown"}`,
          textContent: ag.reportable ? "Reportable" : "Experimental, unvalidated",
        }),
        el("p", {
          style: "margin: 6px 0 0 0;",
          textContent: ag.reportable
            ? "Agreement results meet reportability criteria."
            : `Not reportable: ${ag.reportability_reason || "Validation incomplete."}`,
        }),
      ])
    );

    if (Array.isArray(ag.data) && ag.data.length > 0) {
      relChildren.push(
        el("div", { className: "table-wrap", style: "margin-bottom: 16px;" }, [
          el("table", { className: "data-table" }, [
            el("thead", {}, [
              el("tr", {}, [
                el("th", { textContent: "Source" }),
                el("th", { className: "num", textContent: "Pairs" }),
                el("th", { className: "num", textContent: "B1 Acc" }),
                el("th", { className: "num", textContent: "G Acc" }),
                el("th", { className: "num", textContent: "Hybrid Acc" }),
                el("th", { textContent: "Status" }),
              ]),
            ]),
            el(
              "tbody",
              {},
              ag.data.map((r) =>
                el("tr", {}, [
                  el("td", { textContent: r.source || "" }),
                  el("td", { className: "num", textContent: String(r.n_pairs ?? "-") }),
                  el("td", { className: "num", textContent: r.b1_acc != null ? Number(r.b1_acc).toFixed(3) : "-" }),
                  el("td", { className: "num", textContent: r.g_acc != null ? Number(r.g_acc).toFixed(3) : "-" }),
                  el("td", { className: "num", textContent: r.hybrid_acc != null ? Number(r.hybrid_acc).toFixed(3) : "-" }),
                  el("td", { textContent: r.table_status || "unvalidated" }),
                ])
              )
            ),
          ]),
        ])
      );
    }

    if (Array.isArray(ds.data) && ds.data.length > 0) {
      relChildren.push(
        el("div", { className: "table-wrap" }, [
          el("table", { className: "data-table" }, [
            el("thead", {}, [
              el("tr", {}, [
                el("th", { textContent: "Source" }),
                el("th", { className: "num", textContent: "Requested N" }),
                el("th", { className: "num", textContent: "LM Sentences" }),
                el("th", { className: "num", textContent: "B1 Acc" }),
                el("th", { textContent: "LM Mode" }),
              ]),
            ]),
            el(
              "tbody",
              {},
              ds.data.map((r) =>
                el("tr", {}, [
                  el("td", { textContent: r.source || "" }),
                  el("td", { className: "num", textContent: String(r.requested_n ?? "-") }),
                  el("td", { className: "num", textContent: String(r.lm_training_sentences ?? "-") }),
                  el("td", { className: "num", textContent: r.b1_acc != null ? Number(r.b1_acc).toFixed(3) : "-" }),
                  el("td", { textContent: r.lm_mode || "-" }),
                ])
              )
            ),
          ]),
        ])
      );
    }
  }

  const relSection = el("section", { className: "page-section" }, relChildren);

  return el("div", { className: "doc-page" }, [posSection, woSection, relSection]);
}

export function renderAboutPage() {
  const paragraphs = [
    [
      "1. What this project is",
      "Telugu Grammar Analyzer is an empirical mini-project studying Context-Free Grammar (CFG) induction and syntactic pattern checking for Telugu, an agglutinative, head-final Dravidian language. It provides an interactive viewer over automatic Universal Dependencies parses alongside transparent evaluation metrics.",
    ],
    [
      "2. How the grammar is learned from the treebank",
      "Dependency trees from the Universal Dependencies Telugu-MTG treebank (1,328 sentences total; 1,326 usable after filtering multi-root and non-projective trees) are converted into projective phrase-structure trees via head-outward projection after removing punctuation. The trees are binarized into Chomsky Normal Form (horzMarkov=1) to induce a 375-rule PCFG over coarse UPOS tags.",
    ],
    [
      "3. What the pattern checks do",
      "The syntactic checks inspect the automatic Stanza dependency parse for canonical Telugu word-order tendencies (sentence-final root verbs, determiners and adjectives before head nouns, postpositions after head nouns), words absent from the 1,051-sentence training vocabulary, and an experimental pronoun-verb agreement heuristic. These are descriptive pattern checks, not a full grammar checker.",
    ],
    [
      "4. What was measured",
      "On held-out UD Telugu-MTG splits with gold tokenization, Stanza 1.15.1 achieves 0.942 UPOS accuracy, 0.920 UAS, and 0.818 LAS on test (146 sentences, 721 tokens), while fine-tuned xlm-roberta-base reaches 0.947 UPOS (difference vs. Stanza not statistically significant, p = 0.524). Across 1,118 minimal word-order pairs in 5-fold CV, a local POS-bigram baseline (0.967) outperformed the learned POS-level PCFG (0.944, p = 0.002).",
    ],
    [
      "5. What was not measured",
      "Because UD Telugu-MTG leaves LEMMA and FEATS unpopulated and contains short pedagogical sentences (mean ~4.9 tokens), morphological inflection, long-range colloquial discourse, and non-projective scrambling are not evaluated. Masked-LM pseudo-log-likelihood scores may reflect pretraining exposure to web text.",
    ],
    [
      "6. Limitations",
      "The subject-verb agreement table and suffix column are experimental and unvalidated, and agreement evaluation results are marked non-reportable until native-speaker validation is completed. All automatic parses and transliterations (ISO 15919) may contain errors.",
    ],
  ];

  return el("div", { className: "doc-page" }, [
    el("section", { className: "page-section" }, [
      el("h1", { className: "section-title", textContent: "About Telugu Grammar Analyzer" }),
      ...paragraphs.map(([heading, body]) =>
        el("div", { className: "about-block" }, [
          el("h2", { className: "about-heading", textContent: heading }),
          el("p", { className: "about-body", textContent: body }),
        ])
      ),
    ]),
    el("section", { className: "page-section" }, [
      el("h2", { className: "section-title", textContent: "Treebank source & licence" }),
      el("p", {
        className: "about-body",
        textContent:
          "Treebank data: Universal Dependencies Telugu-MTG (UD_Telugu-MTG), licensed under Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0). Automatic parsing is powered by Stanza (UD Telugu-MTG).",
      }),
    ]),
  ]);
}
