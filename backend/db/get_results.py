from __future__ import annotations
import traceback
from db.supabase_client import supabase

def get_test_results(session_id: str) -> dict:
    """
    Fetch the complete test results (session + personas + synthesis) from Supabase.
    """
    try:
        # 1. Get session
        session_resp = supabase.table("test_sessions").select("*").eq("id", session_id).execute()
        if not session_resp.data:
            return {"ok": False, "error": f"Session {session_id} not found."}
        session = session_resp.data[0]

        # 2. Get persona results
        personas_resp = supabase.table("persona_results").select("*").eq("test_session_id", session_id).execute()
        persona_results = personas_resp.data

        # 3. Get synthesis
        synthesis_resp = supabase.table("synthesis_results").select("*").eq("test_session_id", session_id).execute()
        synthesis = synthesis_resp.data[0] if synthesis_resp.data else None

        return {
            "ok": True,
            "session": session,
            "persona_results": persona_results,
            "synthesis": synthesis,
            "error": None
        }
    except Exception as exc:
        return {"ok": False, "error": f"Failed to fetch results: {exc}\n{traceback.format_exc()}"}

def get_user_history(user_id: str) -> dict:
    """
    Fetch all test sessions for a given user, ordered by creation date descending.
    """
    try:
        resp = supabase.table("test_sessions").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return {"ok": True, "history": resp.data, "error": None}
    except Exception as exc:
        return {"ok": False, "error": f"Failed to fetch history: {exc}\n{traceback.format_exc()}"}
