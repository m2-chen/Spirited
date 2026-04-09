"""
Step 5 — Backend API
FastAPI server exposing the Mixologist agent as a REST API.
"""

import json
import sys
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

load_dotenv(Path(__file__).parent.parent / ".env")
sys.path.append(str(Path(__file__).parent.parent / "rag"))

from agent import MixologistAgent
from api.models import ChatRequest, ChatResponse

app = FastAPI(title="AI Mixologist API", version="1.0.0")

# Allow frontend to talk to the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single agent instance shared across requests
agent = MixologistAgent()

# Serve frontend
FRONTEND_PATH = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_PATH)), name="static")

@app.get("/")
def serve_frontend():
    return FileResponse(str(FRONTEND_PATH / "index.html"))


@app.get("/health")
def health():
    return {"status": "ok", "agent": "AI Mixologist"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        # Convert history to the format the agent expects
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.history
        ]

        result = agent.run(
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
    """Browse the cocktail database with optional filters."""
    data_path = Path(__file__).parent.parent / "data" / "cocktails_enriched.json"
    cocktails = json.loads(data_path.read_text())

    if strength:
        cocktails = [c for c in cocktails if c.get("strength") == strength]
    if alcoholic:
        cocktails = [c for c in cocktails if c.get("alcoholic", "").lower() == alcoholic.lower()]

    total = len(cocktails)
    page = cocktails[offset: offset + limit]

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "cocktails": page
    }


@app.get("/cocktails/{cocktail_id}")
def get_cocktail(cocktail_id: str):
    """Get a single cocktail by ID."""
    data_path = Path(__file__).parent.parent / "data" / "cocktails_enriched.json"
    cocktails = json.loads(data_path.read_text())

    match = next((c for c in cocktails if c["id"] == cocktail_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Cocktail not found")

    return match
