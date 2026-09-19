from __future__ import annotations

from functools import lru_cache

from langchain_groq import ChatGroq

from app.core.settings import settings


@lru_cache(maxsize=1)
def get_chat_model() -> ChatGroq:
    kwargs = dict(
        model=settings.llm_model,
        api_key=settings.llm_api_key or None,
        temperature=0.2,
        max_tokens=800,
        timeout=60,
        max_retries=1,
    )
    if settings.llm_base_url and "groq.com" not in settings.llm_base_url:
        kwargs["base_url"] = settings.llm_base_url
    return ChatGroq(**kwargs)
