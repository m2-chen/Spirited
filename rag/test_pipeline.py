"""
Quick end-to-end test: RAG retrieval → prompt builder → LLM response
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

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
retriever = CocktailRetriever()

def ask(query: str):
    print(f"\n{'='*60}")
    print(f"USER: {query}")
    print('='*60)

    context = retriever.retrieve(query, top_k=4)
    messages = build_prompt(query, context)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=1500,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    result = json.loads(raw)

    print(f"INTENT : {result.get('intent')}")
    print(f"MESSAGE: {result.get('message')}")

    if result.get("clarifying_questions"):
        print("QUESTIONS:")
        for q in result["clarifying_questions"]:
            print(f"  - {q}")

    if result.get("recommendations"):
        print("RECOMMENDATIONS:")
        for r in result["recommendations"]:
            print(f"  🍹 {r['name']} ({r.get('strength')}) — {r.get('why')}")

    print(f"FOLLOW-UP: {result.get('follow_up')}")
    print(f"FACT: {result.get('cocktail_fact')}")


if __name__ == "__main__":
    ask("I want something nice tonight")
    ask("Something fruity and refreshing for a hot summer day, not too strong")
    ask("How do I make a Negroni?")
    ask("Can you help me book a flight?")
