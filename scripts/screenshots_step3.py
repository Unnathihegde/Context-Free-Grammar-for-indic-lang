"""Take Playwright screenshots of Models and About pages (Step 3) + Dependency check."""

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "screenshots"
PORT = 8767
BASE_URL = f"http://127.0.0.1:{PORT}"

VIEWPORTS = [("1440", {"width": 1440, "height": 900}), ("390", {"width": 390, "height": 844})]


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

                for route_name, hash_url in [("models", "#/models"), ("about", "#/about")]:
                    page.goto(f"{BASE_URL}/{hash_url}", wait_until="networkidle")
                    page.wait_for_timeout(300)
                    scroll_w = page.evaluate("document.documentElement.scrollWidth")
                    inner_w = page.evaluate("window.innerWidth")
                    out_path = OUT_DIR / f"step3_{route_name}_{vp_name}.png"
                    page.screenshot(path=str(out_path), full_page=True)
                    print(
                        f"{out_path.name} | scrollWidth={scroll_w} innerWidth={inner_w} "
                        f"overflow={scroll_w > inner_w}",
                        flush=True,
                    )

                # Also screenshot the updated Dependency tab for the 6-token sentence
                page.goto(f"{BASE_URL}/#/analyze/dependency", wait_until="networkidle")
                s6 = "నేను ఆ పని చెయ్యాల్సి వచ్చింది ."
                page.fill("#sentence-textarea", s6)
                page.click("button.btn-primary")
                page.wait_for_function(
                    "exp => document.querySelector('.result-sentence')?.textContent?.trim() === exp",
                    arg=s6,
                    timeout=30000,
                )
                page.click("#tab-dependency")
                page.wait_for_timeout(150)
                scroll_w = page.evaluate("document.documentElement.scrollWidth")
                inner_w = page.evaluate("window.innerWidth")
                out_dep = OUT_DIR / f"step3_dep6_{vp_name}.png"
                page.screenshot(path=str(out_dep), full_page=True)
                print(
                    f"{out_dep.name} | scrollWidth={scroll_w} innerWidth={inner_w} "
                    f"overflow={scroll_w > inner_w}",
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
