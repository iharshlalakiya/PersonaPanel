"""
persona_agent.py — Persona Analysis Agent for PersonaPanel
===========================================================

Public API
----------
    result = run_persona(persona_config, screenshot_bytes_or_url, extracted_text)

Parameters
----------
persona_config : dict
    Configuration describing the persona. Required keys:
        "name"         (str)  — display name, e.g. "Skeptical Buyer"
        "description"  (str)  — one-paragraph character description
        "focus"        (str)  — what this persona pays attention to
        "red_flags"    (list[str]) — triggers that make them distrust / leave
        "green_flags"  (list[str]) — signals that build their confidence

screenshot_input : str | bytes
    Either:
      - Raw PNG bytes (e.g. captured in memory)
      - A public HTTPS URL string pointing to the screenshot image
      Both are handled transparently.

extracted_text : str
    Visible text scraped from the page (from capture_agent).

Returns
-------
Always returns a dict:
    {
        "ok": bool,
        "persona_name": str | None,
        "friction_points": list[dict] | None,   # each: {issue, severity, quote_or_element, suggested_fix}
        "positive_signals": list[str] | None,
        "would_convert": bool | None,
        "gut_reaction": str | None,
        "error": str | None,
    }

Errors are returned in the dict — never raised — so the pipeline can always
inspect `ok` without try/except.
"""

from __future__ import annotations

import base64
import json
import os
import re
import traceback
from typing import Any

import httpx
import google.generativeai as genai
from google.generativeai import protos
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Gemini client setup
# ---------------------------------------------------------------------------
_api_key = os.environ.get("GEMINI_API_KEY", "")
genai.configure(api_key=_api_key)

MODEL_NAME = "gemini-2.0-flash"

# ---------------------------------------------------------------------------
# Built-in persona definitions
# ---------------------------------------------------------------------------

SKEPTICAL_BUYER: dict = {
    "name": "Skeptical Buyer",
    "description": (
        "A cautious, evidence-driven consumer who has been burned by overpromising "
        "products before. They read everything critically, distrust superlatives and "
        "vague marketing language, and actively search for proof: real customer "
        "reviews, concrete numbers, third-party validation, guarantees, and transparent "
        "pricing. They will mentally exit the moment something feels 'too good to be true'."
    ),
    "focus": (
        "Evidence quality (reviews, case studies, certifications), pricing transparency, "
        "presence of guarantees or trials, social proof authenticity, specificity of "
        "claims, and credibility signals like logos, certifications, and named customers."
    ),
    "red_flags": [
        "Vague superlatives with no data ('the best', 'world-class', 'revolutionary')",
        "Hidden pricing or 'contact us for pricing'",
        "Generic stock-photo testimonials without names, roles, or companies",
        "No refund policy or guarantee visible above the fold",
        "Claims that seem exaggerated or unsubstantiated",
        "Overly pushy CTAs with artificial urgency ('Limited time!' without a date)",
        "No 'About Us' or company transparency",
    ],
    "green_flags": [
        "Specific metrics with sources (e.g. '94% customer retention, n=1200')",
        "Named customer logos with case studies or quotes",
        "Transparent pricing with clear tier breakdowns",
        "Free trial, money-back guarantee, or no-credit-card signup",
        "Third-party certifications or press mentions",
        "Founder story or team page that humanises the company",
        "Concrete before/after comparisons or demo videos",
    ],
}

# Registry — extend this dict when adding more personas
PERSONA_REGISTRY: dict[str, dict] = {
    "skeptical_buyer": SKEPTICAL_BUYER,
}

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
    red_flags_block = "\n".join(f"  - {r}" for r in persona["red_flags"])
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
the page in "quote_or_element". Generic observations like "the page lacks social \
proof" without citing what IS (or isn't) there are NOT acceptable.
- severity must be exactly one of: low, medium, high
- would_convert must be a JSON boolean (true or false, not a string)
- gut_reaction must be written in FIRST PERSON as the persona speaking
- Aim for 3-6 friction_points and 2-5 positive_signals

OUTPUT FORMAT:
Return ONLY a single valid JSON object matching this schema — no markdown \
fences, no explanation, no text before or after the JSON:

{_JSON_SCHEMA}"""


def _build_user_message(extracted_text: str) -> str:
    # Cap text so we stay well within token budget
    text_preview = extracted_text[:8_000] if extracted_text else "(no text extracted)"
    return (
        f"Please analyse this webpage as the persona described.\n\n"
        f"EXTRACTED PAGE TEXT:\n```\n{text_preview}\n```\n\n"
        f"The screenshot is provided as the image above. "
        f"Respond with ONLY the JSON object."
    )


# ---------------------------------------------------------------------------
# Screenshot loading helper
# ---------------------------------------------------------------------------

def _load_image_bytes(screenshot_input: str | bytes) -> bytes:
    """
    Accepts either:
      - bytes  → returned as-is
      - str    → treated as a URL, downloaded with httpx
    """
    if isinstance(screenshot_input, bytes):
        return screenshot_input

    # It's a URL string
    url = screenshot_input.strip()
    resp = httpx.get(url, timeout=20, follow_redirects=True)
    resp.raise_for_status()
    return resp.content


# ---------------------------------------------------------------------------
# JSON extraction helper
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict | None:
    """
    Try to pull a JSON object out of *text*, even if Gemini wrapped it in
    markdown fences or added surrounding prose.
    """
    # 1. Direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 2. Strip ```json ... ``` fences
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass

    # 3. Grab the first {...} block in the response
    brace = re.search(r"(\{.*\})", text, re.DOTALL)
    if brace:
        try:
            return json.loads(brace.group(1))
        except json.JSONDecodeError:
            pass

    return None


# ---------------------------------------------------------------------------
# Validation helper
# ---------------------------------------------------------------------------

_REQUIRED_KEYS = {
    "persona_name", "friction_points", "positive_signals",
    "would_convert", "gut_reaction",
}
_VALID_SEVERITIES = {"low", "medium", "high"}


def _validate(data: dict, persona_name: str) -> dict:
    """
    Light-touch validation and normalisation of Gemini's JSON output.
    Raises ValueError with a human-readable message on structural failure.
    """
    missing = _REQUIRED_KEYS - data.keys()
    if missing:
        raise ValueError(f"Response missing keys: {missing}")

    # Coerce types that Gemini sometimes gets wrong
    if isinstance(data["would_convert"], str):
        data["would_convert"] = data["would_convert"].strip().lower() == "true"

    # Normalise persona_name to match config
    data["persona_name"] = persona_name

    # Ensure friction_points is a list of dicts
    fps = data.get("friction_points", [])
    if not isinstance(fps, list):
        raise ValueError("friction_points must be a list")
    for i, fp in enumerate(fps):
        if not isinstance(fp, dict):
            raise ValueError(f"friction_points[{i}] must be a dict")
        # Default missing sub-keys rather than erroring
        fp.setdefault("issue", "")
        fp.setdefault("severity", "medium")
        fp.setdefault("quote_or_element", "")
        fp.setdefault("suggested_fix", "")
        if fp["severity"] not in _VALID_SEVERITIES:
            fp["severity"] = "medium"  # safe default

    # Ensure positive_signals is a list of strings
    ps = data.get("positive_signals", [])
    if not isinstance(ps, list):
        data["positive_signals"] = [str(ps)]
    else:
        data["positive_signals"] = [str(s) for s in ps]

    return data


# ---------------------------------------------------------------------------
# Core Gemini call
# ---------------------------------------------------------------------------

def _call_gemini(
    model: genai.GenerativeModel,
    system_prompt: str,
    user_message: str,
    image_bytes: bytes,
    strict: bool = False,
) -> str:
    """
    Send one request to Gemini with the screenshot + text.
    Returns the raw response text.

    If *strict* is True, a shorter "return ONLY valid JSON" prefix is prepended
    to the user message (used on the retry).
    """
    prefix = (
        "IMPORTANT: Return ONLY a valid JSON object. "
        "No markdown, no explanation, no extra text.\n\n"
        if strict else ""
    )

    image_part = protos.Part(
        inline_data=protos.Blob(mime_type="image/png", data=image_bytes)
    )
    text_part = protos.Part(text=prefix + user_message)

    response = model.generate_content(
        contents=[image_part, text_part],
        generation_config=genai.GenerationConfig(
            temperature=0.4,          # lower = more deterministic / analytical
            max_output_tokens=2048,
            response_mime_type="application/json",  # enforce JSON output mode
        ),
    )
    return response.text


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------

def run_persona(
    persona_config: dict,
    screenshot_input: str | bytes,
    extracted_text: str,
) -> dict:
    """
    Run the given persona against the captured page data.

    persona_config : dict  — use one of the PERSONA_REGISTRY values, or supply
                             a custom config with the same keys.
    screenshot_input : str | bytes  — public URL or raw PNG bytes.
    extracted_text : str — text from capture_agent.

    Returns a result dict (never raises).
    """
    persona_name: str = persona_config.get("name", "Unknown Persona")

    try:
        # ── 1. Load image ────────────────────────────────────────────────
        try:
            image_bytes = _load_image_bytes(screenshot_input)
        except Exception as exc:
            return _err(persona_name, f"Failed to load screenshot: {exc}")

        # ── 2. Build prompt pieces ───────────────────────────────────────
        system_prompt = _build_system_prompt(persona_config)
        user_message = _build_user_message(extracted_text)

        # ── 3. Init model ────────────────────────────────────────────────
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=system_prompt,
        )

        # ── 4. First attempt ─────────────────────────────────────────────
        raw_text = _call_gemini(model, system_prompt, user_message, image_bytes, strict=False)
        parsed = _extract_json(raw_text)

        # ── 5. Retry once if JSON was malformed ──────────────────────────
        if parsed is None:
            raw_text = _call_gemini(model, system_prompt, user_message, image_bytes, strict=True)
            parsed = _extract_json(raw_text)

        if parsed is None:
            return _err(
                persona_name,
                f"Gemini returned malformed JSON after 2 attempts. "
                f"Raw response (first 500 chars): {raw_text[:500]}",
            )

        # ── 6. Validate / normalise ──────────────────────────────────────
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
# Convenience wrapper — run by persona key from registry
# ---------------------------------------------------------------------------

def run_persona_by_key(
    key: str,
    screenshot_input: str | bytes,
    extracted_text: str,
) -> dict:
    """
    Shorthand: run_persona_by_key('skeptical_buyer', ...).
    """
    persona = PERSONA_REGISTRY.get(key)
    if not persona:
        return _err(key, f"Unknown persona key '{key}'. Available: {list(PERSONA_REGISTRY)}")
    return run_persona(persona, screenshot_input, extracted_text)


# ---------------------------------------------------------------------------
# Helpers
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
