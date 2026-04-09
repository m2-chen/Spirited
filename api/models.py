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


class ChatResponse(BaseModel):
    intent: str
    message: str
    clarifying_questions: list[str] = []
    recommendations: list[Recommendation] = []
    follow_up: Optional[str] = None
    cocktail_fact: Optional[str] = None
    shopping_list: Optional[dict] = None
