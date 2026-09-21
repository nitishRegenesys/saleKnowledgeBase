import asyncio

from fastapi import APIRouter, HTTPException, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

import httpx
import websockets

from app.core.config import settings


router = APIRouter(
    prefix="/api/v1/voice",
    tags=["Voice"],
)


MAX_STT_PAYLOAD = 2 * 1024 * 1024  # 2 MB base64 cap


class STTRequest(BaseModel):
    data: str = Field(..., min_length=1)
    encoding: str = "base64"


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1)


class STTResponse(BaseModel):
    text: str


class HealthResponse(BaseModel):
    voice_available: bool


def _voice_url(path: str) -> str:
    return f"{settings.voice_engine_url.rstrip('/')}{path}"


# ============================================================
# HEALTH - reachability probe for the voice-engine gateway.
# Pings the engine's root route (cheap, no STT/TTS usage) so
# the UI can hide the voice controls when it is not running.
# ============================================================


@router.get(
    "/health",
    response_model=HealthResponse,
)
async def voice_health(
) -> HealthResponse:

    try:

        async with httpx.AsyncClient(
            timeout=2.0,
        ) as client:

            response = await client.get(
                _voice_url("/"),
            )

        available = (
            response.status_code == 200
        )

    except httpx.HTTPError:

        available = False

    return HealthResponse(
        voice_available=available,
    )


# ============================================================
# STT — forward recorded audio to the voice-engine for
# speech-to-text and return the transcript.
# ============================================================


@router.post(
    "/stt",
    response_model=STTResponse,
)
async def speech_to_text(
    request: STTRequest,
) -> STTResponse:

    if request.encoding not in ("base64", "audio", "text"):
        raise HTTPException(
            status_code=422,
            detail="Unsupported audio encoding.",
        )

    if len(request.data) > MAX_STT_PAYLOAD:
        raise HTTPException(
            status_code=413,
            detail="Audio payload is too large.",
        )

    try:

        async with httpx.AsyncClient(
            timeout=60.0,
        ) as client:

            response = await client.post(
                _voice_url("/stt"),
                json={
                    "data": request.data,
                    "encoding": request.encoding,
                },
            )

    except httpx.HTTPError as exc:

        print(
            "VOICE ENGINE STT ERROR:",
            repr(exc),
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Speech-to-text service "
                "is unavailable."
            ),
        ) from exc

    if response.status_code != 200:

        print(
            "VOICE ENGINE STT RESPONSE:",
            response.status_code,
            response.text[:500],
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Speech-to-text service "
                "returned an error."
            ),
        )

    return STTResponse(
        text=response.json().get(
            "text",
            "",
        ),
    )


# ============================================================
# TTS — forward answer text to the voice-engine and stream
# the synthesized audio back to the browser.
# ============================================================


@router.post("/tts")
async def text_to_speech(
    request: TTSRequest,
) -> Response:

    try:

        async with httpx.AsyncClient(
            timeout=120.0,
        ) as client:

            response = await client.post(
                _voice_url("/tts"),
                json={"text": request.text},
            )

    except httpx.HTTPError as exc:

        print(
            "VOICE ENGINE TTS ERROR:",
            repr(exc),
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Text-to-speech service "
                "is unavailable."
            ),
        ) from exc

    if response.status_code != 200:

        print(
            "VOICE ENGINE TTS RESPONSE:",
            response.status_code,
            response.text[:500],
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Text-to-speech service "
                "returned an error."
            ),
        )

    media_type = response.headers.get(
        "content-type",
        "audio/mpeg",
    )

    return Response(
        content=response.content,
        media_type=media_type,
    )


# ============================================================
# WS — realtime relay to the voice-engine gateway
#
# The browser talks to `ws://localhost:8000/api/v1/voice/ws`;
# this endpoint transparently forwards every frame to the
# voice-engine `ws://.../ws?auto_llm=0` and streams every event
# (transcript.partial, transcript.final, audio.chunk, speak.done)
# straight back. CORS does not apply to WebSockets, but keeping a
# single-origin gateway also preserves the existing API surface.
# ============================================================


@router.websocket("/ws")
async def voice_websocket(
    ws: WebSocket,
) -> None:

    await ws.accept()

    base = settings.voice_engine_url.rstrip("/")

    upstream_url = (
        base.replace(
            "http://",
            "ws://",
        ).replace(
            "https://",
            "wss://",
        )
        + "/ws?auto_llm=0"
    )

    try:

        async with websockets.connect(
            upstream_url,
            max_size=None,
        ) as upstream:

            async def relay_upstream() -> None:
                """voice-engine -> browser."""
                try:
                    async for message in upstream:
                        if isinstance(message, bytes):
                            await ws.send_bytes(message)
                        else:
                            await ws.send_text(message)
                except Exception:
                    pass

            relay_task = asyncio.create_task(
                relay_upstream()
            )

            try:

                # browser -> voice-engine
                while True:

                    message = await ws.receive()

                    msg_type = message.get("type")

                    if msg_type == "websocket.disconnect":
                        break

                    if msg_type == "websocket.receive":

                        text = message.get("text")

                        if text is not None:
                            await upstream.send(text)
                            continue

                        data = message.get("bytes")

                        if data is not None:
                            await upstream.send(data)

            except WebSocketDisconnect:
                pass

            finally:

                relay_task.cancel()

                try:
                    await relay_task
                except asyncio.CancelledError:
                    pass

    except Exception as exc:

        print(
            "VOICE WS RELAY ERROR:",
            repr(exc),
        )

        try:

            await ws.close(
                code=1011,
                reason="Voice engine unavailable",
            )

        except Exception:
            pass