"""
persona_agent.py — Persona Analysis Agent for PersonaPanel
===========================================================

Public API
----------
Sync (single persona):
    result = run_persona(persona_config, screenshot_input, extracted_text)

Async (all personas in parallel):
    results = await run_all_personas(screenshot_input, extracted_text)
    results = await run_all_personas(screenshot_input, extracted_text,
                                     selected_names=["Skeptical Buyer", ...])

Why thread pool for parallelism
--------------------------------
`run_persona` calls the *synchronous* Gemini SDK (google-generativeai 0.7.x
uses blocking HTTP). To run 5 of them truly in parallel inside an async
FastAPI endpoint we push each call onto the thread pool with
`loop.run_in_executor`, then `asyncio.gather` all futures.
This gives wall-clock time ≈ the slowest single call, not 5× sequential time.

Return shape (per persona, always):
    {
        "ok": bool,
        "persona_name": str | None,
        "friction_points": list[dict] | None,
        "positive_signals": list[str] | None,
        "would_convert": bool | None,
        "gut_reaction": str | None,
        "error": str | None,
    }
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import traceback
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import httpx
import google.generativeai as genai
from google.generativeai import protos
from dotenv import load_dotenv

from agents.personas_config import ALL_PERSONAS, PERSONA_REGISTRY

load_dotenv()

# ---------------------------------------------------------------------------
# Gemini client setup
# ---------------------------------------------------------------------------
_api_key = os.environ.get("GEMINI_API_KEY", "")
genai.configure(api_key=_api_key)

MODEL_NAME = "gemini-2.0-flash"

# Thread pool shared across all concurrent persona calls.
# 5 workers = one per persona; add more if you scale beyond 5.
_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="persona")

# Re-export for backwards-compat with existing imports
SKEPTICAL_BUYER = PERSONA_REGISTRY["skeptical_buyer"]

# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

_JSON_SCHEMA = """\
{
  "persona_name": "<string>",
  "friction_points": [
    {
      "issue": "<short description of the problem>",
      "severity": "<low|medium|high>",
      "quote_or_element": "<exact text or UI element that caused this friction>",
      "suggested_fix": "<actionable recommendation>"
    }
  ],
  "positive_signals": ["<string>", "..."],
  "would_convert": <true|false>,
  "gut_reaction": "<2-3 sentence first-person gut reaction from the persona's point of view>"
}"""


def _build_system_prompt(persona: dict) -> str:
    red_flags_block  = "\n".join(f"  - {r}" for r in persona["red_flags"])
    green_flags_block = "\n".join(f"  - {g}" for g in persona["green_flags"])

    return f"""\
You are simulating a real user persona evaluating a webpage for PersonaPanel, \
an AI-powered synthetic user-testing tool.

PERSONA: {persona['name']}
{persona['description']}

FOCUS AREAS:
{persona['focus']}

RED FLAGS (things that make this persona distrust or leave):
{red_flags_block}

GREEN FLAGS (things that build this persona's confidence):
{green_flags_block}

TASK:
You will be given:
1. A full-page screenshot of the webpage.
2. The extracted visible text from the page.

Analyse the page EXACTLY as this persona would experience it. Be specific — \
reference actual copy, UI elements, prices, button text, headlines, and \
visual design choices you can see. Do NOT make generic observations.

CRITICAL RULES:
- Every friction_point MUST include a real quote or specific element name from \
the page in "quote_or_element". Generic observations without citing actual \
page content are NOT acceptable.
- severity must be exactly one of: low, medium, high
- would_convert must be a JSON boolean (true or false, not a string)
- gut_reaction must be written in FIRST PERSON as the persona speaking
- Aim for 3-6 friction_points and 2-5 positive_signals

OUTPUT FORMAT:
Return ONLY a single valid JSON object matching this schema — no markdown \
fences, no explanation, no text before or after the JSON:

{_JSON_SCHEMA}"""


def _build_user_message(extracted_text: str) -> str:
    text_preview = extracted_text[:8_000] if extracted_text else "(no text extracted)"
    return (
        f"Please analyse this webpage as the persona described.\n\n"
        f"EXTRACTED PAGE TEXT:\n```\n{text_preview}\n```\n\n"
        f"The screenshot is provided as the image above. "
        f"Respond with ONLY the JSON object."
    )


# ---------------------------------------------------------------------------
# Screenshot loading
# ---------------------------------------------------------------------------

def _load_image_bytes(screenshot_input: str | bytes) -> bytes:
    """bytes → returned as-is. str → treated as URL, downloaded."""
    if isinstance(screenshot_input, bytes):
        return screenshot_input
    resp = httpx.get(screenshot_input.strip(), timeout=20, follow_redirects=True)
    resp.raise_for_status()
    return resp.content


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict | None:
    """Robust JSON extraction — handles direct, fenced, and prose-wrapped output."""
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass

    brace = re.search(r"(\{.*\})", text, re.DOTALL)
    if brace:
        try:
            return json.loads(brace.group(1))
        except json.JSONDecodeError:
            pass

    return None


# ---------------------------------------------------------------------------
# Validation & normalisation
# ---------------------------------------------------------------------------

_REQUIRED_KEYS = {
    "persona_name", "friction_points", "positive_signals",
    "would_convert", "gut_reaction",
}
_VALID_SEVERITIES = {"low", "medium", "high"}


def _validate(data: dict, persona_name: str) -> dict:
    missing = _REQUIRED_KEYS - data.keys()
    if missing:
        raise ValueError(f"Response missing keys: {missing}")

    if isinstance(data["would_convert"], str):
        data["would_convert"] = data["would_convert"].strip().lower() == "true"

    data["persona_name"] = persona_name

    fps = data.get("friction_points", [])
    if not isinstance(fps, list):
        raise ValueError("friction_points must be a list")
    for i, fp in enumerate(fps):
        if not isinstance(fp, dict):
            raise ValueError(f"friction_points[{i}] must be a dict")
        fp.setdefault("issue", "")
        fp.setdefault("severity", "medium")
        fp.setdefault("quote_or_element", "")
        fp.setdefault("suggested_fix", "")
        if fp["severity"] not in _VALID_SEVERITIES:
            fp["severity"] = "medium"

    ps = data.get("positive_signals", [])
    data["positive_signals"] = [str(s) for s in ps] if isinstance(ps, list) else [str(ps)]

    return data


# ---------------------------------------------------------------------------
# Gemini call (sync — safe to call from thread pool)
# ---------------------------------------------------------------------------

def _call_gemini(
    model: genai.GenerativeModel,
    user_message: str,
    image_bytes: bytes,
    strict: bool = False,
) -> str:
    prefix = (
        "IMPORTANT: Return ONLY a valid JSON object. "
        "No markdown, no explanation, no extra text.\n\n"
        if strict else ""
    )
    image_part = protos.Part(inline_data=protos.Blob(mime_type="image/png", data=image_bytes))
    text_part  = protos.Part(text=prefix + user_message)

    response = model.generate_content(
        contents=[image_part, text_part],
        generation_config=genai.GenerationConfig(
            temperature=0.4,
            max_output_tokens=2048,
            response_mime_type="application/json",
        ),
    )
    return response.text


# ---------------------------------------------------------------------------
# Public sync function  — run ONE persona (blocking, thread-safe)
# ---------------------------------------------------------------------------

def run_persona(
    persona_config: dict,
    screenshot_input: str | bytes,
    extracted_text: str,
) -> dict:
    """
    Blocking. Safe to call from any thread.
    Returns a result dict — never raises.
    """
    persona_name: str = persona_config.get("name", "Unknown Persona")
    try:
        # 1. Load image
        try:
            image_bytes = _load_image_bytes(screenshot_input)
        except Exception as exc:
            return _err(persona_name, f"Failed to load screenshot: {exc}")

        # 2. Build prompts
        system_prompt = _build_system_prompt(persona_config)
        user_message  = _build_user_message(extracted_text)

        # 3. Init model (lightweight object — fine to create per-call)
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=system_prompt,
        )

        # 4. First attempt
        raw_text = _call_gemini(model, user_message, image_bytes, strict=False)
        parsed   = _extract_json(raw_text)

        # 5. Retry once with stricter instruction if JSON was malformed
        if parsed is None:
            raw_text = _call_gemini(model, user_message, image_bytes, strict=True)
            parsed   = _extract_json(raw_text)

        if parsed is None:
            return _err(
                persona_name,
                f"Gemini returned malformed JSON after 2 attempts. "
                f"Raw (first 500 chars): {raw_text[:500]}",
            )

        # 6. Validate
        try:
            validated = _validate(parsed, persona_name)
        except ValueError as exc:
            return _err(persona_name, f"Response validation failed: {exc}")

        return {
            "ok": True,
            "persona_name": validated["persona_name"],
            "friction_points": validated["friction_points"],
            "positive_signals": validated["positive_signals"],
            "would_convert": validated["would_convert"],
            "gut_reaction": validated["gut_reaction"],
            "error": None,
        }

    except Exception as exc:
        return _err(persona_name, f"Unexpected error: {exc}\n{traceback.format_exc()}")


# ---------------------------------------------------------------------------
# Public async function — run ALL (or selected) personas CONCURRENTLY
# ---------------------------------------------------------------------------

async def run_all_personas(
    screenshot_input: str | bytes,
    extracted_text: str,
    selected_names: list[str] | None = None,
) -> list[dict]:
    """
    Run personas concurrently using a thread-pool executor.

    Each `run_persona` call (blocking Gemini HTTP) is dispatched to a worker
    thread so all 5 fire simultaneously.  Wall-clock time ≈ the slowest
    single call, not 5× sequential time.

    Parameters
    ----------
    screenshot_input : str | bytes
        Public URL or raw PNG bytes (shared across all persona calls).
    extracted_text : str
        Page text from capture_agent (shared).
    selected_names : list[str] | None
        Optional filter by persona name (e.g. ["Skeptical Buyer", "Price-Sensitive Shopper"]).
        Pass None (default) to run all 5.

    Returns
    -------
    list[dict]  — one result dict per persona, in the same order as ALL_PERSONAS.
                  Failed personas have ok=False; others are not affected.
    """
    # Resolve which personas to run
    if selected_names:
        name_set = {n.lower() for n in selected_names}
        personas = [p for p in ALL_PERSONAS if p["name"].lower() in name_set]
    else:
        personas = ALL_PERSONAS

    if not personas:
        return []

    # Pre-download the image bytes ONCE (shared across all threads).
    # This avoids 5 simultaneous downloads of the same screenshot.
    try:
        image_bytes = await asyncio.get_event_loop().run_in_executor(
            _EXECUTOR, _load_image_bytes, screenshot_input
        )
    except Exception as exc:
        # If we can't load the image at all, fail every persona gracefully
        return [
            _err(p["name"], f"Failed to load screenshot: {exc}")
            for p in personas
        ]

    # Build one coroutine per persona — each runs run_persona in a thread
    loop = asyncio.get_event_loop()

    async def _run_one(persona: dict) -> dict:
        fn = partial(run_persona, persona, image_bytes, extracted_text)
        return await loop.run_in_executor(_EXECUTOR, fn)

    results: list[dict] = await asyncio.gather(*[_run_one(p) for p in personas])
    return results


# ---------------------------------------------------------------------------
# Convenience wrappers (backwards-compat)
# ---------------------------------------------------------------------------

def run_persona_by_key(
    key: str,
    screenshot_input: str | bytes,
    extracted_text: str,
) -> dict:
    """Shorthand: run_persona_by_key('skeptical_buyer', ...)."""
    persona = PERSONA_REGISTRY.get(key)
    if not persona:
        return _err(key, f"Unknown persona key '{key}'. Available: {list(PERSONA_REGISTRY)}")
    return run_persona(persona, screenshot_input, extracted_text)


# ---------------------------------------------------------------------------
# Error helper
# ---------------------------------------------------------------------------

def _err(persona_name: str, message: str) -> dict:
    return {
        "ok": False,
        "persona_name": persona_name,
        "friction_points": None,
        "positive_signals": None,
        "would_convert": None,
        "gut_reaction": None,
        "error": message,
    }
