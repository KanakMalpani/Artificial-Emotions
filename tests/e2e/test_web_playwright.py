"""Optional Playwright smoke for the Vite UI.

Skipped unless ``playwright`` is installed **and** ``CURIOSITY_PLAYWRIGHT=1``.
Does not claim a full browser matrix — local smoke only.

  pip install playwright
  playwright install chromium
  cd web && npm run build
  set CURIOSITY_PLAYWRIGHT=1
  pytest tests/e2e/test_web_playwright.py -q
"""

from __future__ import annotations

import os
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

_REPO = Path(__file__).resolve().parents[2]
_DIST_DIR = _REPO / "web" / "dist"
_DIST_INDEX = _DIST_DIR / "index.html"


def _playwright_enabled() -> bool:
    return os.environ.get("CURIOSITY_PLAYWRIGHT", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


@pytest.fixture(scope="module")
def browser_page():
    if not _playwright_enabled():
        pytest.skip("Set CURIOSITY_PLAYWRIGHT=1 to run optional web Playwright smoke")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright not installed")

    if not _DIST_INDEX.is_file():
        pytest.skip("web/dist missing — run: cd web && npm run build")

    handler = partial(SimpleHTTPRequestHandler, directory=str(_DIST_DIR))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"http://127.0.0.1:{port}/", wait_until="domcontentloaded")
        yield page
        browser.close()
    httpd.shutdown()


def test_web_brand_and_framing_honesty(browser_page) -> None:
    page = browser_page
    assert page.get_by_text("Artificial Curiosity").count() >= 1
    footer = page.locator(".footer-note")
    assert footer.count() >= 1
    text = footer.inner_text().lower()
    assert "decision aids" in text or "oracles" in text or "framing" in text
    toggle = page.get_by_text("investigation framing mix")
    if toggle.count():
        toggle.first.click()
        body = page.locator(".mix-honesty")
        if body.count():
            assert "not" in body.inner_text().lower()
            assert "feel" in body.inner_text().lower() or "ees" in body.inner_text().lower()
    assert page.get_by_text("Side-by-side ranks").count() >= 1
    assert page.locator(".compare-panel").count() >= 1
