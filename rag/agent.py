"""
Step 4 — Agent Loop
Orchestrates RAG retrieval + LLM + tool use in a single pipeline.
The LLM autonomously decides when to call tools.
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent / ".env")
sys.path.append(str(Path(__file__).parent))

from retriever import CocktailRetriever
from prompt import build_prompt
from tools import TOOLS_SCHEMA, execute_tool
from units import convert_ingredients, oz_to_ml

MAX_TOOL_ROUNDS = 3  # prevent infinite loops


class MixologistAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self.retriever = CocktailRetriever()

    def run(self, user_message: str, chat_history: list[dict] = None, mode: str = "guest") -> dict:
        """
        Full agent pipeline:
        1. Retrieve relevant cocktails via RAG
        2. Build prompt with context
        3. Call LLM with tools available
        4. If LLM calls a tool → execute it → send result back to LLM
        5. Return final structured JSON response
        """
        # Step 1 — RAG retrieval
        rag_context = self.retriever.retrieve(user_message, top_k=4)

        # Step 2 — Build messages
        messages = build_prompt(user_message, rag_context, mode=mode)

        # Inject chat history for multi-turn conversation
        if chat_history:
            messages = messages[:1] + chat_history + messages[1:]

        # Detect if this is a shopping list / ingredients query
        ingredient_keywords = ["ingredient", "need to buy", "shopping", "what do i need", "what ingredients", "go buy"]
        is_ingredients_query = any(kw in user_message.lower() for kw in ingredient_keywords)

        # Step 3 — Agentic loop
        pro_notes_result = None
        pro_notes_cocktail = None
        shopping_list_result = None
        for round_num in range(MAX_TOOL_ROUNDS):
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=TOOLS_SCHEMA,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1500,
                response_format={"type": "json_object"},
            )

            choice = response.choices[0]

            # No tool call → final answer
            if choice.finish_reason == "stop":
                result = json.loads(choice.message.content)

                # Guarantee message is never empty for recipe/bartender intents
                if not result.get("message") and result.get("recommendations"):
                    first_name = result["recommendations"][0].get("name", "this cocktail")
                    result["message"] = f"{first_name} — your preparation guide is ready below."

                # Never force any tool calls for conversational follow-ups
                is_followup = result.get("intent") == "follow_up"

                # Force generate_pro_notes only when user is explicitly asking HOW TO PREPARE
                prep_keywords = ["how to make", "how do i make", "how to prepare", "how do i prepare",
                                 "how to mix", "recipe for", "make a ", "prepare the", "preparation"]
                is_prep_query = any(kw in user_message.lower() for kw in prep_keywords)

                needs_pro_notes = (
                    not is_followup
                    and not pro_notes_result
                    and is_prep_query
                    and result.get("recommendations")
                )
                if needs_pro_notes:
                    rec = result["recommendations"][0]
                    print(f"  [AGENT] Force-calling generate_pro_notes for: {rec.get('name')}")
                    tool_result = execute_tool("generate_pro_notes", {
                        "cocktail_name": rec.get("name", ""),
                        "ingredients": [
                            f"{i.get('measure', '')} {i.get('ingredient', '')}".strip()
                            for i in (rec.get("ingredients") or [])
                        ],
                        "instructions": rec.get("instructions", "")
                    })
                    pro_notes_result = json.loads(tool_result)
                    pro_notes_cocktail = rec.get("name", "").lower()

                # Force shopping list if ingredients query and not already called
                if not is_followup and is_ingredients_query and not shopping_list_result and result.get("recommendations"):
                    rec = result["recommendations"][0]
                    print(f"  [AGENT] Force-calling generate_shopping_list for: {rec.get('name')}")
                    tool_result = execute_tool("generate_shopping_list", {
                        "cocktail_name": rec.get("name", ""),
                        "ingredients": [
                            f"{oz_to_ml(i.get('measure', '') or '')} {i.get('ingredient', '')}".strip()
                            for i in (rec.get("ingredients") or [])
                        ]
                    })
                    shopping_list_result = json.loads(tool_result)

                # Inject pro_notes into the matching recommendation by name
                if pro_notes_result and result.get("recommendations"):
                    for rec in result["recommendations"]:
                        if pro_notes_cocktail and pro_notes_cocktail in rec.get("name", "").lower():
                            rec["pro_notes"] = pro_notes_result
                            break
                    else:
                        result["recommendations"][0]["pro_notes"] = pro_notes_result

                # Convert all recommendation ingredient measures to ml (skip for follow-ups)
                if not is_followup:
                    for rec in result.get("recommendations", []):
                        if rec.get("ingredients"):
                            rec["ingredients"] = convert_ingredients(rec["ingredients"])

                # Inject shopping list into result
                if shopping_list_result:
                    result["shopping_list"] = shopping_list_result

                return result

            # Tool call detected → execute and loop back
            if choice.finish_reason == "tool_calls":
                messages.append(choice.message)

                for tool_call in choice.message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    print(f"  [AGENT] Calling tool: {tool_name}({list(tool_args.keys())})")
                    tool_result = execute_tool(tool_name, tool_args)

                    # Store pro_notes result + cocktail name to inject later
                    if tool_name == "generate_pro_notes":
                        pro_notes_result = json.loads(tool_result)
                        pro_notes_cocktail = tool_args.get("cocktail_name", "").lower()
                    elif tool_name == "generate_shopping_list":
                        shopping_list_result = json.loads(tool_result)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result
                    })

        # Fallback if max rounds hit
        return {"intent": "error", "message": "I ran into an issue. Please try again.", "recommendations": [], "clarifying_questions": [], "follow_up": "", "cocktail_fact": ""}


if __name__ == "__main__":
    agent = MixologistAgent()

    tests = [
        "I have rum, lime juice, mint and sugar at home. What cocktail can I make?",
        "I want to make a Negroni but I don't have Campari. What can I use instead?",
        "What are the most trendy cocktails right now in 2025?",
    ]

    for query in tests:
        print(f"\n{'='*60}")
        print(f"USER: {query}")
        print("="*60)
        result = agent.run(query)
        print(f"INTENT : {result.get('intent')}")
        print(f"MESSAGE: {result.get('message')}")
        if result.get("recommendations"):
            for r in result["recommendations"]:
                print(f"  🍹 {r['name']} — {r.get('why', '')[:80]}")
        print(f"FACT   : {result.get('cocktail_fact')}")
