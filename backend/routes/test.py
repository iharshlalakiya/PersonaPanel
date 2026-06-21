"""
Test routes — unauthenticated endpoints for isolated feature verification.

POST /api/test/capture
    Body:    { "url": "https://example.com" }
    Returns: { "ok", "screenshot_url", "extracted_text", "error" }

POST /api/test/persona
    Body:    { "url": "https://example.com" }
    Returns: Skeptical Buyer reaction (single, quick iteration)

POST /api/test/run   ← MAIN PIPELINE
    Body:    { "url": "https://example.com" }
             { "url": "...", "personas": ["Skeptical Buyer", ...] }
    Runs:    Capture → 5 personas in parallel → synthesis → Supabase write
    Returns: {
        "ok", "url", "screenshot_url",
        "session_id",               ← Supabase test_sessions row ID
        "capture_time_s",
        "personas_time_s",          ← proves parallelism (≈ 1×, not 5×)
        "synthesis_time_s",
        "persist_time_s",
        "total_time_s",
        "personas_run",
        "persona_results": [...],
        "synthesis": { top_priority_issues, persona_specific_issues,
                       overall_conversion_risk_score, summary },
        "db_errors": [...]          ← non-empty only if Supabase write partially failed
    }

These routes are intentionally unauthenticated.
Remove or auth-gate before going to production.
"""
from __future__ import annotations

import asyncio
import functools
import time

from fastapi import APIRouter
from pydantic import BaseModel

from agents.capture_agent import capture_page
from agents.persona_agent import SKEPTICAL_BUYER, run_all_personas, run_persona
from agents.synthesis_agent import synthesize_results
from db.persistence import save_full_run

router = APIRouter()


# ---------------------------------------------------------------------------
# Shared models
# ---------------------------------------------------------------------------

class UrlRequest(BaseModel):
    url: str


class FrictionPoint(BaseModel):
    issue: str
    severity: str
    quote_or_element: str
    suggested_fix: str


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
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, capture_page, body.url)
    return CaptureResponse(**result)


# ---------------------------------------------------------------------------
# POST /api/test/persona  (single Skeptical Buyer — quick iteration)
# ---------------------------------------------------------------------------

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
# POST /api/test/run — full pipeline
# ---------------------------------------------------------------------------

class RunRequest(BaseModel):
    url: str
    personas: list[str] | None = None   # None → run all 5
    user_id: str | None = None          # optional auth — pass JWT sub if available


class TopPriorityIssue(BaseModel):
    issue: str
    flagged_by: list[str]
    severity: str
    suggested_fix: str


class PersonaSpecificIssue(BaseModel):
    issue: str
    flagged_by: str
    severity: str
    suggested_fix: str


class SynthesisResult(BaseModel):
    ok: bool
    top_priority_issues: list[TopPriorityIssue] | None = None
    persona_specific_issues: list[PersonaSpecificIssue] | None = None
    overall_conversion_risk_score: int | None = None
    summary: str | None = None
    error: str | None = None


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
    session_id: str | None = None        # Supabase test_sessions PK
    # Timing breakdown
    capture_time_s: float | None = None
    personas_time_s: float | None = None  # ≈ 1 persona RTT, not 5×
    synthesis_time_s: float | None = None
    persist_time_s: float | None = None
    total_time_s: float | None = None
    # Results
    personas_run: int = 0
    persona_results: list[PersonaResult] = []
    synthesis: SynthesisResult | None = None
    db_errors: list[str] = []           # populated if Supabase writes partially failed
    error: str | None = None


@router.post(
    "/run",
    response_model=RunResponse,
    summary="Full pipeline: capture → 5 personas in parallel → synthesis → Supabase",
    description=(
        "Runs the complete PersonaPanel analysis pipeline: "
        "(1) Capture Agent — Playwright screenshot + text extraction. "
        "(2) All 5 persona agents concurrently via asyncio.gather + ThreadPoolExecutor. "
        "(3) Synthesis Agent — cross-persona aggregation, risk score, summary. "
        "(4) Supabase write — test_sessions, persona_results, synthesis_results. "
        "Timing fields prove parallelism: personas_time_s ≈ ONE persona call, not 5×."
    ),
)
async def run_all(body: RunRequest) -> RunResponse:
    """
    curl -X POST http://localhost:8001/api/test/run \\
         -H 'Content-Type: application/json' \\
         -d '{"url": "https://stripe.com"}' | python -m json.tool

    Filter personas:
        -d '{"url": "...", "personas": ["Skeptical Buyer", "Price-Sensitive Shopper"]}'

    Expect ~40-60 s total (capture ~10-15s, personas ~20-30s, synthesis ~5-10s).
    """
    wall_start = time.perf_counter()
    loop = asyncio.get_event_loop()

    # ── Step 1: Capture ───────────────────────────────────────────────────
    t0 = time.perf_counter()
    capture_result = await loop.run_in_executor(None, capture_page, body.url)
    capture_time = time.perf_counter() - t0

    if not capture_result["ok"]:
        return RunResponse(
            ok=False, url=body.url,
            capture_time_s=round(capture_time, 2),
            error=f"Capture failed: {capture_result['error']}",
        )

    screenshot_url: str  = capture_result["screenshot_url"]
    extracted_text: str  = capture_result["extracted_text"] or ""

    # ── Step 2: All personas in parallel ─────────────────────────────────
    t1 = time.perf_counter()
    persona_results: list[dict] = await run_all_personas(
        screenshot_input=screenshot_url,
        extracted_text=extracted_text,
        selected_names=body.personas,
    )
    personas_time = time.perf_counter() - t1

    # ── Step 3: Synthesis ─────────────────────────────────────────────────
    t2 = time.perf_counter()
    synthesis: dict = await loop.run_in_executor(
        None,
        functools.partial(synthesize_results, persona_results),
    )
    synthesis_time = time.perf_counter() - t2

    # ── Step 4: Persist to Supabase ───────────────────────────────────────
    t3 = time.perf_counter()
    db_result: dict = await loop.run_in_executor(
        None,
        functools.partial(
            save_full_run,
            body.url,
            screenshot_url,
            persona_results,
            synthesis,
            body.user_id,
        ),
    )
    persist_time = time.perf_counter() - t3
    total_time   = time.perf_counter() - wall_start

    return RunResponse(
        ok=True,
        url=body.url,
        screenshot_url=screenshot_url,
        session_id=db_result.get("session_id"),
        capture_time_s=round(capture_time, 2),
        personas_time_s=round(personas_time, 2),
        synthesis_time_s=round(synthesis_time, 2),
        persist_time_s=round(persist_time, 2),
        total_time_s=round(total_time, 2),
        personas_run=len(persona_results),
        persona_results=[PersonaResult(**r) for r in persona_results],
        synthesis=SynthesisResult(**{k: synthesis.get(k) for k in SynthesisResult.model_fields}),
        db_errors=db_result.get("errors", []),
    )

# ---------------------------------------------------------------------------
# GET /api/test/history
# ---------------------------------------------------------------------------

from db.get_results import get_test_results, get_user_history

@router.get("/history", summary="Fetch all past test sessions for a user")
async def get_history(user_id: str):
    """
    Retrieves all past test sessions for the logged in user.
    """
    if not user_id:
        return {"ok": False, "error": "user_id is required"}
        
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, get_user_history, user_id)
    if not result["ok"]:
        return {"ok": False, "error": result["error"]}
    return result

# ---------------------------------------------------------------------------
# GET /api/test/{test_id}
# ---------------------------------------------------------------------------

@router.get("/{test_id}", summary="Fetch saved test results from Supabase")
async def get_results(test_id: str):
    """
    Retrieves the complete test session, persona results, and synthesis
    from the database using the test_id (which is the test_sessions row ID).
    """
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, get_test_results, test_id)
    if not result["ok"]:
        return {"ok": False, "error": result["error"]}
    return result
