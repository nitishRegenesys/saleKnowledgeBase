/**
 * Transcript of the live call, straight from the engine session
 * (`/api/threecx/calls` -> conversation: [{role, content}]).
 *
 * Ended calls keep their transcript in the local call log; a server-side
 * conversation-history API is still to come, which is what the empty state
 * below is standing in for.
 */
function ConversationPanel({ conversation, hasCall }) {
  if (!hasCall) {
    return (
      <div className="conversation-panel conversation-empty">
        <p>
          No call transcript yet.
        </p>
        <p className="conversation-hint">
          The transcript appears here while a call is live. Stored
          conversation history will be added once that API is
          available.
        </p>
      </div>
    );
  }

  if (conversation.length === 0) {
    return (
      <div className="conversation-panel conversation-empty">
        <p>
          Waiting for the first exchange...
        </p>
        <p className="conversation-hint">
          The AI greets the caller, then every question and answer shows
          up here as it happens.
        </p>
      </div>
    );
  }

  return (
    <div className="conversation-panel">

      {conversation.map((entry, index) => (
        <div
          key={`${entry.role}-${index}`}
          className={`conversation-line conversation-line-${
            entry.role === "user" ? "user" : "assistant"
          }`}
        >

          <div className="conversation-role">
            {entry.role === "user"
              ? "Caller"
              : "AI agent"}
          </div>

          <div className="conversation-text">
            {entry.content}
          </div>

        </div>
      ))}

    </div>
  );
}

export default ConversationPanel;
