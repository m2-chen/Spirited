"""
RecommendationAgent — LLM-powered
Takes retrieved cocktails + user message and crafts personalized recommendations.
Handles: intent detection, clarification, discovery, follow-up, off-topic.
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent.parent / ".env")
sys.path.append(str(Path(__file__).parent.parent))

from prompt import build_prompt
from units import convert_ingredients


class RecommendationAgent:
    """
    Responsible for: understanding what the user wants and recommending cocktails.
    Uses the proven build_prompt (with few-shot examples) to ground its output.
    Uses the RAG context from RetrievalAgent.
    """

    def __init__(self):
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    def run(self, user_message: str, rag_context: list[dict], history: list[dict] = None) -> dict:
        print(f"  [RecommendationAgent] Processing message...")

        # Use the proven prompt builder with full few-shot examples
        messages = build_prompt(user_message, rag_context, mode="guest")

        # Inject chat history for multi-turn conversation
        if history:
            messages = messages[:1] + history + messages[1:]

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)

        # Guarantee message is never empty when recommendations exist
        if not result.get("message") and result.get("recommendations"):
            first_name = result["recommendations"][0].get("name", "this cocktail")
            result["message"] = f"{first_name} — here's what you need to know."

        # Convert ingredient measures to ml
        is_followup = result.get("intent") == "follow_up"
        if not is_followup:
            for rec in result.get("recommendations", []):
                if rec.get("ingredients"):
                    rec["ingredients"] = convert_ingredients(rec["ingredients"])

        print(f"  [RecommendationAgent] Intent: {result.get('intent')} | Recommendations: {len(result.get('recommendations', []))}")
        return result
