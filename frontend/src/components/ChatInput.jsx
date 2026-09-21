import { useState } from "react";

function ChatInput({
  onSend,
  disabled = false,
  onMicrophoneToggle,
  recording = false,
  micDisabled = false,
  transcribing = false,
  voiceEnabled = false,
}) {
  const [message, setMessage] = useState("");

  function handleSubmit(event) {
    event.preventDefault();

    const trimmedMessage = message.trim();

    if (!trimmedMessage || disabled) {
      return;
    }

    onSend(trimmedMessage);
    setMessage("");
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit(event);
    }
  }

  function handleMicClick() {
    if (micDisabled || transcribing || disabled) {
      return;
    }

    onMicrophoneToggle();
  }

  return (
    <form
      className="chat-input-container"
      onSubmit={handleSubmit}
    >
      <textarea
        value={message}
        onChange={(event) =>
          setMessage(event.target.value)
        }
        onKeyDown={handleKeyDown}
        placeholder="Ask about programmes, fees, eligibility, duration..."
        disabled={disabled}
        rows={1}
      />

      {voiceEnabled && (
        <button
          type="button"
          className={`mic-button ${
            recording ? "mic-button-recording" : ""
          }`}
          onClick={handleMicClick}
          disabled={
            disabled || micDisabled || transcribing
          }
          title={
            recording
              ? "Stop recording"
              : transcribing
                ? "Transcribing..."
                : "Record a question"
          }
        >
          {transcribing ? "..." : recording ? "■" : "🎤"}
        </button>
      )}

      <button
        type="submit"
        disabled={
          disabled || !message.trim()
        }
      >
        {disabled ? "..." : "Send"}
      </button>
    </form>
  );
}

export default ChatInput;