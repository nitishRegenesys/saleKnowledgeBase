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