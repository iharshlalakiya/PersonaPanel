"""
Supabase singleton client.

Usage anywhere in the backend:
    from db.supabase_client import supabase
"""
from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()

_url: str = os.environ["SUPABASE_URL"]
_key: str = os.environ["SUPABASE_KEY"]

supabase: Client = create_client(_url, _key)
