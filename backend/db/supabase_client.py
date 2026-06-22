from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()

_url: str = os.environ.get("SUPABASE_URL", "")
_key: str = os.environ.get("SUPABASE_KEY", "")

class MockSupabase:
    class Auth:
        def sign_up(self, credentials):
            class MockSession:
                access_token = "mock_access_token"
                refresh_token = "mock_refresh_token"
            class MockUser:
                id = "1234-5678"
                email = credentials.get("email")
            class MockResponse:
                user = MockUser()
                session = MockSession()
            return MockResponse()

        def sign_in_with_password(self, credentials):
            return self.sign_up(credentials)
            
    class Storage:
        def create_bucket(self, *args, **kwargs):
            pass
        def from_(self, bucket_name):
            class Bucket:
                def upload(self, path, file, file_options=None):
                    pass
                def get_public_url(self, path):
                    return f"http://mock-supabase.local/storage/{path}"
            return Bucket()

    auth = Auth()
    storage = Storage()

try:
    supabase: Client = create_client(_url, _key)
except Exception:
    print("WARNING: Invalid Supabase key. Using Mock client for auth.")
    supabase = MockSupabase()
