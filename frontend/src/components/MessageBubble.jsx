function MessageBubble({ role, content }) {
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