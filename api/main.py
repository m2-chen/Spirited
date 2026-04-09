"""
Step 5 — Backend API
FastAPI server exposing the multi-agent Mixologist orchestrator as a REST API.
"""

import sqlite3
import sys
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

load_dotenv(Path(__file__).parent.parent / ".env")
sys.path.append(str(Path(__file__).parent.parent / "rag"))

from agents.orchestrator import OrchestratorAgent
from api.models import ChatRequest, ChatResponse

app = FastAPI(title="AI Mixologist API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single orchestrator instance shared across requests
orchestrator = OrchestratorAgent()

DB_PATH = Path(__file__).parent.parent / "data" / "cocktails.db"

# Serve frontend
FRONTEND_PATH = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_PATH)), name="static")


@app.get("/")
def serve_frontend():
    return FileResponse(str(FRONTEND_PATH / "index.html"))


@app.get("/health")
def health():
    return {"status": "ok", "agent": "AI Mixologist — Multi-Agent v2"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.history
        ]

        result = orchestrator.run(
            user_message=request.message,
            chat_history=history if history else None,
            mode=request.mode
        )

        return ChatResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cocktails")
def list_cocktails(
    limit: int = 20,
    offset: int = 0,
    strength: str = None,
    alcoholic: str = None
):
    """Browse the cocktail database with optional filters — powered by SQLite."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    query = "SELECT id, name, category, alcoholic, glass, instructions, thumbnail, strength FROM cocktails WHERE 1=1"
    params = []

    if strength:
        query += " AND strength = ?"
        params.append(strength)
    if alcoholic:
        query += " AND LOWER(alcoholic) = LOWER(?)"
        params.append(alcoholic)

    total = con.execute(f"SELECT COUNT(*) FROM ({query})", params).fetchone()[0]
    rows  = con.execute(query + " LIMIT ? OFFSET ?", params + [limit, offset]).fetchall()

    cocktails = []
    for row in rows:
        cid = row["id"]
        c = dict(row)
        c["ingredients"]    = [dict(r) for r in con.execute(
            "SELECT ingredient, measure FROM ingredients WHERE cocktail_id = ?", (cid,))]
        c["flavor_profile"] = [r[0] for r in con.execute(
            "SELECT flavor FROM flavor_profiles WHERE cocktail_id = ?", (cid,))]
        c["mood"]           = [r[0] for r in con.execute(
            "SELECT mood FROM moods WHERE cocktail_id = ?", (cid,))]
        c["best_for"]       = [r[0] for r in con.execute(
            "SELECT use_case FROM best_for WHERE cocktail_id = ?", (cid,))]
        cocktails.append(c)

    con.close()
    return {"total": total, "offset": offset, "limit": limit, "cocktails": cocktails}


@app.get("/cocktails/{cocktail_id}")
def get_cocktail(cocktail_id: str):
    """Get a single cocktail by ID from SQLite."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    row = con.execute("SELECT * FROM cocktails WHERE id = ?", (cocktail_id,)).fetchone()
    if not row:
        con.close()
        raise HTTPException(status_code=404, detail="Cocktail not found")

    c = dict(row)
    c["ingredients"]    = [dict(r) for r in con.execute(
        "SELECT ingredient, measure FROM ingredients WHERE cocktail_id = ?", (cocktail_id,))]
    c["flavor_profile"] = [r[0] for r in con.execute(
        "SELECT flavor FROM flavor_profiles WHERE cocktail_id = ?", (cocktail_id,))]
    c["mood"]           = [r[0] for r in con.execute(
        "SELECT mood FROM moods WHERE cocktail_id = ?", (cocktail_id,))]
    c["best_for"]       = [r[0] for r in con.execute(
        "SELECT use_case FROM best_for WHERE cocktail_id = ?", (cocktail_id,))]

    con.close()
    return c
