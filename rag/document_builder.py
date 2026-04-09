"""
Step 2a — Document Builder
Converts enriched cocktail JSON into natural language documents for embedding.
"""


def build_document(cocktail: dict) -> str:
    name = cocktail.get("name", "")
    category = cocktail.get("category", "")
    alcoholic = cocktail.get("alcoholic", "")
    glass = cocktail.get("glass", "")
    instructions = cocktail.get("instructions", "")

    ingredients = cocktail.get("ingredients", [])
    ingredients_str = ", ".join(
        f"{i['measure']} {i['ingredient']}".strip() if i.get("measure") else i["ingredient"]
        for i in ingredients
    )

    flavor_profile = ", ".join(cocktail.get("flavor_profile", []))
    mood = ", ".join(cocktail.get("mood", []))
    strength = cocktail.get("strength", "")
    taste_tags = ", ".join(cocktail.get("taste_tags", []))
    best_for = ", ".join(cocktail.get("best_for", []))
    tags = ", ".join(cocktail.get("tags", []))

    doc = f"{name} is a {strength} {alcoholic.lower()} {category.lower()}"
    if glass:
        doc += f" served in a {glass.lower()}"
    doc += f". Made with {ingredients_str}."
    if flavor_profile:
        doc += f" It has a {flavor_profile} flavor profile."
    if taste_tags:
        doc += f" It tastes {taste_tags}."
    if mood:
        doc += f" Great for {mood}."
    if best_for:
        doc += f" Best for {best_for}."
    if tags:
        doc += f" Tags: {tags}."
    if instructions:
        doc += f" Preparation: {instructions}"

    return doc
