"""
EventPlannerAgent — LLM-powered
Handles event/party planning queries. Gathers requirements through conversation,
then generates a curated cocktail menu scaled to the number of guests,
plus a consolidated master shopping list.
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


EVENT_SYSTEM_PROMPT = """
You are an expert AI Mixologist specializing in event and party planning.
Your job is to help someone build the perfect cocktail menu for their event.

## YOUR GOAL
Gather the key details about the event through friendly conversation, then create a curated menu of 3–5 cocktails scaled to the number of guests.

## INFORMATION YOU NEED (gather over 1–2 turns if missing)
1. Number of guests
2. Type of event (birthday, wedding, corporate, casual gathering, etc.)
3. Venue / setting (indoor, outdoor, beach, rooftop, garden, etc.)
4. Drink preferences (alcoholic only, non-alcoholic only, or a mix)
5. Flavor mood (fruity, classic/elegant, tropical, refreshing, bold/strong)

## BEHAVIOR
- If key info is missing (especially guest count and preferences), ask for it warmly — max 2 questions at a time.
- CRITICAL: When intent is "event_gathering", the "message" field must be a short warm affirmation ONLY (1 sentence max). NEVER include the questions inside the message — they go in "clarifying_questions". Example: "Love it — just a couple of quick things to get you the perfect menu!" NOT "Can you tell me how many guests and what type of event?"
- Once you have enough info, generate the menu immediately. Don't ask unnecessary questions.
- Always include at least one non-alcoholic option unless the user explicitly said alcoholic only.
- Assign a role to each cocktail (e.g. "Welcome drink", "Signature cocktail", "Non-alcoholic option", "After-dinner drink").
- Scale quantities to the number of guests. If unknown, assume 20 guests.
- Be warm, enthusiastic, and make the user excited about their event.

## OUTPUT FORMAT — STRICT JSON
Always respond with valid JSON only. No markdown outside the JSON.

{
  "intent": "<one of: event_gathering | event_menu>",
  "message": "<warm conversational message — plain text, max 3 sentences>",
  "clarifying_questions": ["<question 1>", "<question 2>"],
  "event_menu": [
    {
      "role": "<e.g. Welcome drink | Signature cocktail | Non-alcoholic option>",
      "name": "<cocktail name>",
      "why": "<1 sentence why this fits the event>",
      "glass": "<glass type>",
      "strength": "<light | medium | strong | non-alcoholic>",
      "flavor_profile": ["<tag1>", "<tag2>"],
      "ingredients": [{"ingredient": "<name>", "measure": "<amount per serving>"}],
      "instructions": "<short preparation steps>",
      "thumbnail": "<image url or empty string>",
      "servings_note": "<e.g. 'For 30 guests: prepare 3 batches of 10'>"
    }
  ],
  "guest_count": <number or null>,
  "event_type": "<type of event or empty string>",
  "follow_up": "<one short question or tip to continue>",
  "cocktail_fact": "<fun fact relevant to events or cocktails>"
}

RULES:
- "intent" = "event_gathering" when you need more info (include clarifying_questions, empty event_menu)
- "intent" = "event_menu" when you have enough info to deliver the full menu (empty clarifying_questions)
- "event_menu" is always [] when intent is "event_gathering"
- "clarifying_questions" is always [] when intent is "event_menu"
- Scale ingredient quantities per serving — the frontend will display the scaling note
- Always include "cocktail_fact"
"""


class EventPlannerAgent:
    """
    Handles event/party planning queries end-to-end.
    Gathers requirements, then delivers a curated scaled menu.
    """

    def __init__(self):
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    def run(self, user_message: str, rag_context: list[dict], history: list[dict] = None) -> dict:
        print(f"  [EventPlannerAgent] Processing event query...")

        messages = [{"role": "system", "content": EVENT_SYSTEM_PROMPT}]

        # Inject RAG context
        if rag_context:
            context_block = "## AVAILABLE COCKTAILS FROM KNOWLEDGE BASE\nUse these to build the event menu:\n\n"
            for c in rag_context[:8]:  # More context for events
                context_block += f"**{c['name']}** ({c.get('strength','')}, {c.get('alcoholic','')})\n"
                context_block += f"  Flavor: {c.get('flavor_profile', [])}\n"
                context_block += f"  Best for: {c.get('best_for', [])}\n"
                context_block += f"  Ingredients: {', '.join(i['ingredient'] for i in c.get('ingredients', []))}\n"
                context_block += f"  Instructions: {c.get('instructions', '')}\n"
                context_block += f"  Thumbnail: {c.get('thumbnail', '')}\n\n"
            messages.append({"role": "system", "content": context_block})

        # Inject conversation history
        if history:
            messages += history

        messages.append({"role": "user", "content": user_message})

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)

        # Convert ingredient measures to ml
        for item in result.get("event_menu", []):
            if item.get("ingredients"):
                item["ingredients"] = [
                    {**ing, "measure": oz_to_ml(ing.get("measure", "") or "")}
                    for ing in item["ingredients"]
                ]

        print(f"  [EventPlannerAgent] Intent: {result.get('intent')} | Menu items: {len(result.get('event_menu', []))}")
        return result

    def build_master_shopping_list(self, event_menu: list[dict], guest_count: int) -> dict:
        """Generate a consolidated shopping list for all cocktails, scaled to guest count."""
        print(f"  [EventPlannerAgent] Building master shopping list for {guest_count} guests...")

        menu_text = ""
        for item in event_menu:
            name = item.get("name", "")
            role = item.get("role", "")
            ingredients = [
                f"{ing.get('measure', '')} {ing.get('ingredient', '')}".strip()
                for ing in item.get("ingredients", [])
            ]
            menu_text += f"- {role}: {name}\n  Ingredients per serving: {', '.join(ingredients)}\n"

        prompt = f"""You are an expert bartender creating a master shopping list for an event with {guest_count} guests.

Event cocktail menu:
{menu_text}

Create a CONSOLIDATED shopping list that:
1. Combines ALL ingredients across all cocktails
2. Scales quantities to {guest_count} guests (assume 2 servings per guest per cocktail)
3. Groups items by category
4. Notes which cocktail each item is for

Return ONLY valid JSON:
{{
  "event": "Event Cocktail Menu",
  "guest_count": {guest_count},
  "categories": [
    {{
      "name": "category name",
      "icon": "single emoji",
      "items": [
        {{
          "ingredient": "ingredient name",
          "measure": "total quantity needed (in ml or units)",
          "for_cocktails": ["cocktail name 1", "cocktail name 2"],
          "likely_have": false
        }}
      ]
    }}
  ],
  "tip": "one practical tip for preparing cocktails at a large event"
}}
Only include categories with items. No markdown."""

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=900,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        print(f"  [EventPlannerAgent] Master shopping list ready.")
        return result
