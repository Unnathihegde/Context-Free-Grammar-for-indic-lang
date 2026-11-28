"""Check bounding-box overlaps among dependency arc pills and word/POS labels."""

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PORT = 8766
BASE_URL = f"http://127.0.0.1:{PORT}"

SENTENCES = [
    "రాము నేను రేపు వెళ్తాను అని కమలతో చెప్పేడు .",
    "నేను ఆ పని చెయ్యాల్సి వచ్చింది .",
]


def main() -> None:
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.server:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        for _ in range(120):
            try:
                with urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=2) as r:
                    if json.loads(r.read().decode()).get("model_loaded"):
                        break
            except Exception:
                pass
            time.sleep(0.5)

        js_check = """() => {
          const svg = document.querySelector('.svg-scroll-wrap svg');
          const pills = Array.from(svg.querySelectorAll('g rect')).map(r => r.getBoundingClientRect());
          const words = Array.from(svg.querySelectorAll('svg > text')).map(t => t.getBoundingClientRect());
          const overlap = (a, b) => !(a.right <= b.left || a.left >= b.right || a.bottom <= b.top || a.top >= b.bottom);
          let pillPill = 0, pillWord = 0;
          for (let i = 0; i < pills.length; i++) {
            for (let j = i + 1; j < pills.length; j++) {
              if (overlap(pills[i], pills[j])) pillPill++;
            }
            for (const w of words) {
              if (overlap(pills[i], w)) pillWord++;
            }
          }
          return { pills: pills.length, words: words.length, pill_pill_overlaps: pillPill, pill_word_overlaps: pillWord };
        }"""

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(f"{BASE_URL}/#/analyze/dependency", wait_until="networkidle")
            for s in SENTENCES:
                page.fill("#sentence-textarea", s)
                page.click("button.btn-primary")
                page.wait_for_function(
                    "exp => document.querySelector('.result-sentence')?.textContent?.trim() === exp",
                    arg=s,
                    timeout=30000,
                )
                page.click("#tab-dependency")
                page.wait_for_timeout(150)
                res = page.evaluate(js_check)
                print(f"{s} -> {res}", flush=True)
            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
