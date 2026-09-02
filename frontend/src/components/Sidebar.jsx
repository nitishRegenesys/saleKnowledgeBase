function Sidebar({
  sessions,
  sessionId,
  loadingSessions,
  onNewChat,
  onSelectSession,
}) {
  return (
    <aside className="sidebar">

      {/* ======================================================
          Brand
          ====================================================== */}

      <div className="sidebar-brand">

        <div className="brand-mark">
          RA
        </div>

        <div>
          <div className="brand-name">
            RegAIcademy
          </div>

          <div className="brand-subtitle">
            Sales Knowledge Base
          </div>
        </div>

      </div>


      {/* ======================================================
          New Chat
          ====================================================== */}

      <button
        className="new-chat-button"
        onClick={onNewChat}
      >
        <span>+</span>
        New Chat
      </button>


      {/* ======================================================
          Conversations
          ====================================================== */}

      <div className="sidebar-section">

        <div className="sidebar-section-title">
          Conversations
        </div>


        {loadingSessions ? (

          <div className="empty-session">
            Loading conversations...
          </div>

        ) : sessions.length === 0 ? (

          <div className="empty-session">
            No conversations yet
          </div>

        ) : (

          <div className="sessions-list">

            {sessions.map((session) => (

              <button
                key={session.session_id}
                className={`session-item ${
                  session.session_id === sessionId
                    ? "session-item-active"
                    : ""
                }`}
                onClick={() =>
                  onSelectSession(
                    session.session_id
                  )
                }
              >

                <div className="session-icon">
                  💬
                </div>

                <div className="session-details">

                  <div className="session-title">
                    {session.title}
                  </div>

                  <div className="session-id">
                    {formatDate(
                      session.updated_at
                    )}
                  </div>

                </div>

              </button>

            ))}

          </div>

        )}

      </div>


      {/* ======================================================
          Footer
          ====================================================== */}

      <div className="sidebar-footer">

        <div className="status-dot" />

        Knowledge Base Online

      </div>

    </aside>
  );
}


function formatDate(value) {
  if (!value) {
    return "";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return date.toLocaleDateString(
    undefined,
    {
      month: "short",
      day: "numeric",
      year: "numeric",
    }
  );
}


export default Sidebar;