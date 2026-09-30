/**
 * Calling dashboard API surface. Everything goes through the FastAPI backend
 * (`/api/v1/calls/*`), which forwards to the voice-engine and attaches the
 * X-API-Key server-side — the browser never sees the credential and no CORS
 * exemptions are needed.
 */
import { API_BASE_URL, handleResponse } from "./api";

const OFFLINE_STATUS = {
  engine_reachable: false,
  enabled: false,
  configured: false,
  connected: false,
  active_call_count: 0,
  active_calls: [],
};

export async function getCallContacts() {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/calls/contacts`,
  );

  const data = await handleResponse(response);

  return data.contacts || [];
}

/**
 * Engine health. Never throws: the dashboard renders an "engine offline"
 * banner from this instead of an error toast on every poll.
 */
export async function getCallingStatus() {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/calls/status`,
    );

    if (!response.ok) {
      return { ...OFFLINE_STATUS };
    }

    return await response.json();
  } catch {
    return { ...OFFLINE_STATUS };
  }
}

export async function getActiveCalls() {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/calls/active`,
    );

    if (!response.ok) {
      return { ...OFFLINE_STATUS };
    }

    return await response.json();
  } catch {
    return { ...OFFLINE_STATUS };
  }
}

export async function startOutboundCall({
  phone,
  callerId = null,
  customerId = null,
}) {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/calls/outbound`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        phone,
        caller_id: callerId,
        customer_id: customerId,
      }),
    }
  );

  return handleResponse(response);
}

export async function hangupCall(channelId) {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/calls/${encodeURIComponent(channelId)}/hangup`,
    {
      method: "POST",
    }
  );

  return handleResponse(response);
}
