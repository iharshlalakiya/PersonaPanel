"""
Test routes — unauthenticated endpoints for isolated feature verification.

POST /api/test/capture
    Body:    { "url": "https://example.com" }
    Returns: { "ok", "screenshot_url", "extracted_text", "error" }

POST /api/test/persona
    Body:    { "url": "https://example.com" }
    Returns: Skeptical Buyer reaction (single persona, for quick iteration)

POST /api/test/run
    Body:    { "url": "https://example.com" }
             { "url": "...", "personas": ["Skeptical Buyer", "Price-Sensitive Shopper"] }
    Returns: {
        "ok": bool,
        "screenshot_url": str,
        "capture_time_s": float,
        "personas_time_s": float,   ← proves parallelism (≈ 1 persona, not 5×)
        "total_time_s": float,
        "results": [ ...5 persona dicts... ]
    }

These routes are intentionally unauthenticated for Postman/curl testing.
Remove or auth-gate before going to production.
"""
from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter
from pydantic import BaseModel

from agents.capture_agent import capture_page
from agents.persona_agent import SKEPTICAL_BUYER, run_all_personas, run_persona
from agents.personas_config import ALL_PERSONAS

router = APIRouter()


# ---------------------------------------------------------------------------
# Shared models
# ---------------------------------------------------------------------------

class UrlRequest(BaseModel):
    url: str


# ---------------------------------------------------------------------------
# POST /api/test/capture
# ---------------------------------------------------------------------------

class CaptureResponse(BaseModel):
    ok: bool
    screenshot_url: str | None = None
    extracted_text: str | None = None
    error: str | None = None


@router.post("/capture", response_model=CaptureResponse,
             summary="Capture screenshot + extract text from a URL")
async def capture(body: UrlRequest) -> CaptureResponse:
    """
    curl -X POST http://localhost:8001/api/test/capture \\
         -H 'Content-Type: application/json' \\
         -d '{"url": "https://stripe.com"}'
    """
    result = capture_page(body.url)
    return CaptureResponse(**result)


# ---------------------------------------------------------------------------
# POST /api/test/persona  (single Skeptical Buyer — kept for quick iteration)
# ---------------------------------------------------------------------------

class FrictionPoint(BaseModel):
    issue: str
    severity: str
    quote_or_element: str
    suggested_fix: str


class PersonaResponse(BaseModel):
    ok: bool
    screenshot_url: str | None = None
    persona_name: str | None = None
    friction_points: list[FrictionPoint] | None = None
    positive_signals: list[str] | None = None
    would_convert: bool | None = None
    gut_reaction: str | None = None
    error: str | None = None


@router.post("/persona", response_model=PersonaResponse,
             summary="Run Skeptical Buyer persona (single, quick test)")
async def persona_single(body: UrlRequest) -> PersonaResponse:
    """
    curl -X POST http://localhost:8001/api/test/persona \\
         -H 'Content-Type: application/json' \\
         -d '{"url": "https://stripe.com"}' | python -m json.tool
    """
    loop = asyncio.get_event_loop()

    capture_result = await loop.run_in_executor(None, capture_page, body.url)
    if not capture_result["ok"]:
        return PersonaResponse(ok=False, error=f"Capture failed: {capture_result['error']}")

    screenshot_url = capture_result["screenshot_url"]
    extracted_text = capture_result["extracted_text"] or ""

    import functools
    persona_result = await loop.run_in_executor(
        None, functools.partial(run_persona, SKEPTICAL_BUYER, screenshot_url, extracted_text)
    )
    if not persona_result["ok"]:
        return PersonaResponse(ok=False, screenshot_url=screenshot_url,
                               error=f"Persona failed: {persona_result['error']}")

    return PersonaResponse(
        ok=True,
        screenshot_url=screenshot_url,
        persona_name=persona_result["persona_name"],
        friction_points=persona_result["friction_points"],
        positive_signals=persona_result["positive_signals"],
        would_convert=persona_result["would_convert"],
        gut_reaction=persona_result["gut_reaction"],
    )


# ---------------------------------------------------------------------------
# POST /api/test/run  ← main endpoint: capture + ALL 5 personas in parallel
# ---------------------------------------------------------------------------

class RunRequest(BaseModel):
    url: str
    # Optional: pass a subset of persona names to run only those
    personas: list[str] | None = None


class PersonaResult(BaseModel):
    ok: bool
    persona_name: str | None = None
    friction_points: list[FrictionPoint] | None = None
    positive_signals: list[str] | None = None
    would_convert: bool | None = None
    gut_reaction: str | None = None
    error: str | None = None


class RunResponse(BaseModel):
    ok: bool
    url: str
    screenshot_url: str | None = None
    # Timing metadata — proves parallelism
    capture_time_s: float | None = None
    personas_time_s: float | None = None    # ≈ single persona time, not 5×
    total_time_s: float | None = None
    personas_run: int = 0
    results: list[PersonaResult] = []
    error: str | None = None


@router.post(
    "/run",
    response_model=RunResponse,
    summary="Full pipeline: capture + all 5 personas in parallel",
    description=(
        "Runs the Capture Agent then dispatches all 5 persona analyses "
        "concurrently via asyncio.gather + ThreadPoolExecutor. "
        "The `personas_time_s` field in the response proves true parallelism — "
        "it should be ≈ the time of ONE persona call, not 5×. "
        "Pass `personas` to filter which personas run."
    ),
)
async def run_all(body: RunRequest) -> RunResponse:
    """
    curl -X POST http://localhost:8001/api/test/run \\
         -H 'Content-Type: application/json' \\
         -d '{"url": "https://stripe.com"}' | python -m json.tool

    With persona filter:
        -d '{"url": "https://stripe.com", "personas": ["Skeptical Buyer", "Price-Sensitive Shopper"]}'

    Expect ~30-50 s total (dominated by capture + one Gemini RTT, not 5×).
    """
    wall_start = time.perf_counter()

    # ── Step 1: Capture (blocking → thread) ──────────────────────────────
    loop = asyncio.get_event_loop()
    t0 = time.perf_counter()
    capture_result = await loop.run_in_executor(None, capture_page, body.url)
    capture_time = time.perf_counter() - t0

    if not capture_result["ok"]:
        return RunResponse(
            ok=False,
            url=body.url,
            capture_time_s=round(capture_time, 2),
            error=f"Capture failed: {capture_result['error']}",
        )

    screenshot_url: str = capture_result["screenshot_url"]
    extracted_text: str = capture_result["extracted_text"] or ""

    # ── Step 2: Run all personas concurrently ────────────────────────────
    t1 = time.perf_counter()
    persona_results: list[dict] = await run_all_personas(
        screenshot_input=screenshot_url,
        extracted_text=extracted_text,
        selected_names=body.personas,   # None → run all 5
    )
    personas_time = time.perf_counter() - t1
    total_time    = time.perf_counter() - wall_start

    return RunResponse(
        ok=True,
        url=body.url,
        screenshot_url=screenshot_url,
        capture_time_s=round(capture_time, 2),
        personas_time_s=round(personas_time, 2),
        total_time_s=round(total_time, 2),
        personas_run=len(persona_results),
        results=[PersonaResult(**r) for r in persona_results],
    )
