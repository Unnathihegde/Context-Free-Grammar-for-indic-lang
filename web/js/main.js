/**
 * Application controller for Telugu Grammar Analyzer.
 */

import {
  analyzeSentence,
  fetchExamples,
  fetchHealth,
  fetchReliability,
} from "./api.js";
import { navigateTo, startRouter } from "./router.js";
import {
  el,
  formatAnalysisAsText,
  renderChecksTab,
  renderDependencyTab,
  renderEmptyState,
  renderErrorBox,
  renderReliabilityStrip,
  renderSummarySection,
  renderTreeTab,
  renderTreebankTab,
  renderWordsTab,
} from "./ui.js";

const TABS = [
  { id: "words", label: "Words" },
  { id: "dependency", label: "Dependency" },
  { id: "tree", label: "Tree" },
  { id: "checks", label: "Checks" },
  { id: "treebank", label: "Treebank" },
];

const state = {
  route: { page: "analyze", tab: "words" },
  health: null,
  examples: [],
  reliability: null,
  inputText: "",
  loading: false,
  error: null,
  analysis: null,
};

const appMain = document.getElementById("app-main");
const loadingBar = document.getElementById("loading-bar");
const statusDot = document.getElementById("model-status-dot");
const statusText = document.getElementById("model-status-text");

function setLoading(isLoading) {
  state.loading = isLoading;
  if (loadingBar) {
    loadingBar.hidden = !isLoading;
  }
}

function updateTopBar() {
  const navLinks = document.querySelectorAll(".nav-link");
  for (const link of navLinks) {
    const isActive = link.dataset.route === state.route.page;
    link.classList.toggle("active", isActive);
    if (isActive) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  }

  if (state.health) {
    if (state.health.model_loaded) {
      statusDot.className = "status-dot ready";
      statusText.textContent = "Model ready";
    } else {
      statusDot.className = "status-dot degraded";
      statusText.textContent = "Model unavailable";
    }
  }
}

async function runAnalysis(sentenceText) {
  const text = (sentenceText || "").trim();
  state.inputText = sentenceText;
  state.error = null;

  if (!text) {
    state.error = new Error("Please enter a Telugu sentence before analyzing.");
    render();
    return;
  }

  setLoading(true);
  render();
  try {
    const res = await analyzeSentence(sentenceText);
    state.analysis = res;
    state.error = null;
  } catch (err) {
    state.error = err;
  } finally {
    setLoading(false);
    render();
  }
}

function buildAnalyzeLeftColumn() {
  const textarea = el("textarea", {
    id: "sentence-textarea",
    className: "sentence-input",
    rows: "3",
    maxlength: "300",
    placeholder: "ఉదా: రాము ఇంట్లోకి వెళ్ళాడు",
    "aria-label": "Telugu sentence input",
    onInput: (e) => {
      state.inputText = e.target.value;
      const counter = document.getElementById("char-count");
      if (counter) {
        counter.textContent = `${state.inputText.length} / 300`;
      }
    },
    onKeydown: (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        runAnalysis(textarea.value);
      }
    },
  });
  textarea.value = state.inputText;

  const exampleSelect = el(
    "select",
    {
      id: "example-select",
      className: "example-select",
      "aria-label": "Choose a treebank example sentence",
      onChange: (e) => {
        if (e.target.value) {
          state.inputText = e.target.value;
          runAnalysis(e.target.value);
        }
      },
    },
    [
      el("option", { value: "", textContent: "Choose a treebank example..." }),
      ...state.examples.map((ex) => {
        const opt = el("option", { value: ex, textContent: ex });
        if (ex === state.inputText) opt.selected = true;
        return opt;
      }),
    ]
  );

  const analyzeBtn = el("button", {
    type: "button",
    className: "btn btn-primary",
    textContent: state.loading ? "Analyzing..." : "Analyze",
    disabled: state.loading,
    onClick: () => runAnalysis(textarea.value),
  });

  const clearBtn = el("button", {
    type: "button",
    className: "btn btn-secondary",
    textContent: "Clear",
    disabled: state.loading,
    onClick: () => {
      state.inputText = "";
      state.analysis = null;
      state.error = null;
      render();
      const ta = document.getElementById("sentence-textarea");
      if (ta) ta.focus();
    },
  });

  const hiddenNotice =
    state.analysis && state.analysis.input && state.analysis.input.removed_hidden_chars
      ? el("div", {
          className: "notice-box",
          role: "status",
          textContent:
            "Hidden zero-width characters were removed before automatic analysis.",
        })
      : null;

  const sentenceSection = el("section", { className: "panel-section" }, [
    el("h2", { className: "section-title", textContent: "Sentence" }),
    el("label", {
      className: "field-label",
      for: "sentence-textarea",
      textContent: "Enter one Telugu sentence (up to 300 characters)",
    }),
    textarea,
    el("div", { className: "input-meta" }, [
      el("span", { textContent: "Enter to analyze, Shift+Enter for a new line" }),
      el("span", {
        id: "char-count",
        className: "num",
        textContent: `${state.inputText.length} / 300`,
      }),
    ]),
    exampleSelect,
    el("div", { className: "btn-row" }, [analyzeBtn, clearBtn]),
    hiddenNotice,
  ]);

  return el("aside", { className: "analyze-left" }, [
    sentenceSection,
    renderSummarySection(state.analysis),
  ]);
}

function buildResultHeader(analysis) {
  const downloadBtn = el("button", {
    type: "button",
    className: "btn btn-secondary btn-sm",
    textContent: "Download JSON",
    onClick: () => {
      const blob = new Blob([JSON.stringify(analysis, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "telugu-analysis.json";
      a.click();
      URL.revokeObjectURL(url);
    },
  });

  const copyBtn = el("button", {
    type: "button",
    className: "btn btn-secondary btn-sm",
    textContent: "Copy as text",
    onClick: async () => {
      try {
        await navigator.clipboard.writeText(formatAnalysisAsText(analysis));
        copyBtn.textContent = "Copied";
        setTimeout(() => {
          copyBtn.textContent = "Copy as text";
        }, 1500);
      } catch {
        copyBtn.textContent = "Copy failed";
      }
    },
  });

  return el("div", { className: "result-header" }, [
    el("h1", {
      className: "result-sentence",
      textContent: analysis.input.cleaned,
    }),
    el("div", { className: "result-actions" }, [downloadBtn, copyBtn]),
  ]);
}

function buildTabBar(activeTab) {
  const buttons = TABS.map((t, idx) =>
    el("button", {
      type: "button",
      role: "tab",
      id: `tab-${t.id}`,
      className: "tab-btn",
      "aria-selected": String(t.id === activeTab),
      tabindex: t.id === activeTab ? "0" : "-1",
      textContent: t.label,
      onClick: () => {
        navigateTo("analyze", t.id);
      },
      onKeydown: (e) => {
        let nextIdx = null;
        if (e.key === "ArrowRight") nextIdx = (idx + 1) % TABS.length;
        if (e.key === "ArrowLeft") nextIdx = (idx - 1 + TABS.length) % TABS.length;
        if (nextIdx !== null) {
          e.preventDefault();
          const nextTab = TABS[nextIdx];
          navigateTo("analyze", nextTab.id);
          requestAnimationFrame(() => {
            const btn = document.getElementById(`tab-${nextTab.id}`);
            if (btn) btn.focus();
          });
        }
      },
    })
  );

  return el("div", { className: "tablist", role: "tablist", "aria-label": "Analysis views" }, buttons);
}

function buildActiveTabPanel(analysis, activeTab) {
  if (activeTab === "words") return renderWordsTab(analysis);
  if (activeTab === "dependency") return renderDependencyTab(analysis);
  if (activeTab === "tree") return renderTreeTab(analysis);
  if (activeTab === "checks") return renderChecksTab(analysis);
  if (activeTab === "treebank") return renderTreebankTab(analysis);
  return renderWordsTab(analysis);
}

function renderAnalyzePage() {
  const rightChildren = [];
  if (state.error) {
    rightChildren.push(renderErrorBox(state.error));
  } else if (state.analysis) {
    rightChildren.push(buildResultHeader(state.analysis));
    rightChildren.push(buildTabBar(state.route.tab));
    rightChildren.push(buildActiveTabPanel(state.analysis, state.route.tab));
  } else {
    rightChildren.push(
      renderEmptyState(state.examples, (ex) => {
        state.inputText = ex;
        runAnalysis(ex);
      })
    );
  }

  const relStrip = renderReliabilityStrip(state.reliability);
  if (relStrip) {
    rightChildren.push(relStrip);
  }

  const layout = el("div", { className: "analyze-layout" }, [
    buildAnalyzeLeftColumn(),
    el("section", { className: "analyze-right", "aria-live": "polite" }, rightChildren),
  ]);

  appMain.replaceChildren(layout);
}

function renderPlaceholderPage(title, desc) {
  appMain.replaceChildren(
    el("section", { className: "empty-state" }, [
      el("h1", { className: "section-title", textContent: title }),
      el("p", { textContent: desc }),
    ])
  );
}

function render() {
  updateTopBar();
  if (state.route.page === "models") {
    renderPlaceholderPage("Models", "The Models comparison page will be added in Step 3.");
    return;
  }
  if (state.route.page === "about") {
    renderPlaceholderPage("About", "The About page will be added in Step 3.");
    return;
  }
  renderAnalyzePage();
}

async function init() {
  startRouter((route) => {
    state.route = route;
    render();
  });

  try {
    const [health, examples, reliability] = await Promise.all([
      fetchHealth().catch(() => null),
      fetchExamples().catch(() => []),
      fetchReliability().catch(() => null),
    ]);
    state.health = health;
    state.examples = Array.isArray(examples) ? examples : [];
    state.reliability = reliability;
  } finally {
    render();
  }
}

init();
