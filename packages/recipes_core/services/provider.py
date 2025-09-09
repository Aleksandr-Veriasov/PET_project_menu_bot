from __future__ import annotations

from packages.integrations.deepseek_api import DeepSeekClient

from .extract_recipe import LLMRecipeExtractor


def get_default_extractor() -> LLMRecipeExtractor:
    client = DeepSeekClient()  # берёт ключ/URL/модель из settings
    return LLMRecipeExtractor(chat_client=client)
