"""
persistence.py — Supabase write helpers for PersonaPanel
=========================================================

All functions are synchronous (safe to call from thread pool or directly).
Each returns a dict:  { "ok": bool, "id": str|None, "error": str|None }

Tables written:
  test_sessions       → save_test_session(...)   → returns session_id
  persona_results     → save_persona_results(session_id, persona_results)
  synthesis_results   → save_synthesis_result(session_id, synthesis)

Usage from an async context (FastAPI):
    loop = asyncio.get_event_loop()
    r = await loop.run_in_executor(None, save_test_session, url, screenshot_url, score)
"""

from __future__ import annotations

import json
import traceback
from typing import Any

from db.supabase_client import supabase


# ---------------------------------------------------------------------------
# test_sessions
# ---------------------------------------------------------------------------

def save_test_session(
    url: str,
    screenshot_url: str | None,
    overall_conversion_risk_score: int | None = None,
    user_id: str | None = None,
) -> dict:
    """
    Insert a row into test_sessions.

    user_id is optional — pass it when the caller is authenticated.
    When None (unauthenticated test calls), the row is inserted with
    user_id = NULL (allowed by schema v2).

    Returns { "ok": bool, "id": str|None, "error": str|None }
    """
    try:
        row: dict[str, Any] = {
            "url": url,
            "screenshot_url": screenshot_url,
            "overall_conversion_risk_score": overall_conversion_risk_score,
        }
        if user_id is not None:
            row["user_id"] = user_id

        resp = supabase.table("test_sessions").insert(row).execute()
        session_id: str = resp.data[0]["id"]
        return {"ok": True, "id": session_id, "error": None}

    except Exception as exc:
        return {"ok": False, "id": None, "error": f"save_test_session failed: {exc}\n{traceback.format_exc()}"}


# ---------------------------------------------------------------------------
# persona_results
# ---------------------------------------------------------------------------

def save_persona_results(
    test_session_id: str,
    persona_results: list[dict],
) -> dict:
    """
    Bulk-insert all successful persona results for a session.

    Only dicts with ok=True are inserted; failed personas are skipped.

    Returns { "ok": bool, "inserted": int, "error": str|None }
    """
    try:
        rows = []
        for r in persona_results:
            if not r.get("ok"):
                continue   # skip failed personas
            rows.append({
                "test_session_id": test_session_id,
                "persona_name":    r["persona_name"],
                "friction_points": r.get("friction_points") or [],
                "positive_signals": r.get("positive_signals") or [],
                "would_convert":   bool(r.get("would_convert", False)),
                "gut_reaction":    r.get("gut_reaction") or "",
            })

        if not rows:
            return {"ok": True, "inserted": 0, "error": None}

        supabase.table("persona_results").insert(rows).execute()
        return {"ok": True, "inserted": len(rows), "error": None}

    except Exception as exc:
        return {
            "ok": False, "inserted": 0,
            "error": f"save_persona_results failed: {exc}\n{traceback.format_exc()}",
        }


# ---------------------------------------------------------------------------
# synthesis_results
# ---------------------------------------------------------------------------

def save_synthesis_result(
    test_session_id: str,
    synthesis: dict,
) -> dict:
    """
    Insert one synthesis result row for a session.

    synthesis must have ok=True and the standard synthesis keys.
    Returns { "ok": bool, "id": str|None, "error": str|None }
    """
    try:
        if not synthesis.get("ok"):
            return {
                "ok": False, "id": None,
                "error": f"Synthesis was not successful: {synthesis.get('error')}",
            }

        row = {
            "test_session_id": test_session_id,
            "top_priority_issues": synthesis.get("top_priority_issues") or [],
            "persona_specific_issues": synthesis.get("persona_specific_issues") or [],
            "overall_conversion_risk_score": synthesis.get("overall_conversion_risk_score"),
            "summary": synthesis.get("summary") or "",
        }

        resp = supabase.table("synthesis_results").insert(row).execute()
        synth_id: str = resp.data[0]["id"]
        return {"ok": True, "id": synth_id, "error": None}

    except Exception as exc:
        return {
            "ok": False, "id": None,
            "error": f"save_synthesis_result failed: {exc}\n{traceback.format_exc()}",
        }


# ---------------------------------------------------------------------------
# Convenience: save everything for one run in the right order
# ---------------------------------------------------------------------------

def save_full_run(
    url: str,
    screenshot_url: str | None,
    persona_results: list[dict],
    synthesis: dict,
    user_id: str | None = None,
) -> dict:
    """
    Orchestrates the full three-table write in dependency order:
        1. test_sessions  (must be first — others FK to it)
        2. persona_results
        3. synthesis_results + back-fill overall_conversion_risk_score on session

    Returns:
        {
            "ok": bool,
            "session_id": str | None,
            "persona_rows_inserted": int,
            "synthesis_id": str | None,
            "errors": list[str],    # non-empty if any step partially failed
        }
    """
    errors: list[str] = []

    # 1. Create session (score filled from synthesis)
    score = synthesis.get("overall_conversion_risk_score") if synthesis.get("ok") else None
    sess_r = save_test_session(url, screenshot_url, score, user_id)
    if not sess_r["ok"]:
        return {
            "ok": False,
            "session_id": None,
            "persona_rows_inserted": 0,
            "synthesis_id": None,
            "errors": [sess_r["error"]],
        }

    session_id: str = sess_r["id"]

    # 2. Persona results
    per_r = save_persona_results(session_id, persona_results)
    if not per_r["ok"]:
        errors.append(per_r["error"])

    # 3. Synthesis result
    syn_r = save_synthesis_result(session_id, synthesis)
    if not syn_r["ok"]:
        errors.append(syn_r["error"])

    return {
        "ok": len(errors) == 0,
        "session_id": session_id,
        "persona_rows_inserted": per_r.get("inserted", 0),
        "synthesis_id": syn_r.get("id"),
        "errors": errors,
    }
