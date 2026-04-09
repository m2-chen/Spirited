"""
Step 2b — Vector Store
Embeds cocktail documents using OpenAI and loads them into ChromaDB.
Run this script once enrichment is complete (or re-run to refresh).
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
import chromadb
from openai import OpenAI
from document_builder import build_document

load_dotenv(Path(__file__).parent.parent / ".env")

DATA_PATH = Path(__file__).parent.parent / "data" / "cocktails_enriched.json"
CHROMA_PATH = Path(__file__).parent.parent / "data" / "chroma_db"
COLLECTION_NAME = "cocktails"
EMBED_MODEL = "text-embedding-3-small"
BATCH_SIZE = 50  # OpenAI embedding batch limit


def get_collection(client: chromadb.Client):
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}  # use cosine similarity
    )


def embed_batch(openai_client: OpenAI, texts: list[str]) -> list[list[float]]:
    response = openai_client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [r.embedding for r in response.data]


def build_vector_store():
    print("Loading cocktail data...")
    cocktails = json.loads(DATA_PATH.read_text())
    print(f"  {len(cocktails)} cocktails loaded")

    openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = get_collection(chroma_client)

    # Skip already embedded cocktails
    existing_ids = set(collection.get()["ids"])
    cocktails = [c for c in cocktails if c["id"] not in existing_ids]

    if not cocktails:
        print("  All cocktails already embedded. Nothing to do.")
        return

    print(f"  Embedding {len(cocktails)} cocktails in batches of {BATCH_SIZE}...")

    for i in range(0, len(cocktails), BATCH_SIZE):
        batch = cocktails[i: i + BATCH_SIZE]
        documents = [build_document(c) for c in batch]
        embeddings = embed_batch(openai_client, documents)

        collection.add(
            ids=[c["id"] for c in batch],
            embeddings=embeddings,
            documents=documents,
            metadatas=[{
                "name": c["name"],
                "category": c.get("category", ""),
                "alcoholic": c.get("alcoholic", ""),
                "glass": c.get("glass", ""),
                "strength": c.get("strength", ""),
                "flavor_profile": ", ".join(c.get("flavor_profile", [])),
                "mood": ", ".join(c.get("mood", [])),
                "best_for": ", ".join(c.get("best_for", [])),
                "thumbnail": c.get("thumbnail", ""),
                "ingredients": json.dumps(c.get("ingredients", [])),
                "instructions": c.get("instructions", ""),
            } for c in batch],
        )
        print(f"  [{min(i + BATCH_SIZE, len(cocktails) + i)}/{len(cocktails)}] batch embedded")

    total = collection.count()
    print(f"\nDone. {total} cocktails stored in ChromaDB at {CHROMA_PATH}")


if __name__ == "__main__":
    build_vector_store()
