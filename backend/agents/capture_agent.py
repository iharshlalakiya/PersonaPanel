"""
capture_agent.py — Page Capture Agent for PersonaPanel
=======================================================

Public API
----------
    result = capture_page(url)

Returns a dict that always has:
    {
        "ok": bool,
        "screenshot_url": str | None,   # public Supabase Storage URL
        "extracted_text": str | None,   # visible text scraped from the DOM
        "error": str | None             # human-readable error, or None on success
    }

Errors are returned as dicts (never raised) so callers can always safely
inspect result["ok"] without wrapping in try/except.
"""

from __future__ import annotations

import io
import re
import tempfile
import traceback
import uuid
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from playwright.sync_api import (
    Browser,
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from db.supabase_client import supabase

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BUCKET_NAME = "screenshots"
NAV_TIMEOUT_MS = 15_000          # 15 s navigation timeout (Playwright uses ms)
WAIT_AFTER_LOAD_MS = 1_500       # extra settle time after networkidle
VIEWPORT = {"width": 1440, "height": 900}

# Tags whose text content is completely ignored during extraction
_SKIP_TAGS = {
    "script", "style", "noscript", "head", "meta", "link",
    "svg", "path", "symbol", "defs",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_valid_url(url: str) -> bool:
    """Return True if *url* looks like an absolute HTTP(S) URL."""
    try:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


def _ensure_bucket() -> None:
    """
    Create the 'screenshots' bucket if it doesn't already exist.
    Swallows the 'already exists' error silently.
    """
    try:
        supabase.storage.create_bucket(
            BUCKET_NAME,
            options={"public": True, "allowed_mime_types": ["image/png"]},
        )
    except Exception as exc:
        # storage3 raises a generic exception with the Supabase error message
        msg = str(exc).lower()
        if "already exists" in msg or "duplicate" in msg or "409" in msg:
            return  # bucket already there — fine
        raise  # unexpected error → re-raise


def _upload_screenshot(png_bytes: bytes) -> str:
    """
    Upload *png_bytes* to Supabase Storage and return the public URL.
    File is stored at  screenshots/<uuid>.png
    """
    _ensure_bucket()

    filename = f"{uuid.uuid4()}.png"
    path = filename  # stored at bucket root

    supabase.storage.from_(BUCKET_NAME).upload(
        path=path,
        file=png_bytes,
        file_options={"content-type": "image/png"},
    )

    public_url: str = supabase.storage.from_(BUCKET_NAME).get_public_url(path)
    return public_url


def _extract_text(page) -> str:
    """
    Pull all human-readable text out of the page DOM.

    Strategy:
      1. Remove script / style / svg tags in a JS evaluate call.
      2. Walk every visible text node via innerText on the body.
      3. De-duplicate adjacent whitespace; return a reasonably clean string.
    """
    # Use Playwright's evaluate to extract text via the browser engine itself —
    # innerText already respects CSS visibility and collapses whitespace.
    raw: str = page.evaluate(
        """() => {
            // Clone so we don't mutate the live DOM
            const clone = document.body.cloneNode(true);

            // Remove tags we never want text from
            const skip = ['script','style','noscript','svg','path','symbol','defs','link','meta'];
            skip.forEach(tag => {
                clone.querySelectorAll(tag).forEach(el => el.remove());
            });

            // Collect text from elements that tend to carry meaningful content
            const selectors = [
                'h1','h2','h3','h4','h5','h6',
                'p','li','td','th','dt','dd',
                'button','a','label','span','div',
                '[placeholder]','[aria-label]',
            ];

            const seen = new Set();
            const parts = [];

            selectors.forEach(sel => {
                clone.querySelectorAll(sel).forEach(el => {
                    // innerText gives rendered text, collapses whitespace
                    const txt = (el.innerText || el.textContent || '').trim();
                    if (txt.length > 1 && !seen.has(txt)) {
                        seen.add(txt);
                        parts.push(txt);
                    }
                });
            });

            return parts.join('\\n');
        }"""
    )

    # Post-process: collapse runs of blank lines, strip leading/trailing
    lines = [ln.strip() for ln in raw.splitlines()]
    # Remove empty lines that are adjacent duplicates
    deduped: list[str] = []
    for ln in lines:
        if ln and (not deduped or deduped[-1] != ln):
            deduped.append(ln)

    cleaned = "\n".join(deduped)
    # Hard cap at 20 000 chars — enough context for LLM, not memory-busting
    return cleaned[:20_000]


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def capture_page(url: str) -> dict:
    """
    Navigate to *url*, take a full-page screenshot, upload it to Supabase
    Storage, and extract visible text.

    Always returns a dict:
        {
            "ok": bool,
            "screenshot_url": str | None,
            "extracted_text": str | None,
            "error": str | None,
        }
    """
    # ── 1. Validate URL ──────────────────────────────────────────────────
    if not url or not url.strip():
        return _err("URL must not be empty.")

    url = url.strip()
    if not _is_valid_url(url):
        return _err(f"Invalid URL: '{url}'. Must start with http:// or https://.")

    # ── 2. Launch browser and capture ────────────────────────────────────
    screenshot_url: Optional[str] = None
    extracted_text: Optional[str] = None

    try:
        with sync_playwright() as pw:
            browser: Browser = pw.chromium.launch(
                headless=True,
                args=[
                    # Reduce fingerprinting that causes bot-detection blocks
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            context = browser.new_context(
                viewport=VIEWPORT,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                java_script_enabled=True,
                locale="en-US",
            )

            # Stealth: remove the 'webdriver' property that many bot-detectors check
            context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            page = context.new_page()

            # ── 2a. Navigate ─────────────────────────────────────────────
            try:
                page.goto(
                    url,
                    timeout=NAV_TIMEOUT_MS,
                    wait_until="domcontentloaded",  # don't wait for all resources
                )
                # Give JS-heavy SPAs a moment to render
                try:
                    page.wait_for_load_state("networkidle", timeout=WAIT_AFTER_LOAD_MS)
                except PlaywrightTimeoutError:
                    pass  # networkidle is best-effort; continue anyway

            except PlaywrightTimeoutError:
                browser.close()
                return _err(
                    f"Navigation timed out after {NAV_TIMEOUT_MS // 1000} seconds. "
                    "The page may be slow or blocking headless browsers."
                )
            except PlaywrightError as exc:
                browser.close()
                msg = str(exc)
                # Surface common human-friendly causes
                if "net::ERR_NAME_NOT_RESOLVED" in msg:
                    return _err(f"Domain not found: '{urlparse(url).netloc}'. Check the URL spelling.")
                if "net::ERR_CONNECTION_REFUSED" in msg:
                    return _err("Connection refused. The server may be down or not publicly reachable.")
                if "net::ERR_SSL" in msg or "SSL" in msg:
                    return _err("SSL/TLS error connecting to the page.")
                return _err(f"Browser navigation error: {msg}")

            # ── 2b. Screenshot ───────────────────────────────────────────
            try:
                png_bytes: bytes = page.screenshot(full_page=True, type="png")
            except PlaywrightError as exc:
                browser.close()
                return _err(f"Screenshot failed: {exc}")

            # ── 2c. Text extraction ──────────────────────────────────────
            try:
                extracted_text = _extract_text(page)
            except Exception as exc:
                # Non-fatal: we still have the screenshot
                extracted_text = f"[Text extraction error: {exc}]"

            browser.close()

        # ── 3. Upload to Supabase Storage ────────────────────────────────
        try:
            screenshot_url = _upload_screenshot(png_bytes)
        except Exception as exc:
            # Return partial success: text extracted but upload failed
            return {
                "ok": False,
                "screenshot_url": None,
                "extracted_text": extracted_text,
                "error": f"Screenshot taken but upload to Supabase failed: {exc}",
            }

        return {
            "ok": True,
            "screenshot_url": screenshot_url,
            "extracted_text": extracted_text,
            "error": None,
        }

    except Exception as exc:
        # Catch-all so we never crash the API
        return _err(f"Unexpected error during page capture: {exc} | {traceback.format_exc()}")


def _err(message: str) -> dict:
    return {
        "ok": False,
        "screenshot_url": None,
        "extracted_text": None,
        "error": message,
    }
