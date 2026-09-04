import { useEffect, useRef, useState } from "react";

import ChatInput from "./components/ChatInput";
import MessageBubble from "./components/MessageBubble";
import Sidebar from "./components/Sidebar";
import SourceList from "./components/SourceList";

import useVoiceRecorder from "./hooks/useVoiceRecorder";

import {
  getSessions,
  sendChatMessage,
  getConversation,
  synthesizeSpeech,
  streamChatMessage,
  getVoiceSocketUrl,
  getVoiceHealth,
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

  const [voiceError, setVoiceError] =
    useState(null);

  const [isSpeaking, setIsSpeaking] =
    useState(false);

  const [voiceStatus, setVoiceStatus] =
    useState("idle");

  const [partialText, setPartialText] =
    useState("");

  const [streamingAnswer, setStreamingAnswer] =
    useState(null);

  // Voice-engine reachability (null = not checked yet,
  // treated as unavailable so the UI starts hidden)
  const [voiceAvailable, setVoiceAvailable] =
    useState(null);

  const audioRef = useRef(null);

  // ---- voice pipeline refs ----

  const voiceWsRef = useRef(null);
  const finalizeRequestedRef = useRef(false);
  const turnInProgressRef = useRef(false);
  const voiceAbortedRef = useRef(false);
  const answerStreamingRef = useRef(false);
  const pendingSentencesRef = useRef([]);
  const speakInFlightRef = useRef(false);
  const sentenceBytesRef = useRef([]);
  const speechQueueRef = useRef([]);
  const playInFlightRef = useRef(false);

  // Committed transcript accumulation + finalize timers
  const finalTranscriptRef = useRef("");
  const finalizeCommitTimerRef = useRef(null);
  const finalizeDeadlineTimerRef = useRef(null);
  const micActiveRef = useRef(false);

  // Stop-speech: mutes the rest of a streamed turn and
  // tracks which replay message is currently speaking
  const speechMutedRef = useRef(false);
  const [speakingMessageIdx, setSpeakingMessageIdx] =
    useState(null);

  const voiceStatusRef = useRef("idle");

  useEffect(() => {
    voiceStatusRef.current = voiceStatus;
  }, [voiceStatus]);

  useEffect(() => {
    return () => {
      // Inline socket close (unmount-only cleanup path).
      const ws = voiceWsRef.current;

      voiceWsRef.current = null;

      if (ws) {
        try {
          ws.close();
        } catch {
          // Ignore
        }
      }
    };
  }, []);


  // ==========================================================
  // Voice recorder
  // ==========================================================

  const {
    error: micError,
    startRecording,
    stopRecording,
  } = useVoiceRecorder({
    onFrame: handleAudioFrame,
    onError: handleMicError,
    onSilence: stopMicAndFinalize,
  });


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


  async function checkVoiceHealth() {
    const available =
      await getVoiceHealth();

    // Never flip the UI in the middle of an active voice
    // turn; failures during the turn are surfaced by the
    // WS error handlers (which re-check right after).
    if (voiceStatusRef.current !== "idle") {
      return;
    }

    setVoiceAvailable(available);
  }

  useEffect(() => {
    loadSessions();

    checkVoiceHealth();

    const voiceHealthInterval =
      setInterval(checkVoiceHealth, 30000);

    return () =>
      clearInterval(voiceHealthInterval);
  }, []);


  // ==========================================================
  // Send message
  // ==========================================================

async function handleSend(message) {
  cancelVoice();

  setError(null);
  setVoiceError(null);

  const userMessage = {
    role: "user",
    content: message,
  };

  setMessages((current) => [
    ...current,
    userMessage,
  ]);

  setLoading(true);

  // Create an empty assistant message immediately.
  setStreamingAnswer({
    text: "",
  });

  try {
    await streamChatMessage({
      sessionId,
      message,
      limit: 5,

      // ------------------------------------------------------
      // Receive answer progressively
      // ------------------------------------------------------

      onDelta: (piece) => {
        setStreamingAnswer((current) => ({
          text: (current?.text || "") + piece,
        }));
      },

      // ------------------------------------------------------
      // Final response
      // ------------------------------------------------------

      onDone: (data) => {
        setSessionId(data.session_id);

        setMessages((current) => [
          ...current,
          {
            role: "assistant",
            content: data.answer,
            sources: data.sources || [],
          },
        ]);

        setStreamingAnswer(null);

        loadSessions();
      },
    });
  } catch (err) {
    console.error(
      "Streaming chat error:",
      err
    );

    setStreamingAnswer(null);

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

    cancelVoice();

    setSessionId(null);

    setMessages([]);

    setError(null);

    setVoiceError(null);
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

  cancelVoice();

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
  // Speech playback
  // ==========================================================

  function stopPlayback() {
    if (audioRef.current) {
      const audio = audioRef.current;

      audio.pause();

      // Release the blob URL (the ended/error handlers do
      // not fire for a paused element).
      if (
        audio.src &&
        audio.src.startsWith("blob:")
      ) {
        URL.revokeObjectURL(audio.src);
      }

      audioRef.current = null;
    }

    setIsSpeaking(false);
  }

  async function playSpeech(idx, text) {
    stopPlayback();

    try {
      setVoiceError(null);

      const audioUrl =
        await synthesizeSpeech(text);

      const audio = new Audio(audioUrl);

      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
        audioRef.current = null;
        setSpeakingMessageIdx(null);
        setIsSpeaking(false);
      };

      audio.onerror = () => {
        URL.revokeObjectURL(audioUrl);
        audioRef.current = null;
        setSpeakingMessageIdx(null);
        setIsSpeaking(false);
      };

      audioRef.current = audio;
      setSpeakingMessageIdx(idx);
      setIsSpeaking(true);

      try {
        await audio.play();
      } catch (err) {
        URL.revokeObjectURL(audioUrl);
        audioRef.current = null;
        setSpeakingMessageIdx(null);
        setIsSpeaking(false);

        throw err;
      }
    } catch (err) {
      console.error(
        "Speech playback error:",
        err
      );

      setVoiceError(
        err?.message ||
          "Unable to play the spoken answer."
      );
    }
  }

  function handleSpeak(idx, text) {
    if (isSpeaking) {
      // Stop if the same message was clicked, otherwise
      // interrupt the current audio and play the new one.
      if (speakingMessageIdx === idx) {
        stopAllSpeech();
        return;
      }

      stopAllSpeech();
    }

    playSpeech(idx, text);
  }

  function handleStopSpeech() {
    stopAllSpeech();
  }

  function stopAllSpeech() {
    // Mute the rest of any streamed turn: drainSpeak and
    // onSentenceSpoken check this flag so late audio.chunk /
    // speak.done events cannot resurrect the audio.
    speechMutedRef.current = true;

    stopPlayback();

    if (speechQueueRef.current.length > 0) {
      speechQueueRef.current.forEach((url) => {
        URL.revokeObjectURL(url);
      });

      speechQueueRef.current = [];
    }

    pendingSentencesRef.current = [];
    sentenceBytesRef.current = [];
    playInFlightRef.current = false;
    speakInFlightRef.current = false;

    setSpeakingMessageIdx(null);
    setIsSpeaking(false);
  }


  // ==========================================================
  // Voice pipeline (WebSocket streaming)
  // ==========================================================

  function closeVoiceSocket() {
    const ws = voiceWsRef.current;

    voiceWsRef.current = null;

    if (ws) {
      try {
        ws.close();
      } catch {
        // Ignore
      }
    }
  }

  function resetVoicePipeline() {
    stopPlayback();

    if (speechQueueRef.current.length > 0) {
      speechQueueRef.current.forEach((url) => {
        URL.revokeObjectURL(url);
      });

      speechQueueRef.current = [];
    }

    playInFlightRef.current = false;
    pendingSentencesRef.current = [];
    speakInFlightRef.current = false;
    sentenceBytesRef.current = [];

    setSpeakingMessageIdx(null);
    setPartialText("");
    setStreamingAnswer(null);
  }

  function cancelVoice() {
    turnInProgressRef.current = false;
    finalizeRequestedRef.current = false;
    answerStreamingRef.current = false;
    micActiveRef.current = false;
    finalTranscriptRef.current = "";
    speechMutedRef.current = false;

    clearFinalizeTimers();

    resetVoicePipeline();
    stopRecording();
    closeVoiceSocket();

    setVoiceStatus("idle");
    setVoiceError(null);
  }

  function handleVoiceError(message) {
    voiceAbortedRef.current = true;
    answerStreamingRef.current = false;
    micActiveRef.current = false;
    finalTranscriptRef.current = "";

    clearFinalizeTimers();

    setVoiceError(message);
    setVoiceStatus("idle");
    voiceStatusRef.current = "idle";

    resetVoicePipeline();
    stopRecording();
    closeVoiceSocket();

    // Re-check reachability right away so the voice UI
    // hides promptly if the engine went down.
    checkVoiceHealth();
  }

  function handleAudioFrame(base64) {
    const ws = voiceWsRef.current;

    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return;
    }

    ws.send(
      JSON.stringify({
        type: "audio",
        data: base64,
      })
    );
  }

  function handleMicError(message) {
    handleVoiceError(
      message ||
        "Unable to access the microphone."
    );
  }

  // ----------------------------------------------------------
  // Transcript finalization helpers
  // ----------------------------------------------------------

  function joinText(left, right) {
    return [left, right]
      .map((part) => (part || "").trim())
      .filter(Boolean)
      .join(" ");
  }

  function clearFinalizeTimers() {
    if (finalizeCommitTimerRef.current) {
      clearTimeout(
        finalizeCommitTimerRef.current
      );

      finalizeCommitTimerRef.current = null;
    }

    if (finalizeDeadlineTimerRef.current) {
      clearTimeout(
        finalizeDeadlineTimerRef.current
      );

      finalizeDeadlineTimerRef.current = null;
    }
  }

  function commitFinalTranscript() {
    clearFinalizeTimers();

    if (!finalizeRequestedRef.current) {
      return;
    }

    finalizeRequestedRef.current = false;

    const text = finalTranscriptRef.current.trim();

    finalTranscriptRef.current = "";

    handleVoiceTranscript(text);
  }

  // ----------------------------------------------------------
  // Turn lifecycle
  // ----------------------------------------------------------

  function startVoiceTurn() {
    setVoiceError(null);

    resetVoicePipeline();
    stopRecording();
    clearFinalizeTimers();

    voiceAbortedRef.current = false;
    finalizeRequestedRef.current = false;
    finalTranscriptRef.current = "";
    micActiveRef.current = false;
    turnInProgressRef.current = false;
    answerStreamingRef.current = false;
    speechMutedRef.current = false;

    setVoiceStatus("connecting");

    const ws = new WebSocket(
      getVoiceSocketUrl()
    );

    voiceWsRef.current = ws;

    ws.onopen = () => {
      if (voiceWsRef.current !== ws) {
        try {
          ws.close();
        } catch {
          // Ignore
        }

        return;
      }

      setVoiceStatus("recording");

      micActiveRef.current = true;

      startRecording();
    };

    ws.onmessage = (event) => {
      handleVoiceMessage(event);
    };

    ws.onerror = () => {
      if (voiceWsRef.current !== ws) {
        return;
      }

      handleVoiceError(
        "Voice service is unavailable."
      );
    };

    ws.onclose = () => {
      if (voiceWsRef.current !== ws) {
        return;
      }

      voiceWsRef.current = null;

      if (
        answerStreamingRef.current ||
        turnInProgressRef.current ||
        micActiveRef.current
      ) {
        handleVoiceError(
          "Voice connection was lost."
        );
        return;
      }

      setVoiceStatus("idle");
      resetVoicePipeline();
      stopRecording();
    };
  }

  function stopMicAndFinalize() {
    stopRecording();

    micActiveRef.current = false;

    setVoiceStatus("waiting");

    const ws = voiceWsRef.current;

    if (!ws || ws.readyState !== WebSocket.OPEN) {
      handleVoiceError(
        "Voice connection was lost."
      );

      return;
    }

    // Arm the transcript commit BEFORE sending <end>: the engine
    // finalizes the STT stream and emits transcript.final; if no
    // final ever arrives (e.g. silence), the deadline commits
    // whatever accumulated so the turn cannot hang in "waiting".
    finalizeRequestedRef.current = true;

    clearFinalizeTimers();

    finalizeDeadlineTimerRef.current = setTimeout(
      commitFinalTranscript,
      3000
    );

    ws.send(
      JSON.stringify({
        type: "audio",
        data: "<end>",
      })
    );
  }

  function finishVoiceTurn() {
    turnInProgressRef.current = false;
    finalizeRequestedRef.current = false;
    micActiveRef.current = false;
    finalTranscriptRef.current = "";

    clearFinalizeTimers();

    setVoiceStatus("idle");
    setIsSpeaking(false);

    stopRecording();
    closeVoiceSocket();
  }

  function maybeFinishTurn() {
    if (
      answerStreamingRef.current ||
      speakInFlightRef.current ||
      pendingSentencesRef.current.length > 0 ||
      speechQueueRef.current.length > 0 ||
      playInFlightRef.current
    ) {
      return;
    }

    if (turnInProgressRef.current) {
      finishVoiceTurn();
    }
  }

  function handleMicrophoneToggle() {
    if (loading || voiceAvailable !== true) {
      return;
    }

    if (voiceStatus === "recording") {
      stopMicAndFinalize();
      return;
    }

    if (voiceStatus !== "idle") {
      return;
    }

    startVoiceTurn();
  }

// ----------------------------------------------------------
  // WS message handler
  // ----------------------------------------------------------

  function handleVoiceMessage(event) {
    let msg;

    try {
      msg = JSON.parse(event.data);
    } catch {
      return;
    }

    if (!msg || typeof msg !== "object") {
      return;
    }

    switch (msg.type) {
      case "transcript.partial":
        // Only show live partials while the mic is actually
        // recording; trailing partials after finalize would
        // otherwise overwrite the committed transcript.
        if (!micActiveRef.current) {
          break;
        }

        setPartialText(
          joinText(
            finalTranscriptRef.current,
            msg.text
          )
        );
        break;

      case "transcript.final": {
        const piece = (msg.text || "").trim();

        if (!finalizeRequestedRef.current) {
          // Still recording: the engine commits one final
          // per utterance, so accumulate them (multi-sentence
          // questions produce several finals) and show the
          // committed text live.
          finalTranscriptRef.current = joinText(
            finalTranscriptRef.current,
            piece
          );

          setPartialText(
            finalTranscriptRef.current
          );

          break;
        }

        // Mic stopped: collect the flushed finals briefly —
        // the committed text can arrive in more than one
        // segment — then start the turn once they settle.
        finalTranscriptRef.current = joinText(
          finalTranscriptRef.current,
          piece
        );

        if (finalizeCommitTimerRef.current) {
          clearTimeout(
            finalizeCommitTimerRef.current
          );
        }

        finalizeCommitTimerRef.current = setTimeout(
          commitFinalTranscript,
          600
        );

        break;
      }

      case "audio.chunk":
        appendSentenceBytes(msg.data);
        break;

      case "speak.done":
        onSentenceSpoken();
        break;

      default:
        break;
    }
  }

  // ----------------------------------------------------------
  // Streaming answer + sentence-chunked speech
  // ----------------------------------------------------------

  function appendSentenceBytes(base64) {
    if (!base64) {
      return;
    }

    try {
      const binary = atob(base64);
      const bytes = new Uint8Array(
        binary.length
      );

      for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
      }

      sentenceBytesRef.current.push(bytes);
    } catch (err) {
      console.error(
        "Audio chunk decode error:",
        err
      );
    }
  }

  function drainSpeak() {
    if (speechMutedRef.current) {
      return;
    }

    if (speakInFlightRef.current) {
      return;
    }

    if (pendingSentencesRef.current.length === 0) {
      return;
    }

    const ws = voiceWsRef.current;

    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return;
    }

    const sentence =
      pendingSentencesRef.current.shift();

    speakInFlightRef.current = true;
    sentenceBytesRef.current = [];

    ws.send(
      JSON.stringify({
        type: "speak",
        data: sentence,
      })
    );
  }

  function onSentenceSpoken() {
    speakInFlightRef.current = false;

    const parts = sentenceBytesRef.current;

    sentenceBytesRef.current = [];

    // Speech was stopped: discard any late audio for the
    // in-flight sentence instead of queueing it.
    if (speechMutedRef.current) {
      drainSpeak();
      maybeFinishTurn();

      return;
    }

    if (parts.length > 0) {
      let total = 0;

      for (const part of parts) {
        total += part.length;
      }

      const merged = new Uint8Array(total);

      let offset = 0;

      for (const part of parts) {
        merged.set(part, offset);
        offset += part.length;
      }

      const blob = new Blob(
        [merged.buffer],
        { type: "audio/mpeg" }
      );

      const url = URL.createObjectURL(blob);

      speechQueueRef.current.push(url);

      pumpPlayback();
    }

    drainSpeak();
    maybeFinishTurn();
  }

  function pumpPlayback() {
    if (playInFlightRef.current) {
      return;
    }

    const url = speechQueueRef.current.shift();

    if (!url) {
      return;
    }

    playInFlightRef.current = true;
    setIsSpeaking(true);

    const audio = new Audio(url);
    audioRef.current = audio;

    const cleanup = () => {
      URL.revokeObjectURL(url);
      audioRef.current = null;
      playInFlightRef.current = false;
      setIsSpeaking(false);

      pumpPlayback();
      maybeFinishTurn();
    };

    audio.onended = cleanup;
    audio.onerror = cleanup;
    audio.play().catch(cleanup);
  }

  async function handleVoiceTranscript(text) {
    if (!text) {
      setVoiceError(
        "No speech was detected. Please try again."
      );

      finishVoiceTurn();

      return;
    }

    setPartialText("");

    turnInProgressRef.current = true;
    voiceAbortedRef.current = false;

    setMessages((current) => [
      ...current,
      {
        role: "user",
        content: text,
      },
    ]);

    setVoiceStatus("answering");
    answerStreamingRef.current = true;

    try {
      await streamChatMessage({
        sessionId,
        message: text,
        limit: 5,
        onDelta: (piece) => {
          setStreamingAnswer((current) => ({
            text: (current?.text || "") + piece,
          }));

          pendingSentencesRef.current.push(piece);
          drainSpeak();
        },
        onDone: (data) => {
          answerStreamingRef.current = false;

          setSessionId(data.session_id);

          setMessages((current) => [
            ...current,
            {
              role: "assistant",
              content: data.answer,
              sources: data.sources || [],
            },
          ]);

          setStreamingAnswer(null);
          loadSessions();

          if (
            !voiceAbortedRef.current &&
            !speechMutedRef.current
          ) {
            setVoiceStatus("speaking");
          }
        },
      });

      answerStreamingRef.current = false;
      maybeFinishTurn();
    } catch (err) {
      console.error(
        "Voice chat error:",
        err
      );

      handleVoiceError(
        err?.message ||
          "Unable to process your question right now."
      );
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
                      onSpeak={
                        voiceAvailable === true &&
                        message.role ===
                          "assistant"
                          ? (content) =>
                              handleSpeak(
                                index,
                                content
                              )
                          : undefined
                      }
                      speaking={
                        speakingMessageIdx ===
                        index
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


              {streamingAnswer && (

                <div className="message-row message-row-assistant">

                  <div className="message-bubble message-bubble-assistant">

                    <div className="assistant-label">
                      RegAIcademy AI
                    </div>

                    <div className="message-content streaming-text">
                      {streamingAnswer.text}
                    </div>

                  </div>

                </div>

              )}


              {loading && !streamingAnswer &&(

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


        {(voiceError || micError) && (

          <div className="voice-error">
            {voiceError || micError}
          </div>

        )}


        {/* ====================================================
            Input
            ==================================================== */}

        <footer className="chat-footer">

          <ChatInput
            onSend={handleSend}
            disabled={
              loading ||
              voiceStatus === "connecting" ||
              voiceStatus === "waiting" ||
              voiceStatus === "answering"
            }
            onMicrophoneToggle={handleMicrophoneToggle}
            recording={
              voiceStatus === "recording"
            }
            micDisabled={
              loading ||
              (voiceStatus !== "idle" &&
                voiceStatus !== "recording")
            }
            transcribing={
              voiceStatus === "connecting" ||
              voiceStatus === "waiting" ||
              voiceStatus === "answering"
            }
            voiceEnabled={
              voiceAvailable === true
            }
          />

          <div className="footer-note">
            {voiceStatus === "recording" && (
              <>
                {partialText
                  ? `“${partialText}” — listening... stops automatically after you finish speaking.`
                  : "Listening... speak now; it stops automatically after you finish (or click the mic to stop)."}
              </>
            )}

            {voiceStatus === "waiting" &&
              "Waiting for the transcript..."}

            {voiceStatus === "answering" &&
              "Preparing your answer..."}

            {voiceStatus === "speaking" &&
              "Speaking..."}

            {(voiceStatus === "idle" ||
              voiceStatus === "connecting") &&
              "Answers are generated from the Sales Knowledge Base."}
          </div>

          {isSpeaking && (
            <button
              type="button"
              className="stop-speech-button"
              onClick={handleStopSpeech}
            >
              ⏹ Stop speaking
            </button>
          )}

        </footer>

      </main>

    </div>
  );
}


export default App;