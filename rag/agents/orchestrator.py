"""
OrchestratorAgent — the manager
Coordinates all agents, decides what to run, and aggregates the final response.
PreparationAgent and ShoppingAgent run in PARALLEL when triggered.
EventPlannerAgent handles party/event planning queries.
"""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from agents.retrieval_agent import RetrievalAgent
from agents.recommendation_agent import RecommendationAgent
from agents.preparation_agent import PreparationAgent
from agents.shopping_agent import ShoppingAgent
from agents.event_agent import EventPlannerAgent


PREP_KEYWORDS = [
    "how to make", "how do i make", "how can i make",
    "how to prepare", "how do i prepare", "how can i prepare",
    "how do you make", "how do you prepare",
    "how to mix", "how do i mix", "how can i mix",
    "recipe for", "make a ", "prepare the", "prepare that",
    "prepare it", "prepare this", "preparation", "can you make",
    "show me how", "walk me through"
]

SHOPPING_KEYWORDS = [
    "ingredient", "need to buy", "shopping", "what do i need",
    "what ingredients", "go buy"
]

EVENT_KEYWORDS = [
    "party", "event", "gathering", "birthday", "wedding", "anniversary",
    "corporate", "dinner party", "cocktail party", "brunch", "reception",
    "hosting", "organize", "organise", "guests", "crowd", "people coming",
    "plan a", "planning a", "planning an", "preparing for", "celebrate"
]


class OrchestratorAgent:
    """
    The central coordinator. Responsibilities:
    1. Always runs RetrievalAgent (no LLM, fast)
    2. Routes to EventPlannerAgent for event queries
    3. Otherwise runs RecommendationAgent + optionally PreparationAgent & ShoppingAgent in parallel
    """

    def __init__(self):
        self.retrieval    = RetrievalAgent()
        self.recommendation = RecommendationAgent()
        self.preparation  = PreparationAgent()
        self.shopping     = ShoppingAgent()
        self.event        = EventPlannerAgent()

    def run(self, user_message: str, chat_history: list[dict] = None, mode: str = "guest") -> dict:
        print(f"\n[Orchestrator] ── New request ──────────────────────────")
        print(f"[Orchestrator] Message: '{user_message[:80]}'")

        msg_lower = user_message.lower()

        # ── Step 1: Retrieve relevant cocktails (no LLM, always runs) ─────
        # If the current message looks like a chip answer (short, no question words),
        # combine it with the last user message from history for richer RAG retrieval.
        # e.g. "An alcoholic drink, More tropical and sweet" → loses "kiwi" context
        rag_query = user_message
        if chat_history and len(user_message.split()) <= 10:
            question_words = {"what", "which", "how", "where", "when", "why", "who", "?"}
            is_chip_answer = not any(w in user_message.lower() for w in question_words)
            if is_chip_answer:
                for msg in reversed(chat_history):
                    if msg.get("role") == "user":
                        rag_query = msg["content"] + " " + user_message
                        print(f"[Orchestrator] RAG query enriched: '{rag_query[:100]}'")
                        break

        rag_context = self.retrieval.run(rag_query)

        # ── Step 2: Detect event intent and route accordingly ─────────────
        is_event_query = any(kw in msg_lower for kw in EVENT_KEYWORDS)

        # Also treat as event if recent history contains event context
        if not is_event_query and chat_history:
            recent = " ".join(m.get("content", "") for m in chat_history[-4:]).lower()
            is_event_query = any(kw in recent for kw in EVENT_KEYWORDS)

        if is_event_query:
            print(f"[Orchestrator] → Routing to EventPlannerAgent")
            result = self.event.run(user_message, rag_context, chat_history)

            # Shopping list is NOT generated automatically — user must confirm the menu first

            # Normalise response so the frontend ChatResponse model is satisfied
            result.setdefault("recommendations", [])
            result.setdefault("clarifying_questions", [])
            result.setdefault("follow_up", "")
            result.setdefault("cocktail_fact", "")
            print(f"[Orchestrator] ── Done (Event) ───────────────────────\n")
            return result

        # ── Step 3: Standard flow — RecommendationAgent ───────────────────
        result = self.recommendation.run(user_message, rag_context, chat_history)

        intent      = result.get("intent", "")
        is_followup = intent == "follow_up"
        recs        = result.get("recommendations", [])

        is_prep_query     = any(kw in msg_lower for kw in PREP_KEYWORDS)
        is_shopping_query = any(kw in msg_lower for kw in SHOPPING_KEYWORDS)

        # Use RAG context as fallback cocktail source when LLM returned no recs
        cocktail_source = recs[0] if recs else (rag_context[0] if rag_context else None)

        needs_prep     = not is_followup and is_prep_query and cocktail_source is not None
        needs_shopping = is_shopping_query and cocktail_source is not None

        # ── Step 4: Run parallel agents (ThreadPoolExecutor) ─────────────
        if needs_prep or needs_shopping:
            print(f"[Orchestrator] Launching parallel agents — prep:{needs_prep} shopping:{needs_shopping}")
            futures = {}

            with ThreadPoolExecutor(max_workers=2) as executor:
                if needs_prep:
                    futures["prep"] = executor.submit(self.preparation.run, cocktail_source)
                if needs_shopping:
                    futures["shopping"] = executor.submit(self.shopping.run, cocktail_source)

            if "prep" in futures:
                pro_notes = futures["prep"].result()
                cocktail_name = cocktail_source.get("name", "").lower()
                injected = False
                for rec in recs:
                    if cocktail_name in rec.get("name", "").lower():
                        rec["pro_notes"] = pro_notes
                        injected = True
                        break
                if not injected and recs:
                    recs[0]["pro_notes"] = pro_notes

            if "shopping" in futures:
                result["shopping_list"] = futures["shopping"].result()

        print(f"[Orchestrator] ── Done ──────────────────────────────────\n")
        return result
