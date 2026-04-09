"""
Step 1b — Data Enrichment
Uses OpenAI API to enrich each cocktail with:
  - flavor_profile (e.g. citrusy, sweet, smoky)
  - mood (e.g. relaxing, party, romantic)
  - strength (light / medium / strong)
  - taste_tags (e.g. fruity, dry, creamy)
  - best_for (e.g. beginners, hot weather, brunch)

Saves progress incrementally — safe to interrupt and resume.
Output: data/cocktails_enriched.json
"""

import json
import time
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent / ".env")

BASE_PATH = Path(__file__).parent.parent / "data"
INPUT_PATH = BASE_PATH / "cocktails.json"
OUTPUT_PATH = BASE_PATH / "cocktails_enriched.json"

API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = "gpt-4o-mini"  # fast, cheap, reliable

SYSTEM_PROMPT = """You are a professional bartender and flavor expert.
Given a cocktail's name and ingredients, return ONLY a valid JSON object with these fields:
{
  "flavor_profile": [list of 2-4 flavor descriptors, e.g. "citrusy", "sweet", "bitter", "smoky", "herbal", "refreshing"],
  "mood": [list of 2-3 occasion/mood tags, e.g. "relaxing", "party", "romantic", "summer", "cozy", "energetic"],
  "strength": one of "light", "medium", "strong",
  "taste_tags": [list of 2-4 taste descriptors a customer would use, e.g. "fruity", "not too sweet", "dry", "creamy", "tangy"],
  "best_for": [list of 2-3 context tags, e.g. "beginners", "hot weather", "after dinner", "brunch", "celebrations"]
}
Return ONLY the JSON. No explanation, no markdown, no extra text."""


def build_user_message(cocktail: dict) -> str:
    ingredients = ", ".join(i["ingredient"] for i in cocktail["ingredients"])
    return (
        f"Cocktail: {cocktail['name']}\n"
        f"Category: {cocktail['category']}\n"
        f"Alcoholic: {cocktail['alcoholic']}\n"
        f"Ingredients: {ingredients}"
    )


def enrich_cocktail(client: OpenAI, cocktail: dict) -> dict:
    max_retries = 5
    backoff = 3

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_message(cocktail)},
                ],
                temperature=0.2,
                max_tokens=200,
            )
            raw = response.choices[0].message.content.strip()

            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            enrichment = json.loads(raw)
            return {**cocktail, **enrichment}

        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                wait = backoff * (2 ** attempt)
                print(f"  [RATE LIMIT] Waiting {wait}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait)
            else:
                raise e

    raise Exception(f"Failed after {max_retries} retries")


def load_progress() -> dict:
    if OUTPUT_PATH.exists():
        existing = json.loads(OUTPUT_PATH.read_text())
        return {c["id"]: c for c in existing}
    return {}


def save_progress(enriched: dict):
    OUTPUT_PATH.write_text(json.dumps(list(enriched.values()), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    if not API_KEY:
        raise EnvironmentError("OPENAI_API_KEY not set in .env file.")

    client = OpenAI(api_key=API_KEY)
    cocktails = json.loads(INPUT_PATH.read_text())
    enriched = load_progress()

    already_done = len(enriched)
    remaining = [c for c in cocktails if c["id"] not in enriched]

    print(f"Total: {len(cocktails)} | Already enriched: {already_done} | Remaining: {len(remaining)}")

    errors = []

    for idx, cocktail in enumerate(remaining, start=1):
        try:
            result = enrich_cocktail(client, cocktail)
            enriched[cocktail["id"]] = result

            flavor = ", ".join(result.get("flavor_profile", []))
            print(f"[{already_done + idx}/{len(cocktails)}] {cocktail['name']} → {flavor}")

            if idx % 10 == 0:
                save_progress(enriched)

            time.sleep(0.3)

        except json.JSONDecodeError as e:
            print(f"  [SKIP] {cocktail['name']} — bad JSON: {e}")
            errors.append(cocktail["name"])
        except Exception as e:
            print(f"  [ERROR] {cocktail['name']} — {e}")
            errors.append(cocktail["name"])
            time.sleep(2)

    save_progress(enriched)

    print(f"\nDone. {len(enriched)} cocktails saved to {OUTPUT_PATH}")
    if errors:
        print(f"Skipped {len(errors)}: {errors}")
