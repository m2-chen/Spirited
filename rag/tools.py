"""
Step 4 — Agents & Tool Use
Four tools the agent can autonomously call:
  1. filter_by_ingredients  — what can I make with what I have?
  2. get_substitution       — LLM-powered ingredient substitution
  3. search_cocktail_trends — Tavily web search for trends
  4. generate_pro_notes     — professional preparation guide for bartenders
"""

import json
import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from tavily import TavilyClient

load_dotenv(Path(__file__).parent.parent / ".env")

DB_PATH = Path(__file__).parent.parent / "data" / "cocktails.db"


def _get_connection():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

# ── OpenAI function definitions (sent to the LLM) ──────────────────────────

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "filter_by_ingredients",
            "description": (
                "Find cocktails the user can make with the ingredients they have available. "
                "Call this when the user lists ingredients they own and asks what they can make."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ingredients": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Ingredients the user has available, e.g. ['rum', 'lime', 'mint']"
                    }
                },
                "required": ["ingredients"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_substitution",
            "description": (
                "Suggest the best substitute for a missing ingredient in a cocktail. "
                "Call this when the user says they don't have a specific ingredient."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "missing_ingredient": {
                        "type": "string",
                        "description": "The ingredient the user is missing, e.g. 'Campari'"
                    },
                    "cocktail_name": {
                        "type": "string",
                        "description": "The cocktail being made, e.g. 'Negroni'"
                    },
                    "other_ingredients": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Other ingredients in the recipe"
                    }
                },
                "required": ["missing_ingredient", "cocktail_name", "other_ingredients"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_pro_notes",
            "description": (
                "Generate a professional preparation guide for a cocktail. "
                "ALWAYS call this when the user is in bartender mode and asks about a specific cocktail recipe or technique."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cocktail_name": {
                        "type": "string",
                        "description": "Name of the cocktail, e.g. 'Negroni'"
                    },
                    "ingredients": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of ingredients in the cocktail"
                    },
                    "instructions": {
                        "type": "string",
                        "description": "Base preparation instructions from the recipe"
                    }
                },
                "required": ["cocktail_name", "ingredients", "instructions"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_shopping_list",
            "description": (
                "Generate a categorized shopping list of ingredients needed to make a cocktail. "
                "Call this when the user asks what ingredients they need, what to buy, or asks for a shopping list."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cocktail_name": {
                        "type": "string",
                        "description": "Name of the cocktail"
                    },
                    "ingredients": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of ingredients with measures, e.g. ['1 oz Calvados', '1 oz Cointreau']"
                    }
                },
                "required": ["cocktail_name", "ingredients"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_cocktail_trends",
            "description": (
                "Search the web for trending cocktails, seasonal specials, new recipes, or cocktail news. "
                "Call this when the user asks about trends, what's popular, or anything requiring up-to-date information."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Web search query, e.g. 'trending summer cocktails 2025'"
                    }
                },
                "required": ["query"]
            }
        }
    }
]


# ── Tool implementations ────────────────────────────────────────────────────

def filter_by_ingredients(ingredients: list[str]) -> dict:
    """
    Queries SQLite to find cocktails where all required ingredients
    are available. Partial matches (missing 1) are also returned.
    """
    user_ingredients = {i.lower().strip() for i in ingredients}
    con = _get_connection()

    # Get all cocktails with their ingredients
    cocktail_rows = con.execute("SELECT id, name, instructions, strength, thumbnail FROM cocktails").fetchall()

    exact_matches = []
    close_matches = []

    for row in cocktail_rows:
        cid = row["id"]
        ing_rows = con.execute(
            "SELECT ingredient, measure FROM ingredients WHERE cocktail_id = ?", (cid,)
        ).fetchall()
        required = {r["ingredient"].lower().strip() for r in ing_rows}
        missing  = required - user_ingredients

        flavors = [r[0] for r in con.execute(
            "SELECT flavor FROM flavor_profiles WHERE cocktail_id = ?", (cid,))]

        entry = {
            "name":         row["name"],
            "ingredients":  [dict(r) for r in ing_rows],
            "instructions": row["instructions"],
            "strength":     row["strength"] or "",
            "flavor_profile": flavors,
            "thumbnail":    row["thumbnail"] or "",
            "missing":      list(missing)
        }

        if len(missing) == 0:
            exact_matches.append(entry)
        elif len(missing) == 1:
            close_matches.append(entry)

    con.close()

    return {
        "exact_matches": exact_matches[:5],
        "close_matches": close_matches[:5],
        "total_exact":   len(exact_matches),
        "total_close":   len(close_matches)
    }


def get_substitution(missing_ingredient: str, cocktail_name: str, other_ingredients: list[str]) -> dict:
    """
    Uses the LLM to reason about the best substitute for a missing ingredient,
    considering the flavor profile of the cocktail.
    """
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    prompt = f"""You are an expert bartender. A user is making a {cocktail_name} but is missing {missing_ingredient}.
The other ingredients in the recipe are: {', '.join(other_ingredients)}.

Suggest the 2 best substitutes for {missing_ingredient} in this specific cocktail context.
For each substitute explain:
- What it is
- How it changes the flavor
- Any adjustment to the quantity

Return ONLY a valid JSON object:
{{
  "missing": "{missing_ingredient}",
  "cocktail": "{cocktail_name}",
  "substitutes": [
    {{
      "name": "substitute name",
      "reason": "why it works",
      "flavor_change": "how it changes the taste",
      "quantity_adjustment": "any change to amount"
    }}
  ]
}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=400,
        response_format={"type": "json_object"}
    )

    return json.loads(response.choices[0].message.content)


def generate_shopping_list(cocktail_name: str, ingredients: list[str]) -> dict:
    """
    Uses the LLM to categorize cocktail ingredients into a structured shopping list.
    Groups into: Base Spirits, Liqueurs & Mixers, Fresh & Perishables, Garnishes, Equipment.
    Flags items the user likely already has at home.
    """
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    prompt = f"""You are an expert bartender building a shopping list for: {cocktail_name}
Ingredients: {', '.join(ingredients)}

Categorize each ingredient into one of these groups:
- "Base Spirits" (whiskey, vodka, rum, gin, tequila, brandy, etc.)
- "Liqueurs & Mixers" (Cointreau, vermouth, bitters, syrups, juices, sodas, etc.)
- "Fresh & Perishables" (fresh citrus juice, eggs, cream, fresh herbs, etc.)
- "Garnishes" (citrus slices, cherries, olives, herbs for garnish, salt/sugar rim, etc.)
- "Equipment" (shaker, strainer, specific glassware only if non-standard)

For each item set "likely_have" to true only if it's a pantry staple most people own (e.g. ice, sugar, salt, water).
IMPORTANT: Express all quantities in ml (not oz). 1 oz = 30ml, 1/2 oz = 15ml, 1 tsp = 5ml.

Return ONLY valid JSON:
{{
  "cocktail": "{cocktail_name}",
  "categories": [
    {{
      "name": "category name",
      "icon": "single emoji",
      "items": [
        {{
          "ingredient": "ingredient name only (no measure)",
          "measure": "amount e.g. 1 oz or 'to taste'",
          "likely_have": false
        }}
      ]
    }}
  ],
  "tip": "one short practical shopping tip for this cocktail"
}}
Only include categories that have at least one item. No markdown."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=600,
        response_format={"type": "json_object"}
    )

    return json.loads(response.choices[0].message.content)


def search_cocktail_trends(query: str) -> dict:
    """
    Uses Tavily to search the web for cocktail trends and news.
    """
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

    results = client.search(
        query=query,
        search_depth="basic",
        max_results=4,
        include_answer=True
    )

    return {
        "query": query,
        "summary": results.get("answer", ""),
        "sources": [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", "")[:300]
            }
            for r in results.get("results", [])
        ]
    }


def generate_pro_notes(cocktail_name: str, ingredients: list[str], instructions: str) -> dict:
    """
    Generates a structured professional preparation guide for a cocktail.
    Called autonomously by the agent in bartender mode.
    """
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    prompt = f"""You are a master bartender with 20 years of experience.
Generate a professional preparation guide for: {cocktail_name}
Ingredients: {', '.join(ingredients)}
Base instructions: {instructions}
IMPORTANT: Always express quantities in ml (not oz). 1 oz = 30ml.

Return ONLY a valid JSON object with exactly these fields:
{{
  "ratio": "<the ratio logic and why it works — e.g. 1:1:1 equal parts, balance theory>",
  "technique": "<precise technique — stir vs shake, duration, temperature, dilution, straining method>",
  "garnish": "<garnish detail and technique — express vs drop, preparation, alternatives>",
  "mistakes": "<the single most common mistake bartenders make with this specific cocktail>",
  "variations": "<2-3 well-known variations with the key difference for each>"
}}
Be concise, professional, and precise. No markdown. Plain text values only."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=500,
        response_format={"type": "json_object"}
    )

    return json.loads(response.choices[0].message.content)


# ── Tool dispatcher ─────────────────────────────────────────────────────────

def execute_tool(tool_name: str, tool_args: dict) -> str:
    """Routes tool calls from the LLM to the correct function."""
    if tool_name == "filter_by_ingredients":
        result = filter_by_ingredients(**tool_args)
    elif tool_name == "get_substitution":
        result = get_substitution(**tool_args)
    elif tool_name == "search_cocktail_trends":
        result = search_cocktail_trends(**tool_args)
    elif tool_name == "generate_pro_notes":
        result = generate_pro_notes(**tool_args)
    elif tool_name == "generate_shopping_list":
        result = generate_shopping_list(**tool_args)
    else:
        result = {"error": f"Unknown tool: {tool_name}"}

    return json.dumps(result)
