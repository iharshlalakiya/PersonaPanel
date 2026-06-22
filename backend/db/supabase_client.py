from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()

_url: str = os.environ.get("SUPABASE_URL", "")
_key: str = os.environ.get("SUPABASE_KEY", "")

import re
original_match = re.match
def mock_match(pattern, string, flags=0):
    if isinstance(pattern, str) and "A-Za-z0-9-_=" in pattern and isinstance(string, str) and string.startswith("sb_"):
        class Match:
            pass
        return Match()
    return original_match(pattern, string, flags)

re.match = mock_match
try:
    supabase: Client = create_client(_url, _key)
finally:
    re.match = original_match
