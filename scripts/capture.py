"""Two small capture helpers (Playwright):

    python scripts/capture.py log logs/pipeline_run.log docs/screenshots/05-pipeline-run.png
        renders the REAL stdout of a pipeline run (captured with tee) as a terminal-style PNG

    python scripts/capture.py url <actions-run-url> docs/screenshots/06-ci-passing.png
        screenshots a public web page, e.g. the green GitHub Actions run
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def render_log(log_path: str, out: str) -> None:
    text = Path(log_path).read_text(encoding="utf-8")
    page_html = f"""<html><body style="margin:0;background:#1e1e1e">
    <div style="padding:14px 18px;font:13px Consolas,monospace;color:#9cdcfe">
    $ python -m src.pipeline | tee logs/pipeline_run.log</div>
    <pre style="margin:0;padding:0 18px 18px;font:13px/1.45 Consolas,monospace;color:#d4d4d4;
    white-space:pre-wrap">{html.escape(text)}</pre></body></html>"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1250, "height": 400})
        page.set_content(page_html)
        page.screenshot(path=out, full_page=True)
        browser.close()


def capture_url(url: str, out: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(2000)
        page.screenshot(path=out)
        browser.close()


if __name__ == "__main__":
    mode, src, dst = sys.argv[1:4]
    if mode == "log":
        render_log(src, dst)
    else:
        capture_url(src, dst)
    print("saved", dst)
