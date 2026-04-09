"""
Step 1 — Data Pipeline
Fetches all cocktails from TheCocktailDB (free tier) by iterating a-z,
cleans the data, and saves to data/cocktails.json
"""

import requests
import json
import time
import string
from pathlib import Path

BASE_URL = "https://www.thecocktaildb.com/api/json/v1/1/search.php"
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "cocktails.json"


def fetch_by_letter(letter: str) -> list[dict]:
    response = requests.get(BASE_URL, params={"f": letter}, timeout=10)
    response.raise_for_status()
    data = response.json()
    return data.get("drinks") or []


def clean_cocktail(raw: dict) -> dict:
    """Extract and flatten relevant fields from raw API response."""
    ingredients = []
    for i in range(1, 16):
        ingredient = (raw.get(f"strIngredient{i}") or "").strip()
        measure = (raw.get(f"strMeasure{i}") or "").strip()
        if ingredient:
            ingredients.append({
                "ingredient": ingredient,
                "measure": measure if measure else None
            })

    return {
        "id": raw.get("idDrink"),
        "name": raw.get("strDrink"),
        "category": raw.get("strCategory"),
        "alcoholic": raw.get("strAlcoholic"),
        "glass": raw.get("strGlass"),
        "instructions": raw.get("strInstructions"),
        "thumbnail": raw.get("strDrinkThumb"),
        "tags": [t.strip() for t in raw.get("strTags", "").split(",") if t.strip()] if raw.get("strTags") else [],
        "ingredients": ingredients,
    }


def fetch_all_cocktails() -> list[dict]:
    all_cocktails = []
    seen_ids = set()

    for letter in string.ascii_lowercase:
        print(f"Fetching cocktails starting with '{letter}'...")
        raw_list = fetch_by_letter(letter)

        for raw in raw_list:
            cid = raw.get("idDrink")
            if cid not in seen_ids:
                seen_ids.add(cid)
                all_cocktails.append(clean_cocktail(raw))

        time.sleep(0.2)  # be polite to the free API

    return all_cocktails


if __name__ == "__main__":
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    cocktails = fetch_all_cocktails()
    OUTPUT_PATH.write_text(json.dumps(cocktails, indent=2, ensure_ascii=False))
    print(f"\nDone. {len(cocktails)} cocktails saved to {OUTPUT_PATH}")
