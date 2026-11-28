/**
 * API client helpers for Telugu Grammar Analyzer.
 * All requests target the same-origin FastAPI backend.
 */

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const err = new Error(
      (data && data.message) || `Request failed with status ${response.status}`
    );
    err.status = response.status;
    err.downloadCommand = data && data.download_command ? data.download_command : null;
    throw err;
  }
  return data;
}

export function fetchHealth() {
  return requestJson("/api/health");
}

export function fetchExamples() {
  return requestJson("/api/examples");
}

export function fetchReliability() {
  return requestJson("/api/reliability");
}

export function fetchModels() {
  return requestJson("/api/models");
}

export function analyzeSentence(sentence) {
  return requestJson("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sentence }),
  });
}
