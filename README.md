# PersonaPanel — AI-Powered Synthetic User Testing

> **Generate diverse AI personas, run automated sessions, surface actionable insights — all before you talk to a single real user.**

---

## Project Structure

```
PersonaPanel/
├── backend/              # FastAPI (Python 3.11+)
│   ├── agents/           # AI persona & session logic (future)
│   ├── routes/           # FastAPI routers (future)
│   ├── models/           # Pydantic schemas (future)
│   ├── db/               # Supabase client & helpers (future)
│   ├── app.py            # Main application entry point
│   ├── requirements.txt
│   └── .env.example
└── frontend/             # Vite + React 18 + Tailwind CSS 3
    ├── src/
    │   ├── api/          # Axios client
    │   ├── pages/        # Page components
    │   ├── App.jsx
    │   └── main.jsx
    ├── package.json
    └── .env.example
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| npm / pnpm | latest |

---

## Backend (FastAPI)

### 1 — Create & activate a virtual environment

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### 3 — Configure environment variables

```bash
copy .env.example .env    # Windows
cp  .env.example .env     # macOS / Linux
# Then open .env and fill in your keys
```

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Google Gemini API key |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Your Supabase anon/service key |
| `CORS_ORIGINS` | Comma-separated allowed origins (default: `http://localhost:5173`) |

### 4 — Run the dev server

```bash
uvicorn app:app --reload --port 8000
```

Health-check: [http://localhost:8000/api/health](http://localhost:8000/api/health)
Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Frontend (Vite + React + Tailwind)

### 1 — Install dependencies

```bash
cd frontend
npm install
```

### 2 — Configure environment variables (optional for dev)

```bash
copy .env.example .env    # Windows
cp  .env.example .env     # macOS / Linux
```

> **Note**: In development the Vite proxy (`/api → http://localhost:8000`) handles all
> API calls automatically, so you don't strictly need `.env` filled in.

### 3 — Start the dev server

```bash
npm run dev
```

The app opens at [http://localhost:5173](http://localhost:5173).  
It auto-pings `/api/health` on load and shows the result in the hero section.

---

## Running Both Together (Quick-start)

Open two terminals:

```bash
# Terminal 1 — backend
cd backend && .venv\Scripts\activate && uvicorn app:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Uvicorn, Pydantic v2 |
| AI / LLM | Google Gemini (`google-generativeai`) |
| Browser automation | Playwright |
| Database | Supabase (PostgreSQL) |
| Frontend | React 18, Vite 5, Tailwind CSS 3 |
| HTTP client | Axios |
| Routing | react-router-dom v6 |

---

## Roadmap

- [ ] Persona creation & management
- [ ] Session runner with Playwright agents
- [ ] Results dashboard with Gemini summaries
- [ ] Supabase persistence layer
- [ ] Auth (Supabase Auth)