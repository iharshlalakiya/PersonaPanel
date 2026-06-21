"""
synthesis_agent.py — Cross-Persona Synthesis for PersonaPanel
=============================================================

Public API
----------
    result = synthesize_results(persona_results)

Input
-----
persona_results : list[dict]
    The output list from run_all_personas — one dict per persona.
    Only dicts with ok=True are used (failed personas are skipped with a note).

Output
------
Always a dict:
    {
        "ok": bool,
        "top_priority_issues": list[dict] | None,
        "persona_specific_issues": list[dict] | None,
        "overall_conversion_risk_score": int | None,   # 0-100
        "summary": str | None,
        "error": str | None,
    }

top_priority_issues (flagged by 2+ personas):
    [{"issue": str, "flagged_by": [str, ...], "severity": str, "suggested_fix": str}]

persona_specific_issues (flagged by exactly 1 persona):
    [{"issue": str, "flagged_by": str, "severity": str, "suggested_fix": str}]
"""

from __future__ import annotations

import json
import os
import re
import traceback

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

_api_key = os.environ.get("GEMINI_API_KEY", "")
genai.configure(api_key=_api_key)

MODEL_NAME = "gemini-2.0-flash"

# ---------------------------------------------------------------------------
# JSON schema returned by Gemini
# ---------------------------------------------------------------------------

_JSON_SCHEMA = """\
{
  "top_priority_issues": [
    {
      "issue": "<concise description of the shared friction>",
      "flagged_by": ["<persona name>", "..."],
      "severity": "<low|medium|high>",
      "suggested_fix": "<specific, actionable recommendation>"
    }
  ],
  "persona_specific_issues": [
    {
      "issue": "<concise description of the friction>",
      "flagged_by": "<single persona name>",
      "severity": "<low|medium|high>",
      "suggested_fix": "<specific, actionable recommendation>"
    }
  ],
  "overall_conversion_risk_score": <integer 0-100>,
  "summary": "<2-3 sentence executive summary of the page's main conversion barriers and strengths>"
}"""

# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an expert conversion-rate optimisation (CRO) analyst for PersonaPanel, \
an AI-powered synthetic user-testing tool.

You have received structured feedback on a webpage from multiple AI persona simulations. \
Each persona independently analysed the same page and reported friction points (barriers \
to conversion), positive signals (trust/confidence builders), whether they would convert, \
and a gut reaction.

YOUR TASK:
Synthesise all persona feedback into a unified, prioritised report.

SYNTHESIS RULES:
1. TOP PRIORITY ISSUES — Cross-persona friction:
   - Find friction points that were flagged by TWO OR MORE personas.
   - Do NOT just match identical text — look for thematically similar issues
     (e.g. "no pricing visible" and "pricing hidden behind contact form" are the same issue).
   - List each shared friction once, with all persona names in "flagged_by".
   - Assign severity: high if flagged by 3+ personas or any single "high" flag,
     medium if flagged by 2 personas with medium severity, low otherwise.

2. PERSONA-SPECIFIC ISSUES:
   - List friction points raised by exactly ONE persona that were NOT already captured
     in top_priority_issues.
   - These are lower priority but still actionable.

3. OVERALL CONVERSION RISK SCORE (0–100):
   - 0 = virtually no barriers, most personas would convert.
   - 100 = severe barriers, essentially no persona would convert.
   - Weight factors: number of personas that would NOT convert (heaviest weight),
     number and severity of top_priority_issues, breadth of persona-specific issues.
   - Be calibrated: a page with 3/5 personas not converting and 4 high-severity
     cross-persona issues might score 70-80.

4. SUMMARY:
   - Write 2-3 sentences as an executive summary.
   - State: overall risk level, the single most critical barrier, and one strength.
   - Be specific — reference actual page content from the persona reports.

OUTPUT:
Return ONLY a single valid JSON object matching this schema.
No markdown fences, no explanation, no text outside the JSON:

""" + _JSON_SCHEMA


def _build_user_message(persona_results: list[dict]) -> str:
    """Serialise all successful persona results into a clear prompt input."""
    successful = [r for r in persona_results if r.get("ok")]
    failed     = [r for r in persona_results if not r.get("ok")]

    lines = ["PERSONA ANALYSIS RESULTS:\n"]

    for r in successful:
        lines.append(f"{'='*60}")
        lines.append(f"PERSONA: {r['persona_name']}")
        lines.append(f"Would convert: {r['would_convert']}")
        lines.append(f"Gut reaction: {r['gut_reaction']}")
        lines.append("")
        lines.append("Friction Points:")
        for fp in (r.get("friction_points") or []):
            lines.append(
                f"  [{fp.get('severity','?').upper()}] {fp.get('issue','')}\n"
                f"    Quote/Element: {fp.get('quote_or_element','')}\n"
                f"    Fix: {fp.get('suggested_fix','')}"
            )
        lines.append("")
        lines.append("Positive Signals:")
        for sig in (r.get("positive_signals") or []):
            lines.append(f"  + {sig}")
        lines.append("")

    if failed:
        lines.append(f"{'='*60}")
        lines.append(f"NOTE: {len(failed)} persona(s) failed and are excluded from synthesis:")
        for r in failed:
            lines.append(f"  - {r.get('persona_name','?')}: {r.get('error','unknown error')}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON extraction (same robust pattern as persona_agent)
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict | None:
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

_VALID_SEVERITIES = {"low", "medium", "high"}


def _validate(data: dict) -> dict:
    missing = {"top_priority_issues", "persona_specific_issues",
               "overall_conversion_risk_score", "summary"} - data.keys()
    if missing:
        raise ValueError(f"Synthesis response missing keys: {missing}")

    # Clamp score to 0-100
    score = data.get("overall_conversion_risk_score")
    if not isinstance(score, int):
        try:
            score = int(float(str(score)))
        except (ValueError, TypeError):
            score = 50   # safe default if Gemini returns garbage
    data["overall_conversion_risk_score"] = max(0, min(100, score))

    # Normalise top_priority_issues
    tpi = data.get("top_priority_issues", [])
    if not isinstance(tpi, list):
        tpi = []
    for item in tpi:
        if not isinstance(item, dict):
            continue
        item.setdefault("issue", "")
        item.setdefault("flagged_by", [])
        item.setdefault("severity", "medium")
        item.setdefault("suggested_fix", "")
        if isinstance(item["flagged_by"], str):
            item["flagged_by"] = [item["flagged_by"]]
        if item["severity"] not in _VALID_SEVERITIES:
            item["severity"] = "medium"
    data["top_priority_issues"] = tpi

    # Normalise persona_specific_issues
    psi = data.get("persona_specific_issues", [])
    if not isinstance(psi, list):
        psi = []
    for item in psi:
        if not isinstance(item, dict):
            continue
        item.setdefault("issue", "")
        item.setdefault("flagged_by", "")
        item.setdefault("severity", "medium")
        item.setdefault("suggested_fix", "")
        if isinstance(item["flagged_by"], list):
            item["flagged_by"] = item["flagged_by"][0] if item["flagged_by"] else ""
        if item["severity"] not in _VALID_SEVERITIES:
            item["severity"] = "medium"
    data["persona_specific_issues"] = psi

    if not isinstance(data.get("summary"), str):
        data["summary"] = ""

    return data


# ---------------------------------------------------------------------------
# Gemini call
# ---------------------------------------------------------------------------

def _call_gemini(user_message: str, strict: bool = False) -> str:
    prefix = (
        "IMPORTANT: Return ONLY a valid JSON object. "
        "No markdown, no explanation, no extra text.\n\n"
        if strict else ""
    )
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=_SYSTEM_PROMPT,
    )
    response = model.generate_content(
        contents=prefix + user_message,
        generation_config=genai.GenerationConfig(
            temperature=0.3,           # synthesis is analytical — keep it tight
            max_output_tokens=2048,
            response_mime_type="application/json",
        ),
    )
    return response.text


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------

def synthesize_results(persona_results: list[dict]) -> dict:
    """
    Synthesise all persona results into a unified CRO report.

    persona_results : list[dict]
        Output from run_all_personas — ok and failed personas mixed.
        At least one must have ok=True or an error dict is returned.

    Returns a dict (never raises).
    """
    try:
        # Guard: need at least one successful persona result
        successful = [r for r in persona_results if r.get("ok")]
        if not successful:
            return _err(
                "No successful persona results to synthesise. "
                "All personas failed — check persona agent logs."
            )

        # Build the user message
        user_message = _build_user_message(persona_results)

        # First attempt
        raw_text = _call_gemini(user_message, strict=False)
        parsed   = _extract_json(raw_text)

        # Retry once with stricter instruction
        if parsed is None:
            raw_text = _call_gemini(user_message, strict=True)
            parsed   = _extract_json(raw_text)

        if parsed is None:
            return _err(
                f"Gemini returned malformed JSON after 2 attempts. "
                f"Raw (first 500 chars): {raw_text[:500]}"
            )

        # Validate & normalise
        try:
            validated = _validate(parsed)
        except ValueError as exc:
            return _err(f"Synthesis response validation failed: {exc}")

        return {
            "ok": True,
            "top_priority_issues": validated["top_priority_issues"],
            "persona_specific_issues": validated["persona_specific_issues"],
            "overall_conversion_risk_score": validated["overall_conversion_risk_score"],
            "summary": validated["summary"],
            "error": None,
        }

    except Exception as exc:
        return _err(f"Unexpected error during synthesis: {exc}\n{traceback.format_exc()}")


def _err(message: str) -> dict:
    return {
        "ok": False,
        "top_priority_issues": None,
        "persona_specific_issues": None,
        "overall_conversion_risk_score": None,
        "summary": None,
        "error": message,
    }
