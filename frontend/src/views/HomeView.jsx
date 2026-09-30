import { useEffect, useState } from "react";

import { getCallingStatus } from "../services/callingApi";
import { getVoiceHealth } from "../services/api";

/**
 * Home route: choose between the chat assistant and the AI calling dashboard.
 */
function HomeView({ onNavigate }) {
  const [chatReady, setChatReady] = useState(null);
  const [callingReady, setCallingReady] = useState(null);

  useEffect(() => {
    let cancelled = false;

    getVoiceHealth().then((available) => {
      if (!cancelled) {
        setChatReady(available);
      }
    });

    getCallingStatus().then((status) => {
      if (!cancelled) {
        setCallingReady(
          Boolean(status?.engine_reachable && status?.connected)
        );
      }
    });

    return () => {
      cancelled = true;
    };
  }, []);

  function statusLabel(ready, onlineText, offlineText) {
    if (ready === null) {
      return "Checking...";
    }

    return ready ? onlineText : offlineText;
  }

  return (
    <div className="home-shell">

      <header className="home-header">

        <div className="brand-mark">
          RA
        </div>

        <div>

          <div className="brand-name">
            Regenesys Sales Knowledge Base
          </div>

          <div className="home-subtitle">
            Pick how you want to work with the assistant today.
          </div>

        </div>

      </header>

      <main className="home-grid">

        {/* ---------------- Chat ---------------- */}

        <button
          type="button"
          className="home-card home-card-chat"
          onClick={() => onNavigate("/chat")}
        >

          <div className="home-card-icon">
            💬
          </div>

          <h2>
            Chat
          </h2>

          <p>
            Ask the knowledge base about programmes, fees, eligibility and
            duration, with typed and spoken questions.
          </p>

          <div className="home-card-meta">
            <span
              className={`home-dot ${
                chatReady === false ? "home-dot-off" : ""
              }`}
            />
            {statusLabel(
              chatReady,
              "Knowledge base online",
              "Backend offline"
            )}
          </div>

          <span className="home-card-cta">
            Open chat →
          </span>

        </button>


        {/* ---------------- AI calling ---------------- */}

        <button
          type="button"
          className="home-card home-card-calling"
          onClick={() => onNavigate("/calls")}
        >

          <div className="home-card-icon">
            📞
          </div>

          <h2>
            AI Calling
          </h2>

          <p>
            Dial a user from the dashboard and let the AI agent hold the
            conversation, with live status and a call log.
          </p>

          <div className="home-card-meta">
            <span
              className={`home-dot ${
                callingReady === false ? "home-dot-off" : ""
              }`}
            />
            {statusLabel(
              callingReady,
              "3CX gateway connected",
              "Calling engine not connected"
            )}
          </div>

          <span className="home-card-cta">
            Open dashboard →
          </span>

        </button>

      </main>

      <footer className="home-footer">
        Chat runs on the sales knowledge base. Calls are placed through the
        voice-engine and answered by the same AI assistant.
      </footer>

    </div>
  );
}

export default HomeView;
