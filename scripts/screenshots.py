"""Capture real screenshots and a demo video of the running Streamlit dashboard (Playwright).

Usage (dashboard must be running on port 8530):
    python scripts/screenshots.py            -> docs/screenshots/01..03 PNG + _demo.webm
    ffmpeg converts _demo.webm to demo.gif   (see scripts/make_gif.sh)
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"
URL = "http://localhost:8530"
VIEW = {"width": 1440, "height": 1200}


def wait_ready(page) -> None:
    """Wait until Streamlit has finished running the script and charts are drawn."""
    page.wait_for_selector("h1:has-text('SYNTHETIC DATA')", timeout=90000)
    # while the script runs Streamlit shows a "Stop" button in the header: wait until it has
    # been gone for 3 checks in a row, then give the charts a moment to draw
    calm = 0
    for _ in range(120):
        running = page.get_by_text("Stop", exact=True).count() > 0
        calm = 0 if running else calm + 1
        if calm >= 3:
            break
        page.wait_for_timeout(500)
    page.wait_for_timeout(2500)
    if page.locator("[data-testid='stException']").count():
        sys.exit("Streamlit shows an exception - fix the app first")


def screenshots(pw) -> None:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport=VIEW)
    for name, page_param in [("01-overview", "KPI overview"), ("02-drilldown", "Drill-down"),
                             ("03-data-quality", "Data quality")]:
        page.goto(f"{URL}/?page={page_param.replace(' ', '+')}")
        wait_ready(page)
        if name == "02-drilldown":
            # show a real filter selection: one country, two categories
            pick(page, "Country (LAND1)", ["IT"])
            pick(page, "Category (MATKL)", ["DRESSES", "FOOTWEAR"])
            wait_ready(page)
        page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)
        print("saved", name)
    browser.close()


def pick(page, label: str, values: list[str]) -> None:
    """Choose values in a Streamlit multiselect identified by its label."""
    box = page.locator("[data-testid='stMultiSelect']").filter(has_text=label)
    for v in values:
        box.locator("input").click()
        page.get_by_role("option", name=v, exact=True).click()
        page.keyboard.press("Escape")
        page.wait_for_timeout(1200)


def demo_video(pw) -> None:
    """~18 s walkthrough: overview -> scroll -> drill-down with filters -> data quality."""
    browser = pw.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1280, "height": 760},
                              record_video_dir=str(OUT / "_video"),
                              record_video_size={"width": 1280, "height": 760})
    page = ctx.new_page()
    page.set_default_timeout(60000)  # fail loudly instead of hanging
    page.goto(URL)
    wait_ready(page)
    page.wait_for_timeout(1500)
    page.mouse.wheel(0, 500)
    page.wait_for_timeout(1500)
    print("video: overview done", flush=True)
    page.get_by_text("Drill-down", exact=True).click()
    wait_ready(page)
    pick(page, "Country (LAND1)", ["IT"])
    wait_ready(page)
    page.mouse.wheel(0, 400)
    page.wait_for_timeout(1500)
    print("video: drill-down done", flush=True)
    page.get_by_text("Data quality", exact=True).click()
    wait_ready(page)
    page.wait_for_timeout(1500)
    video = page.video.path()
    ctx.close()
    browser.close()
    Path(video).replace(OUT / "_demo.webm")
    print("saved _demo.webm")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        if "--video-only" not in sys.argv:
            screenshots(p)
        if "--video" in sys.argv or "--video-only" in sys.argv:
            demo_video(p)
