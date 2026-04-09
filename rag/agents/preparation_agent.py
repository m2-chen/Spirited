"""
PreparationAgent — LLM-powered
Generates a professional step-by-step preparation guide for a cocktail.
Runs in parallel with ShoppingAgent when triggered.
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


class PreparationAgent:
    """
    Responsible for: generating professional preparation guides.
    Triggered when user asks how to make/prepare a specific cocktail.
    Runs in parallel with ShoppingAgent.
    """

    def __init__(self):
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    def run(self, cocktail: dict) -> dict:
        name = cocktail.get("name", "")
        ingredients = [
            f"{oz_to_ml(i.get('measure', '') or '')} {i.get('ingredient', '')}".strip()
            for i in (cocktail.get("ingredients") or [])
        ]
        instructions = cocktail.get("instructions", "")

        print(f"  [PreparationAgent] Generating pro guide for: {name}")

        prompt = f"""You are a master bartender with 20 years of experience.
Generate a professional preparation guide for: {name}
Ingredients: {', '.join(ingredients)}
Base instructions: {instructions}
IMPORTANT: Always express quantities in ml (not oz). 1 oz = 30ml.

Return ONLY a valid JSON object with exactly these fields:
{{
  "ratio": "<the ratio logic and why it works>",
  "technique": "<precise technique — stir vs shake, duration, temperature, dilution, straining>",
  "garnish": "<garnish detail and technique — express vs drop, preparation, alternatives>",
  "mistakes": "<the single most common mistake bartenders make with this specific cocktail>",
  "variations": "<2-3 well-known variations with the key difference for each>"
}}
Be concise, professional, and precise. No markdown. Plain text values only."""

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=500,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        print(f"  [PreparationAgent] Pro guide ready for: {name}")
        return result
