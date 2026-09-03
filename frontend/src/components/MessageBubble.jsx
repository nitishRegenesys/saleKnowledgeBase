function MessageBubble({
  role,
  content,
  onSpeak,
  speaking = false,
}) {
  const isUser = role === "user";

  return (
    <div
      className={`message-row ${
        isUser ? "message-row-user" : "message-row-assistant"
      }`}
    >
      <div
        className={`message-bubble ${
          isUser
            ? "message-bubble-user"
            : "message-bubble-assistant"
        }`}
      >
        {!isUser && (
          <div className="assistant-label">
            RegAIcademy AI

            {typeof onSpeak === "function" && (
              <button
                type="button"
                className={`speak-button ${
                  speaking ? "speak-button-stop" : ""
                }`}
                onClick={() => onSpeak(content)}
                title={
                  speaking
                    ? "Stop"
                    : "Play answer aloud"
                }
              >
                {speaking ? "⏹" : "🔊"}
              </button>
            )}
          </div>
        )}

        <div className="message-content">
          {content}
        </div>
      </div>
    </div>
  );
}

export default MessageBubble;