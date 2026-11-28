"""Step 4 verification: screenshots at 1440/1024/390 px, overflow & accessibility checks."""

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "screenshots"
PORT = 8768
BASE_URL = f"http://127.0.0.1:{PORT}"

VIEWPORTS = [
    ("1440", {"width": 1440, "height": 900}),
    ("1024", {"width": 1024, "height": 800}),
    ("390", {"width": 390, "height": 844}),
]

A11Y_JS = """() => {
  const els = Array.from(document.querySelectorAll('a, button, input, select, textarea, [role="tab"]'));
  const missingName = [];
  for (const el of els) {
    if (el.offsetParent === null) continue;
    const aria = (el.getAttribute('aria-label') || '').trim();
    const text = (el.innerText || el.textContent || '').trim();
    let labelText = '';
    if (el.id) {
      const lbl = document.querySelector(`label[for="${el.id}"]`);
      if (lbl) labelText = (lbl.innerText || '').trim();
    }
    if (!aria && !text && !labelText) {
      missingName.push(el.tagName + (el.id ? '#' + el.id : ''));
    }
  }
  return {
    interactive_count: els.filter(e => e.offsetParent !== null).length,
    missing_accessible_name: missingName,
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
    overflow: document.documentElement.scrollWidth > window.innerWidth,
  };
}"""


def wait_for_server(timeout_sec: float = 60.0) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=2) as resp:
                if resp.status == 200 and json.loads(resp.read().decode("utf-8")).get("model_loaded"):
                    return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("Server did not become ready.")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.server:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        wait_for_server()
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for vp_name, vp_size in VIEWPORTS:
                page = browser.new_page(viewport=vp_size)
                console_errors = []
                page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

                # 1. Analyze page
                page.goto(f"{BASE_URL}/#/analyze/words", wait_until="networkidle")
                page.fill("#sentence-textarea", "రాము ఇంట్లోకి వెళ్ళాడు")
                page.click("button.btn-primary")
                page.wait_for_selector(".result-sentence", timeout=30000)
                page.wait_for_timeout(150)
                a11y_an = page.evaluate(A11Y_JS)
                print(f"Analyze@{vp_name}: {a11y_an}", flush=True)
                if vp_name == "1024":
                    page.screenshot(path=str(OUT_DIR / "step4_analyze_1024.png"), full_page=True)

                # 2. Models page
                page.goto(f"{BASE_URL}/#/models", wait_until="networkidle")
                page.wait_for_timeout(200)
                a11y_mod = page.evaluate(A11Y_JS)
                print(f"Models@{vp_name}: {a11y_mod}", flush=True)
                page.screenshot(path=str(OUT_DIR / f"step4_models_{vp_name}.png"), full_page=True)

                # 3. About page
                page.goto(f"{BASE_URL}/#/about", wait_until="networkidle")
                page.wait_for_timeout(150)
                a11y_abt = page.evaluate(A11Y_JS)
                print(f"About@{vp_name}: {a11y_abt}", flush=True)
                if vp_name == "1024":
                    page.screenshot(path=str(OUT_DIR / "step4_about_1024.png"), full_page=True)

                if console_errors:
                    print(f"Console errors ({vp_name}):", console_errors, flush=True)
                page.close()
            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
