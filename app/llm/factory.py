from app.core.config import settings
from app.llm.base import LLMProvider
from app.llm.bedrock import BedrockProvider
from app.llm.groq import GroqProvider


def get_llm() -> LLMProvider:

    provider = settings.llm_provider.lower()

    if provider == "bedrock":
        return BedrockProvider()

    if provider == "groq":
        return GroqProvider()

    raise ValueError(
        f"Unsupported LLM provider: {provider}"
    )