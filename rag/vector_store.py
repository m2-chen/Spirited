"""
Step 2b — Vector Store (SQLite version)
Embeds cocktail documents using OpenAI and stores them in the SQLite database.
Run this script once, or re-run to embed any cocktails missing embeddings.
"""

import json
import os
import sqlite3
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from document_builder import build_document

load_dotenv(Path(__file__).parent.parent / ".env")

DB_PATH        = Path(__file__).parent.parent / "data" / "cocktails.db"
EMBED_MODEL    = "text-embedding-3-small"
BATCH_SIZE     = 50


def get_connection():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def ensure_embeddings_table(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            cocktail_id TEXT PRIMARY KEY REFERENCES cocktails(id) ON DELETE CASCADE,
            document    TEXT NOT NULL,
            embedding   TEXT NOT NULL
        )
    """)
    con.commit()


def load_cocktail(con, cocktail_id: str) -> dict:
    """Reconstruct a cocktail dict from SQLite for document building."""
    row = con.execute("SELECT * FROM cocktails WHERE id = ?", (cocktail_id,)).fetchone()
    if not row:
        return {}
    c = dict(row)
    c["ingredients"]    = [dict(r) for r in con.execute(
        "SELECT ingredient, measure FROM ingredients WHERE cocktail_id = ?", (cocktail_id,))]
    c["flavor_profile"] = [r[0] for r in con.execute(
        "SELECT flavor FROM flavor_profiles WHERE cocktail_id = ?", (cocktail_id,))]
    c["mood"]           = [r[0] for r in con.execute(
        "SELECT mood FROM moods WHERE cocktail_id = ?", (cocktail_id,))]
    c["taste_tags"]     = [r[0] for r in con.execute(
        "SELECT tag FROM taste_tags WHERE cocktail_id = ?", (cocktail_id,))]
    c["best_for"]       = [r[0] for r in con.execute(
        "SELECT use_case FROM best_for WHERE cocktail_id = ?", (cocktail_id,))]
    return c


def embed_batch(client: OpenAI, texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [r.embedding for r in response.data]


def build_vector_store():
    con = get_connection()
    ensure_embeddings_table(con)

    # Find cocktails not yet embedded
    all_ids     = {r[0] for r in con.execute("SELECT id FROM cocktails")}
    embedded_ids = {r[0] for r in con.execute("SELECT cocktail_id FROM embeddings")}
    pending_ids  = list(all_ids - embedded_ids)

    if not pending_ids:
        print("All cocktails already embedded. Nothing to do.")
        con.close()
        return

    print(f"Embedding {len(pending_ids)} cocktails in batches of {BATCH_SIZE}...")
    openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    for i in range(0, len(pending_ids), BATCH_SIZE):
        batch_ids = pending_ids[i: i + BATCH_SIZE]
        cocktails = [load_cocktail(con, cid) for cid in batch_ids]
        documents = [build_document(c) for c in cocktails]
        embeddings = embed_batch(openai_client, documents)

        con.executemany(
            "INSERT OR REPLACE INTO embeddings (cocktail_id, document, embedding) VALUES (?, ?, ?)",
            [(cid, doc, json.dumps(emb))
             for cid, doc, emb in zip(batch_ids, documents, embeddings)]
        )
        con.commit()
        print(f"  [{min(i + BATCH_SIZE, len(pending_ids))}/{len(pending_ids)}] embedded")

    total = con.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
    print(f"\nDone. {total} cocktails embedded in {DB_PATH}")
    con.close()


if __name__ == "__main__":
    build_vector_store()
