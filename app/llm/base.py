from abc import ABC, abstractmethod


class LLMProvider(ABC):

    @abstractmethod
    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        raise NotImplementedError

    async def stream(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ):
        """Stream response text as an async generator of string deltas.

        Default implementation falls back to the one-shot ``generate``.
        Providers may override it for true token streaming.
        """
        answer = self.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        if not answer:
            return

        # Emit in small deltas so downstream sentence chunking still works.
        for i in range(0, len(answer), 4):
            yield answer[i : i + 4]