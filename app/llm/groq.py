from groq import Groq

from app.core.config import settings
from app.llm.base import LLMProvider


class GroqProvider(LLMProvider):

    def __init__(self):
        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not configured."
            )

        self.client = Groq(
            api_key=settings.groq_api_key
        )

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:

        completion = self.client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            reasoning_effort="medium",
        )

        return completion.choices[0].message.content or ""