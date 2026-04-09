"""
Step 2c — Retriever (SQLite version)
Embeds the user query, computes cosine similarity against stored embeddings,
then keyword-reranks the top candidates and fetches full data from SQLite.
"""

import json
import os
import sqlite3
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent / ".env")

DB_PATH     = Path(__file__).parent.parent / "data" / "cocktails.db"
EMBED_MODEL = "text-embedding-3-small"


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))


class CocktailRetriever:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self.db_path = DB_PATH

    def _get_connection(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def _fetch_cocktail(self, con, cocktail_id: str) -> dict:
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
        c["best_for"]       = [r[0] for r in con.execute(
            "SELECT use_case FROM best_for WHERE cocktail_id = ?", (cocktail_id,))]
        return c

    def retrieve(self, query: str, top_k: int = 4) -> list[dict]:
        # Embed the user query
        response = self.openai_client.embeddings.create(
            model=EMBED_MODEL,
            input=[query]
        )
        query_vector = response.data[0].embedding

        con = self._get_connection()

        # Load all embeddings from SQLite
        rows = con.execute("SELECT cocktail_id, document, embedding FROM embeddings").fetchall()

        # Compute cosine similarity for all cocktails
        scored = []
        for row in rows:
            emb = json.loads(row["embedding"])
            score = cosine_similarity(query_vector, emb)
            scored.append((row["cocktail_id"], row["document"], score))

        # Sort by similarity descending, take top candidates for reranking
        fetch_k = max(top_k * 4, 16)
        scored.sort(key=lambda x: x[2], reverse=True)
        candidates = scored[:fetch_k]

        # Build cocktail dicts from SQLite
        cocktails = []
        for cocktail_id, document, similarity in candidates:
            c = self._fetch_cocktail(con, cocktail_id)
            if c:
                c["similarity_score"] = round(similarity, 3)
                c["document"]         = document
                cocktails.append(c)

        con.close()

        # Keyword reranking
        stopwords = {"something", "want", "like", "with", "for", "me", "a", "an",
                     "the", "i", "to", "and", "or", "give", "make", "some", "can",
                     "have", "do", "please", "need", "get", "is", "in", "my", "any"}
        query_words = {
            w.lower().strip("?!.,")
            for w in query.split()
            if len(w) > 2 and w.lower() not in stopwords
        }

        def keyword_score(cocktail):
            searchable = cocktail["name"].lower()
            for ing in cocktail["ingredients"]:
                searchable += " " + ing.get("ingredient", "").lower()
            searchable += " " + cocktail.get("document", "").lower()
            return sum(1 for kw in query_words if kw in searchable)

        cocktails.sort(key=lambda c: (keyword_score(c), c["similarity_score"]), reverse=True)

        return cocktails[:top_k]


if __name__ == "__main__":
    retriever = CocktailRetriever()

    test_queries = [
        "something fruity and refreshing for a hot summer day",
        "a strong classic cocktail for a romantic evening",
        "how do I make a Mojito?",
        "I want something sweet but not too alcoholic for a beginner",
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 50)
        results = retriever.retrieve(query, top_k=3)
        for r in results:
            print(f"  {r['name']} (score: {r['similarity_score']}) — {r['flavor_profile']}")
