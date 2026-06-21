"""
Auth routes — signup & login via Supabase Auth.

POST /api/auth/signup   → creates a new Supabase user
POST /api/auth/login    → authenticates and returns JWT tokens
"""
from fastapi import APIRouter, HTTPException, status
from gotrue.errors import AuthApiError

from db.supabase_client import supabase
from models.auth import AuthResponse, LoginRequest, SignUpRequest

router = APIRouter()


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignUpRequest):
    """Create a new account with email + password."""
    try:
        res = supabase.auth.sign_up(
            {"email": body.email, "password": body.password}
        )
    except AuthApiError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if res.user is None or res.session is None:
        # Supabase returns a user but no session when email confirmation is required.
        # For dev convenience we surface a clear message.
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="Account created — check your email to confirm before logging in.",
        )

    return AuthResponse(
        access_token=res.session.access_token,
        refresh_token=res.session.refresh_token,
        user_id=str(res.user.id),
        email=res.user.email,
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest):
    """Authenticate with email + password and return JWT tokens."""
    try:
        res = supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except AuthApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthResponse(
        access_token=res.session.access_token,
        refresh_token=res.session.refresh_token,
        user_id=str(res.user.id),
        email=res.user.email,
    )
