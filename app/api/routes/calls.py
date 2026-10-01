"""AI Calling proxy routes for the calling dashboard.

The voice-engine owns the telephony (Asterisk/ARI -> 3CX) but exposes two
things that make it unusable directly from a browser: no CORS headers, and an
`X-API-Key` requirement on the dial/hangup endpoints. This router keeps the
credential server-side and gives the frontend a same-origin, CORS-enabled
surface:

    POST /api/v1/calls/outbound             -> engine /api/threecx/calls/outbound
    GET  /api/v1/calls/status               -> engine /api/threecx/status
    GET  /api/v1/calls/active               -> engine /api/threecx/calls
    POST /api/v1/calls/{channel_id}/hangup  -> engine /api/threecx/calls/{id}/hangup
    GET  /api/v1/calls/contacts             -> mock contact list (see TODO below)

An unreachable engine is reported as an empty-but-successful status/active
payload so the dashboard can show an "engine offline" banner instead of
throwing, while a dial attempt surfaces a real 5xx with the engine's own
explanation.
"""
import httpx

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings


router = APIRouter(
    prefix="/api/v1/calls",
    tags=["Calls"],
)


ENGINE_OFFLINE = (
    "Calling engine is unavailable. "
    "Start the voice-engine service and retry."
)

ACTIVE_CALLS_UNREACHABLE = {
    "engine_reachable": False,
    "active_call_count": 0,
    "active_calls": [],
}

STATUS_UNREACHABLE = {
    "engine_reachable": False,
    "enabled": False,
    "configured": False,
    "connected": False,
    "active_call_count": 0,
    "active_calls": [],
}


class OutboundCallRequest(BaseModel):
    phone: str = Field(..., min_length=3, max_length=24)
    caller_id: str | None = None
    customer_id: str | None = None


def _engine_url(path: str) -> str:
    return f"{settings.voice_engine_url.rstrip('/')}{path}"


def _engine_headers() -> dict[str, str]:
    return {"X-API-Key": settings.calls_api_key}


def _engine_detail(response) -> str:
    """Prefer the engine's own explanation over a generic message."""
    try:
        detail = response.json().get("detail")
    except Exception:
        detail = None

    if isinstance(detail, str) and detail.strip():
        return detail

    return f"Calling engine returned status {response.status_code}."


# TODO: replace with the real customer/user source (CRM / app DB) once the
# users API is available. The frontend keeps a small offline fallback list.
MOCK_CALL_CONTACTS = [
    {
        "id": "c-1001",
        "name": "Dheer",
        "phone": "0730825043",
        "company": "Regenesys",
        "role": "AI Lead",
        "status": "warm",
    }
]


@router.get("/contacts")
def get_contacts() -> dict:
    """Users/contacts the dashboard can dial (mock until the user API lands)."""
    return {"contacts": MOCK_CALL_CONTACTS}


@router.get("/status")
async def calling_status() -> dict:
    """Engine reachability + lifecycle flags, safe to poll while offline."""
    try:

        async with httpx.AsyncClient(
            timeout=5.0,
        ) as client:

            response = await client.get(
                _engine_url("/api/threecx/status"),
            )

    except httpx.HTTPError:
        return dict(STATUS_UNREACHABLE)

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=_engine_detail(response),
        )

    return {
        **response.json(),
        "engine_reachable": True,
    }


@router.get("/active")
async def list_active_calls() -> dict:
    """Active calls with live state, duration, turns and transcript."""
    try:

        async with httpx.AsyncClient(
            timeout=5.0,
        ) as client:

            response = await client.get(
                _engine_url("/api/threecx/calls"),
            )

    except httpx.HTTPError:
        return dict(ACTIVE_CALLS_UNREACHABLE)

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=_engine_detail(response),
        )

    return {
        **response.json(),
        "engine_reachable": True,
    }


@router.post("/outbound")
async def originate_outbound_call(
    request: OutboundCallRequest,
) -> dict:
    """Ask the engine to dial a number through the 3CX/Asterisk gateway."""
    payload = {"phone": request.phone}

    if request.caller_id:
        payload["caller_id"] = request.caller_id

    if request.customer_id:
        payload["customer_id"] = request.customer_id

    try:

        async with httpx.AsyncClient(
            timeout=30.0,
        ) as client:

            response = await client.post(
                _engine_url("/api/threecx/calls/outbound"),
                json=payload,
                headers=_engine_headers(),
            )

    except httpx.HTTPError as exc:
        print("VOICE ENGINE OUTBOUND ERROR:", repr(exc))

        raise HTTPException(
            status_code=503,
            detail=ENGINE_OFFLINE,
        ) from exc

    if response.status_code != 200:
        # 4xx from the engine is a client problem (bad number, bad key)
        status_code = (
            response.status_code
            if 400 <= response.status_code < 500
            else 502
        )

        raise HTTPException(
            status_code=status_code,
            detail=_engine_detail(response),
        )

    return response.json()


@router.post("/{channel_id}/hangup")
async def hangup_call(channel_id: str) -> dict:
    """Terminate an active call by ARI channel id."""
    try:

        async with httpx.AsyncClient(
            timeout=15.0,
        ) as client:

            response = await client.post(
                _engine_url(
                    f"/api/threecx/calls/{channel_id}/hangup",
                ),
                headers=_engine_headers(),
            )

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=ENGINE_OFFLINE,
        ) from exc

    if response.status_code != 200:
        status_code = (
            response.status_code
            if 400 <= response.status_code < 500
            else 502
        )

        raise HTTPException(
            status_code=status_code,
            detail=_engine_detail(response),
        )

    return response.json()



