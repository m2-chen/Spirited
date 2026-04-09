"""
Step 2c — Retriever
Given a user query, embeds it and retrieves the top-K most similar cocktails
from ChromaDB using cosine similarity.
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
import chromadb
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent / ".env")

CHROMA_PATH = Path(__file__).parent.parent / "data" / "chroma_db"
COLLECTION_NAME = "cocktails"
EMBED_MODEL = "text-embedding-3-small"


class CocktailRetriever:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        self.collection = chroma_client.get_collection(COLLECTION_NAME)

    def retrieve(self, query: str, top_k: int = 4) -> list[dict]:
        # Embed the user query
        response = self.openai_client.embeddings.create(
            model=EMBED_MODEL,
            input=[query]
        )
        query_vector = response.data[0].embedding

        # Fetch more candidates than needed so we can rerank
        fetch_k = max(top_k * 4, 16)
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=fetch_k,
            include=["metadatas", "documents", "distances"]
        )

        cocktails = []
        for i in range(len(results["ids"][0])):
            meta = results["metadatas"][0][i]
            cocktails.append({
                "id": results["ids"][0][i],
                "name": meta["name"],
                "category": meta["category"],
                "alcoholic": meta["alcoholic"],
                "glass": meta["glass"],
                "strength": meta["strength"],
                "flavor_profile": meta["flavor_profile"],
                "mood": meta["mood"],
                "best_for": meta["best_for"],
                "thumbnail": meta["thumbnail"],
                "ingredients": json.loads(meta["ingredients"]),
                "instructions": meta["instructions"],
                "similarity_score": round(1 - results["distances"][0][i], 3),
                "document": results["documents"][0][i],
            })

        # Keyword reranking — extract meaningful words from the query
        # and boost cocktails whose ingredients/name actually contain them
        stopwords = {"something", "want", "like", "with", "for", "me", "a", "an",
                     "the", "i", "to", "and", "or", "give", "make", "some", "can",
                     "have", "do", "please", "need", "get", "is", "in", "my", "any"}
        query_words = {
            w.lower().strip("?!.,")
            for w in query.split()
            if len(w) > 2 and w.lower() not in stopwords
        }

        def keyword_score(cocktail):
            """Returns number of query keywords found in name + ingredients."""
            searchable = cocktail["name"].lower()
            for ing in cocktail["ingredients"]:
                searchable += " " + ing.get("ingredient", "").lower()
            searchable += " " + cocktail.get("document", "").lower()
            return sum(1 for kw in query_words if kw in searchable)

        # Sort: keyword matches first, then by semantic similarity
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
