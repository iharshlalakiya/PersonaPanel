from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(
    title="PersonaPanel API",
    description="Synthetic user-testing tool powered by AI personas",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS — allow the Vite dev server to talk to this API
# ---------------------------------------------------------------------------
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers  (import each sub-router here as the project grows)
# ---------------------------------------------------------------------------
# from routes.personas import router as personas_router
# app.include_router(personas_router, prefix="/api/personas", tags=["personas"])


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/api/health", tags=["system"])
async def health_check():
    """Returns a simple liveness signal for the API."""
    return {"status": "ok"}
