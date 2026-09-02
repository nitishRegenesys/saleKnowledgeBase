function Sidebar({
  onNewChat,
  sessionId,
}) {
  return (
    <aside className="sidebar">
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

      <button
        className="new-chat-button"
        onClick={onNewChat}
      >
        <span>+</span>
        New Chat
      </button>

      <div className="sidebar-section">
        <div className="sidebar-section-title">
          Current conversation
        </div>

        {sessionId ? (
          <div className="session-item">
            <div className="session-icon">
              💬
            </div>

            <div className="session-details">
              <div className="session-title">
                Current Chat
              </div>

              <div className="session-id">
                {sessionId.slice(0, 8)}...
              </div>
            </div>
          </div>
        ) : (
          <div className="empty-session">
            Start a new conversation
          </div>
        )}
      </div>

      <div className="sidebar-footer">
        <div className="status-dot" />
        Knowledge Base Online
      </div>
    </aside>
  );
}

export default Sidebar;