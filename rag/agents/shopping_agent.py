"""
ShoppingAgent — LLM-powered
Generates a categorized shopping list for a cocktail.
Runs in parallel with PreparationAgent when triggered.
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent.parent / ".env")
sys.path.append(str(Path(__file__).parent.parent))

from units import oz_to_ml


class ShoppingAgent:
    """
    Responsible for: building categorized shopping lists with WhatsApp sharing.
    Triggered when user asks what ingredients they need or want a shopping list.
    Runs in parallel with PreparationAgent.
    """

    def __init__(self):
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    def run(self, cocktail: dict) -> dict:
        name = cocktail.get("name", "")
        ingredients = [
            f"{oz_to_ml(i.get('measure', '') or '')} {i.get('ingredient', '')}".strip()
            for i in (cocktail.get("ingredients") or [])
        ]

        print(f"  [ShoppingAgent] Building shopping list for: {name}")

        prompt = f"""You are an expert bartender building a shopping list for: {name}
Ingredients: {', '.join(ingredients)}

Categorize each ingredient into one of these groups:
- "Base Spirits" (whiskey, vodka, rum, gin, tequila, brandy, etc.)
- "Liqueurs & Mixers" (Cointreau, vermouth, bitters, syrups, juices, sodas, etc.)
- "Fresh & Perishables" (fresh citrus juice, eggs, cream, fresh herbs, etc.)
- "Garnishes" (citrus slices, cherries, olives, herbs for garnish, salt/sugar rim, etc.)
- "Equipment" (shaker, strainer, specific glassware only if non-standard)

For each item set "likely_have" to true only if it's a pantry staple most people own (ice, sugar, salt, water).
IMPORTANT: Express all quantities in ml (not oz). 1 oz = 30ml, 1/2 oz = 15ml, 1 tsp = 5ml.

Return ONLY valid JSON:
{{
  "cocktail": "{name}",
  "categories": [
    {{
      "name": "category name",
      "icon": "single emoji",
      "items": [
        {{
          "ingredient": "ingredient name only (no measure)",
          "measure": "amount in ml or 'to taste'",
          "likely_have": false
        }}
      ]
    }}
  ],
  "tip": "one short practical shopping tip for this cocktail"
}}
Only include categories that have at least one item. No markdown."""

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=600,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        print(f"  [ShoppingAgent] Shopping list ready for: {name}")
        return result
