"""
Request and response models for the Mixologist API.
"""

from pydantic import BaseModel
from typing import Optional


class ChatMessage(BaseModel):
    role: str   # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    mode: str = "guest"  # "guest" or "bartender"


class Ingredient(BaseModel):
    ingredient: str
    measure: Optional[str] = None


class Recommendation(BaseModel):
    name: str
    why: str
    glass: Optional[str] = None
    strength: Optional[str] = None
    flavor_profile: Optional[list[str]] = []
    ingredients: Optional[list[Ingredient]] = []
    instructions: Optional[str] = None
    thumbnail: Optional[str] = None
    pro_notes: Optional[dict] = None


class EventMenuItem(BaseModel):
    role: Optional[str] = None
    name: str
    why: Optional[str] = None
    glass: Optional[str] = None
    strength: Optional[str] = None
    flavor_profile: Optional[list[str]] = []
    ingredients: Optional[list[Ingredient]] = []
    instructions: Optional[str] = None
    thumbnail: Optional[str] = None
    servings_note: Optional[str] = None


class EventShoppingRequest(BaseModel):
    event_menu: list[dict]
    guest_count: Optional[int] = 20


class ChatResponse(BaseModel):
    intent: str
    message: str
    clarifying_questions: list[str] = []
    recommendations: list[Recommendation] = []
    event_menu: Optional[list[EventMenuItem]] = None
    guest_count: Optional[int] = None
    event_type: Optional[str] = None
    follow_up: Optional[str] = None
    cocktail_fact: Optional[str] = None
    shopping_list: Optional[dict] = None
