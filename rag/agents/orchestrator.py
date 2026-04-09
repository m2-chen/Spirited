"""
OrchestratorAgent — the manager
Coordinates all agents, decides what to run, and aggregates the final response.
PreparationAgent and ShoppingAgent run in PARALLEL when triggered.
"""

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from agents.retrieval_agent import RetrievalAgent
from agents.recommendation_agent import RecommendationAgent
from agents.preparation_agent import PreparationAgent
from agents.shopping_agent import ShoppingAgent


PREP_KEYWORDS = [
    "how to make", "how do i make", "how to prepare", "how do i prepare",
    "how to mix", "recipe for", "make a ", "prepare the", "preparation"
]

SHOPPING_KEYWORDS = [
    "ingredient", "need to buy", "shopping", "what do i need",
    "what ingredients", "go buy"
]


class OrchestratorAgent:
    """
    The central coordinator. Responsibilities:
    1. Always runs RetrievalAgent (no LLM, fast)
    2. Always runs RecommendationAgent to get intent + recommendations
    3. Conditionally runs PreparationAgent + ShoppingAgent IN PARALLEL
    4. Aggregates all results into the final response
    """

    def __init__(self):
        self.retrieval      = RetrievalAgent()
        self.recommendation = RecommendationAgent()
        self.preparation    = PreparationAgent()
        self.shopping       = ShoppingAgent()

    def run(self, user_message: str, chat_history: list[dict] = None, mode: str = "guest") -> dict:
        print(f"\n[Orchestrator] ── New request ──────────────────────────")
        print(f"[Orchestrator] Message: '{user_message[:80]}'")

        # ── Step 1: Retrieve relevant cocktails (no LLM) ──────────────────
        rag_context = self.retrieval.run(user_message)

        # ── Step 2: Get recommendations + intent ──────────────────────────
        result = self.recommendation.run(user_message, rag_context, chat_history)

        intent      = result.get("intent", "")
        is_followup = intent == "follow_up"
        recs        = result.get("recommendations", [])

        # ── Step 3: Decide which parallel agents to run ───────────────────
        msg_lower       = user_message.lower()
        is_prep_query   = any(kw in msg_lower for kw in PREP_KEYWORDS)
        is_shopping_query = any(kw in msg_lower for kw in SHOPPING_KEYWORDS)

        needs_prep     = not is_followup and is_prep_query and len(recs) > 0
        needs_shopping = not is_followup and is_shopping_query and len(recs) > 0

        # ── Step 4: Run parallel agents (ThreadPoolExecutor) ─────────────
        if needs_prep or needs_shopping:
            print(f"[Orchestrator] Launching parallel agents — prep:{needs_prep} shopping:{needs_shopping}")
            futures = {}

            with ThreadPoolExecutor(max_workers=2) as executor:
                if needs_prep:
                    futures["prep"] = executor.submit(self.preparation.run, recs[0])
                if needs_shopping:
                    futures["shopping"] = executor.submit(self.shopping.run, recs[0])

            # Inject PreparationAgent result into first recommendation
            if "prep" in futures:
                pro_notes = futures["prep"].result()
                cocktail_name = recs[0].get("name", "").lower()
                injected = False
                for rec in recs:
                    if cocktail_name in rec.get("name", "").lower():
                        rec["pro_notes"] = pro_notes
                        injected = True
                        break
                if not injected:
                    recs[0]["pro_notes"] = pro_notes

            # Inject ShoppingAgent result into response
            if "shopping" in futures:
                result["shopping_list"] = futures["shopping"].result()

        print(f"[Orchestrator] ── Done ──────────────────────────────────\n")
        return result
