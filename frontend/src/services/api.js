const API_BASE_URL = "http://localhost:8000";


async function handleResponse(response) {
  if (!response.ok) {
    let errorMessage = "Something went wrong.";

    try {
      const errorData = await response.json();

      if (errorData?.detail) {
        errorMessage = errorData.detail;
      }
    } catch {
      // Use default error
    }

    throw new Error(errorMessage);
  }

  return response.json();
}


export async function sendChatMessage({
  sessionId = null,
  message,
  limit = 5,
  category = null,
  subcategory = null,
}) {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/rag/chat`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        session_id: sessionId,
        message,
        limit,
        category,
        subcategory,
      }),
    }
  );

  return handleResponse(response);
}


export async function getSessions() {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/rag/sessions`
  );

  const data = await handleResponse(response);

  return data.sessions || [];
}


export async function getConversation(
  sessionId
) {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/rag/sessions/${sessionId}`
  );

  return handleResponse(response);
}


export async function transcribeAudio(
  base64Audio
) {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/voice/stt`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        data: base64Audio,
        encoding: "base64",
      }),
    }
  );

  return handleResponse(response);
}


export async function synthesizeSpeech(
  text
) {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/voice/tts`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ text }),
    }
  );

  if (!response.ok) {
    let errorMessage = "Something went wrong.";

    try {
      const errorData = await response.json();

      if (errorData?.detail) {
        errorMessage = errorData.detail;
      }
    } catch {
      // Use default error
    }

    throw new Error(errorMessage);
  }

  const blob = await response.blob();

  return URL.createObjectURL(blob);
}


export function getVoiceSocketUrl() {
  const url = new URL(API_BASE_URL);

  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/api/v1/voice/ws";

  return url.toString();
}


export async function getVoiceHealth() {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/voice/health`
    );

    if (!response.ok) {
      return false;
    }

    const data = await response.json();

    return Boolean(data?.voice_available);
  } catch {
    // Backend or voice-engine unreachable
    return false;
  }
}


export async function streamChatMessage({
  sessionId = null,
  message,
  limit = 5,
  category = null,
  subcategory = null,
  onDelta,
  onDone,
}) {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/rag/chat/stream`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        session_id: sessionId,
        message,
        limit,
        category,
        subcategory,
      }),
    }
  );

  if (!response.ok) {
    let errorMessage = "Something went wrong.";

    try {
      const errorData = await response.json();

      if (errorData?.detail) {
        errorMessage = errorData.detail;
      }
    } catch {
      // Use default error
    }

    throw new Error(errorMessage);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  function handleData(raw) {
    if (!raw) {
      return;
    }

    let data;

    try {
      data = JSON.parse(raw);
    } catch {
      return;
    }

    if (!data || typeof data !== "object") {
      return;
    }

    if (data.type === "delta" && typeof data.text === "string") {
      onDelta?.(data.text);
    } else if (data.type === "done") {
      onDone?.(data);
    } else if (data.type === "error") {
      throw new Error(
        data.detail || "Something went wrong."
      );
    }
  }

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { done, value } = await reader.read();

    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const trimmed = line.trim();

      if (!trimmed.startsWith("data:")) {
        continue;
      }

      handleData(trimmed.slice(5).trim());
    }
  }

  const tail = buffer.trim();

  if (tail.startsWith("data:")) {
    handleData(tail.slice(5).trim());
  }
}