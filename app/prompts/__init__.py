"""Versioned marketing prompt knowledge."""

from app.prompts.models import PromptPack
from app.prompts.repository import PromptPackRepository

__all__ = [
    "PromptPack",
    "PromptPackRepository",
]
