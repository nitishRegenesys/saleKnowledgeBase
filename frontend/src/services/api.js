const API_BASE_URL = "http://localhost:8000";

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

  if (!response.ok) {
    let errorMessage = "Unable to process your message.";

    try {
      const errorData = await response.json();

      if (errorData?.detail) {
        errorMessage = errorData.detail;
      }
    } catch {
      // Keep default error message
    }

    throw new Error(errorMessage);
  }

  return response.json();
}