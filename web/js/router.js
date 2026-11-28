/**
 * Hash-based router for #/analyze[/tab], #/models, #/about.
 */

const VALID_PAGES = new Set(["analyze", "models", "about"]);
const VALID_TABS = new Set(["words", "dependency", "tree", "checks", "treebank"]);

export function parseHash(hashStr) {
  const cleaned = (hashStr || "").replace(/^#\/?/, "").trim();
  if (!cleaned) {
    return { page: "analyze", tab: "words" };
  }
  const parts = cleaned.split("/").filter(Boolean);
  const page = VALID_PAGES.has(parts[0]) ? parts[0] : "analyze";
  let tab = "words";
  if (page === "analyze" && parts[1] && VALID_TABS.has(parts[1])) {
    tab = parts[1];
  }
  return { page, tab };
}

export function navigateTo(page, tab = "words") {
  const target = page === "analyze" ? `#/analyze/${tab}` : `#/${page}`;
  if (window.location.hash !== target) {
    window.location.hash = target;
  }
}

export function startRouter(onRouteChange) {
  const handle = () => onRouteChange(parseHash(window.location.hash));
  window.addEventListener("hashchange", handle);
  handle();
  return () => window.removeEventListener("hashchange", handle);
}
