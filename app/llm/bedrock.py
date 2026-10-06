import asyncio
import os

import boto3
from botocore.config import Config

from app.core.config import settings
from app.llm.base import LLMProvider


def _message_text(message: dict) -> str:
    """Concatenate the text blocks of a Converse response message."""

    parts = []

    for block in message.get("content", []):
        text = block.get("text")

        if text:
            parts.append(text)

    return "".join(parts)


class BedrockProvider(LLMProvider):
    """LLM provider backed by Amazon Bedrock Runtime (Converse APIs).

    Authenticates with an Amazon Bedrock API key (bearer token, the
    base64 ``ABSK...`` string) supplied through ``AWS_API_KEY``.
    """

    def __init__(self):

        if not settings.aws_api_key:
            raise RuntimeError(
                "AWS_API_KEY is not configured."
            )

        # Amazon Bedrock API keys are long-lived bearer tokens consumed by
        # boto3 via the AWS_BEARER_TOKEN_BEDROCK environment variable.
        os.environ["AWS_BEARER_TOKEN_BEDROCK"] = settings.aws_api_key

        self.model_id = settings.llm_model

        self.client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_bedrock_region,
            config=Config(
                connect_timeout=10,
                read_timeout=180,
                retries={
                    "max_attempts": 3,
                    "mode": "adaptive",
                },
            ),
        )

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:

        response = self.client.converse(
            modelId=self.model_id,
            system=[
                {
                    "text": system_prompt,
                },
            ],
            messages=[
                {
                    "role": "user",
                    "content": [{"text": user_prompt}],
                },
            ],
            inferenceConfig={
                "maxTokens": 4096,
                "temperature": 0.2,
            },
        )

        return _message_text(
            response.get("output", {}).get("message", {})
        )

    async def stream(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ):

        response = await asyncio.to_thread(
            self.client.converse_stream,
            modelId=self.model_id,
            system=[
                {
                    "text": system_prompt,
                },
            ],
            messages=[
                {
                    "role": "user",
                    "content": [{"text": user_prompt}],
                },
            ],
            inferenceConfig={
                "maxTokens": 4096,
                "temperature": 0.2,
            },
        )

        events = iter(response.get("stream", []))

        while True:
            # boto3's event stream is synchronous; pull each event in a
            # worker thread so the FastAPI event loop is never blocked.
            event = await asyncio.to_thread(next, events, None)

            if event is None:
                break

            delta = event.get("contentBlockDelta", {}).get(
                "delta", {}
            )
            text = delta.get("text")

            if text:
                yield text