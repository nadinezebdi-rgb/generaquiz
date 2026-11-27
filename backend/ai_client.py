"""Appels IA texte (Claude via la clé universelle Emergent) pour les générations nocturnes."""
from __future__ import annotations

import os
import uuid

from emergentintegrations.llm.chat import LlmChat, UserMessage

AI_PROVIDER, AI_MODEL = "anthropic", "claude-sonnet-5-5"
AI_LABEL = f"{AI_PROVIDER}/{AI_MODEL}"
SYSTEM = ("Tu es un auteur de jeux et de quiz en français pour des familles et des personnes âgées. "
          "Tu respectes exactement le format demandé et tu réponds uniquement avec le JSON demandé, sans texte autour.")


def ai_available() -> bool:
    return bool(os.environ.get("EMERGENT_LLM_KEY"))


async def ai_complete(prompt: str, *, max_tokens: int = 4000, tag: str = "gen") -> str:
    """Génération non diffusée en direct (tâches de fond) : une session neuve par appel."""
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"{tag}-{uuid.uuid4().hex}",
                   system_message=SYSTEM).with_model(AI_PROVIDER, AI_MODEL).with_params(max_tokens=max_tokens)
    return await chat.send_message(UserMessage(text=prompt))
