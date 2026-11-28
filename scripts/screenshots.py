"""Take Playwright screenshots of every Analyze tab for the 3 target sentences at 1440 and 390 px."""

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "screenshots"
PORT = 8765
BASE_URL = f"http://127.0.0.1:{PORT}"

SENTENCES = [
    ("s1", "రాము ఇంట్లోకి వెళ్ళాడు"),
    ("s2", "నేను పుస్తకం చదివాను ."),
    ("s3", "రాము నేను రేపు వెళ్తాను అని కమలతో చెప్పేడు ."),
]
TABS = ["words", "dependency", "tree", "checks", "treebank"]
VIEWPORTS = [("1440", {"width": 1440, "height": 900}), ("390", {"width": 390, "height": 844})]


def wait_for_server(timeout_sec: float = 60.0) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=2) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("model_loaded"):
                        return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("Server did not become ready with model_loaded=True within timeout.")


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
        print("Server ready at", BASE_URL, flush=True)

        with sync_playwright() as p:
            browser = p.chromium.launch()
            for vp_name, vp_size in VIEWPORTS:
                page = browser.new_page(viewport=vp_size)
                console_errors = []
                page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
                page.goto(BASE_URL, wait_until="networkidle")

                for s_key, sentence in SENTENCES:
                    page.fill("#sentence-textarea", sentence)
                    page.click("button.btn-primary")
                    page.wait_for_function(
                        "expected => document.querySelector('.result-sentence')?.textContent?.trim() === expected",
                        arg=sentence,
                        timeout=30000,
                    )
                    for tab in TABS:
                        page.click(f"#tab-{tab}")
                        page.wait_for_timeout(150)
                        scroll_w = page.evaluate("document.documentElement.scrollWidth")
                        inner_w = page.evaluate("window.innerWidth")
                        overflow = scroll_w > inner_w
                        out_path = OUT_DIR / f"step2_{s_key}_{tab}_{vp_name}.png"
                        page.screenshot(path=str(out_path), full_page=True)
                        print(
                            f"{out_path.name} | scrollWidth={scroll_w} innerWidth={inner_w} overflow={overflow}",
                            flush=True,
                        )
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
