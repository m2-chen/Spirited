"""
RetrievalAgent — no LLM, pure Python/SQL
Embeds the user query and retrieves the most relevant cocktails
from SQLite using cosine similarity + keyword reranking.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from retriever import CocktailRetriever


class RetrievalAgent:
    """
    Responsible for: finding the right cocktails from the database.
    No LLM involved — pure embedding + cosine similarity + keyword reranking.
    """

    def __init__(self):
        self.retriever = CocktailRetriever()

    def run(self, query: str, top_k: int = 4) -> list[dict]:
        print(f"  [RetrievalAgent] Searching for: '{query[:60]}...' " if len(query) > 60 else f"  [RetrievalAgent] Searching for: '{query}'")
        results = self.retriever.retrieve(query, top_k=top_k)
        print(f"  [RetrievalAgent] Found: {[r['name'] for r in results]}")
        return results
