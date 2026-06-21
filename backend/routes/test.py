"""
Test routes — lightweight endpoints for isolated feature verification.

POST /api/test/capture
    Body:    { "url": "https://example.com" }
    Returns: { "ok", "screenshot_url", "extracted_text", "error" }

POST /api/test/persona
    Body:    { "url": "https://example.com" }
    Returns: full Skeptical Buyer persona analysis:
             { "ok", "persona_name", "friction_points", "positive_signals",
               "would_convert", "gut_reaction", "error" }

These routes are intentionally unauthenticated for Postman/curl testing.
Auth-gate or remove them before going to production.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from agents.capture_agent import capture_page
from agents.persona_agent import SKEPTICAL_BUYER, run_persona

router = APIRouter()


# ---------------------------------------------------------------------------
# Shared request model
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


@router.post(
    "/capture",
    response_model=CaptureResponse,
    summary="Capture a page screenshot and extract its text",
)
async def capture(body: UrlRequest) -> CaptureResponse:
    """
    Example curl:
        curl -X POST http://localhost:8001/api/test/capture \\
             -H 'Content-Type: application/json' \\
             -d '{"url": "https://stripe.com"}'
    """
    result = capture_page(body.url)
    return CaptureResponse(**result)


# ---------------------------------------------------------------------------
# POST /api/test/persona
# ---------------------------------------------------------------------------

class FrictionPoint(BaseModel):
    issue: str
    severity: str
    quote_or_element: str
    suggested_fix: str


class PersonaResponse(BaseModel):
    ok: bool
    # capture stage info
    screenshot_url: str | None = None
    # persona analysis
    persona_name: str | None = None
    friction_points: list[FrictionPoint] | None = None
    positive_signals: list[str] | None = None
    would_convert: bool | None = None
    gut_reaction: str | None = None
    error: str | None = None


@router.post(
    "/persona",
    response_model=PersonaResponse,
    summary="Run the Skeptical Buyer persona against a live URL",
    description=(
        "Chains the Capture Agent (Playwright screenshot + text extraction) "
        "into the Persona Agent (Gemini 2.0 Flash vision analysis). "
        "Returns the Skeptical Buyer's full structured reaction to the page."
    ),
)
async def persona(body: UrlRequest) -> PersonaResponse:
    """
    Example curl:
        curl -X POST http://localhost:8001/api/test/persona \\
             -H 'Content-Type: application/json' \\
             -d '{"url": "https://stripe.com"}' | python -m json.tool

    Takes 20-40 s depending on page load + Gemini response time.
    """
    # ── Step 1: Capture ───────────────────────────────────────────────────
    capture_result = capture_page(body.url)

    if not capture_result["ok"]:
        return PersonaResponse(
            ok=False,
            error=f"Capture failed: {capture_result['error']}",
        )

    screenshot_url: str = capture_result["screenshot_url"]
    extracted_text: str = capture_result["extracted_text"] or ""

    # ── Step 2: Persona analysis ──────────────────────────────────────────
    persona_result = run_persona(
        persona_config=SKEPTICAL_BUYER,
        screenshot_input=screenshot_url,   # pass the public URL → agent downloads it
        extracted_text=extracted_text,
    )

    if not persona_result["ok"]:
        return PersonaResponse(
            ok=False,
            screenshot_url=screenshot_url,
            error=f"Persona analysis failed: {persona_result['error']}",
        )

    return PersonaResponse(
        ok=True,
        screenshot_url=screenshot_url,
        persona_name=persona_result["persona_name"],
        friction_points=persona_result["friction_points"],
        positive_signals=persona_result["positive_signals"],
        would_convert=persona_result["would_convert"],
        gut_reaction=persona_result["gut_reaction"],
        error=None,
    )
