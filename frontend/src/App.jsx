import { useEffect, useState } from "react";

import ChatInput from "./components/ChatInput";
import MessageBubble from "./components/MessageBubble";
import Sidebar from "./components/Sidebar";
import SourceList from "./components/SourceList";

import {
  getSessions,
  sendChatMessage,
  getConversation,
} from "./services/api";


function App() {

  // ==========================================================
  // State
  // ==========================================================

  const [sessionId, setSessionId] =
    useState(null);

  const [messages, setMessages] =
    useState([]);

  const [sessions, setSessions] =
    useState([]);

  const [loading, setLoading] =
    useState(false);

  const [loadingSessions, setLoadingSessions] =
    useState(true);

  const [error, setError] =
    useState(null);


  // ==========================================================
  // Load sessions
  // ==========================================================

  async function loadSessions() {

    setLoadingSessions(true);

    try {

      const loadedSessions =
        await getSessions();

      setSessions(
        loadedSessions
      );

    } catch (err) {

      console.error(
        "Unable to load sessions:",
        err
      );

    } finally {

      setLoadingSessions(false);

    }
  }


  useEffect(() => {
    loadSessions();
  }, []);


  // ==========================================================
  // Send message
  // ==========================================================

  async function handleSend(message) {

    setError(null);

    const userMessage = {
      role: "user",
      content: message,
    };

    setMessages((current) => [
      ...current,
      userMessage,
    ]);

    setLoading(true);

    try {

      const result =
        await sendChatMessage({
          sessionId,
          message,
          limit: 5,
        });


      // ------------------------------------------------------
      // Store session ID
      // ------------------------------------------------------

      setSessionId(
        result.session_id
      );


      // ------------------------------------------------------
      // Add assistant response
      // ------------------------------------------------------

      const assistantMessage = {
        role: "assistant",
        content: result.answer,
        sources: result.sources || [],
      };

      setMessages((current) => [
        ...current,
        assistantMessage,
      ]);


      // ------------------------------------------------------
      // Refresh sidebar
      // ------------------------------------------------------

      await loadSessions();

    } catch (err) {

      console.error(
        "Chat error:",
        err
      );

      setError(
        err.message ||
          "Something went wrong while processing your message."
      );

    } finally {

      setLoading(false);

    }
  }


  // ==========================================================
  // New chat
  // ==========================================================

  function handleNewChat() {

    setSessionId(null);

    setMessages([]);

    setError(null);
  }


  // ==========================================================
  // Select session
  // ==========================================================

 async function handleSelectSession(
  selectedSessionId
) {
  if (loading) {
    return;
  }

  setError(null);
  setLoading(true);

  try {
    const conversation =
      await getConversation(
        selectedSessionId
      );

    setSessionId(
      conversation.session_id
    );

    setMessages(
      conversation.messages.map(
        (message) => ({
          role: message.role,
          content: message.content,
          sources: [],
        })
      )
    );

  } catch (err) {

    console.error(
      "Conversation load error:",
      err
    );

    setError(
      err.message ||
        "Unable to load conversation."
    );

  } finally {

    setLoading(false);

  }
}


  // ==========================================================
  // Render
  // ==========================================================

  return (
    <div className="app-shell">

      <Sidebar
        sessions={sessions}
        sessionId={sessionId}
        loadingSessions={
          loadingSessions
        }
        onNewChat={
          handleNewChat
        }
        onSelectSession={
          handleSelectSession
        }
      />


      <main className="chat-area">

        {/* ====================================================
            Header
            ==================================================== */}

        <header className="chat-header">

          <div>

            <h1>
              Sales Knowledge Base
            </h1>

            <p>
              Ask questions about Regenesys
              programmes and offerings.
            </p>

          </div>


          <div className="connection-status">

            <span />

            Online

          </div>

        </header>


        {/* ====================================================
            Messages
            ==================================================== */}

        <section className="messages-area">

          {messages.length === 0 ? (

            <div className="welcome-screen">

              <div className="welcome-icon">
                ✦
              </div>

              <h2>
                How can I help you?
              </h2>

              <p>
                Ask me about programmes,
                fees, eligibility, duration,
                NQF levels, and other
                information in the
                knowledge base.
              </p>


              <div className="suggestion-grid">

                <button
                  onClick={() =>
                    handleSend(
                      "What programmes does the Business School offer?"
                    )
                  }
                >
                  Business School programmes
                </button>


                <button
                  onClick={() =>
                    handleSend(
                      "What programmes does the School of AI offer?"
                    )
                  }
                >
                  School of AI programmes
                </button>


                <button
                  onClick={() =>
                    handleSend(
                      "What is the duration of the MBA?"
                    )
                  }
                >
                  MBA duration
                </button>


                <button
                  onClick={() =>
                    handleSend(
                      "What are the MBA eligibility requirements?"
                    )
                  }
                >
                  MBA eligibility
                </button>

              </div>

            </div>

          ) : (

            <div className="messages-container">

              {messages.map(
                (message, index) => (

                  <div
                    key={index}
                    className="message-wrapper"
                  >

                    <MessageBubble
                      role={
                        message.role
                      }
                      content={
                        message.content
                      }
                    />


                    {message.role ===
                      "assistant" && (

                      <SourceList
                        sources={
                          message.sources
                        }
                      />

                    )}

                  </div>

                )
              )}


              {loading && (

                <div className="message-row message-row-assistant">

                  <div className="message-bubble message-bubble-assistant typing">

                    <div className="assistant-label">
                      RegAIcademy AI
                    </div>

                    <div className="typing-indicator">

                      <span />
                      <span />
                      <span />

                    </div>

                  </div>

                </div>

              )}

            </div>

          )}

        </section>


        {/* ====================================================
            Error
            ==================================================== */}

        {error && (

          <div className="error-message">
            {error}
          </div>

        )}


        {/* ====================================================
            Input
            ==================================================== */}

        <footer className="chat-footer">

          <ChatInput
            onSend={handleSend}
            disabled={loading}
          />

          <div className="footer-note">
            Answers are generated from the
            Sales Knowledge Base.
          </div>

        </footer>

      </main>

    </div>
  );
}


export default App;