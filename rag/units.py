"""
Unit conversion utility — converts oz-based cocktail measures to ml.
1 oz = 30 ml | 1 tsp = 5 ml | 1 tbsp = 15 ml
"""

import re
from fractions import Fraction


def oz_to_ml(measure: str) -> str:
    """
    Converts a cocktail measure string to ml where applicable.
    Leaves non-convertible values (dash, splash, pinch, etc.) unchanged.

    Examples:
        "1 oz"      → "30 ml"
        "1/2 oz"    → "15 ml"
        "1 1/2 oz"  → "45 ml"
        "2 oz"      → "60 ml"
        "1 tsp"     → "5 ml"
        "1 tbsp"    → "15 ml"
        "1 dash"    → "1 dash"   (unchanged)
        ""          → ""
    """
    if not measure:
        return measure

    m = measure.strip()
    lower = m.lower()

    # Extract numeric part — handles integers, decimals, fractions, mixed numbers
    # e.g. "1 1/2", "3/4", "1.5", "2"
    num_pattern = r'(\d+\s+\d+/\d+|\d+/\d+|\d+\.?\d*)'
    num_match = re.search(num_pattern, m)

    def parse_number(s):
        s = s.strip()
        if ' ' in s:
            # mixed number: "1 1/2"
            parts = s.split()
            return int(parts[0]) + float(Fraction(parts[1]))
        elif '/' in s:
            return float(Fraction(s))
        else:
            return float(s)

    if 'oz' in lower and num_match:
        amount = parse_number(num_match.group(1))
        ml = round(amount * 30)
        return f"{ml} ml"

    if ('tsp' in lower or 'teaspoon' in lower) and num_match:
        amount = parse_number(num_match.group(1))
        ml = round(amount * 5)
        return f"{ml} ml"

    if ('tbsp' in lower or 'tablespoon' in lower) and num_match:
        amount = parse_number(num_match.group(1))
        ml = round(amount * 15)
        return f"{ml} ml"

    # cl → ml
    if 'cl' in lower and num_match:
        amount = parse_number(num_match.group(1))
        ml = round(amount * 10)
        return f"{ml} ml"

    # Unchanged: dash, splash, pinch, drop, slice, etc.
    return m


def convert_ingredients(ingredients: list[dict]) -> list[dict]:
    """Converts measure field of each ingredient dict to ml."""
    converted = []
    for ing in ingredients:
        converted.append({
            **ing,
            "measure": oz_to_ml(ing.get("measure", "") or "")
        })
    return converted
