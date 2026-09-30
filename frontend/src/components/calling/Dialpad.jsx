const DIALPAD_KEYS = [
  ["1", ""],
  ["2", "ABC"],
  ["3", "DEF"],
  ["4", "GHI"],
  ["5", "JKL"],
  ["6", "MNO"],
  ["7", "PQRS"],
  ["8", "TUV"],
  ["9", "WXYZ"],
  ["*", ""],
  ["0", "+"],
  ["#", ""],
];

const MAX_NUMBER_LENGTH = 20;

/**
 * Dialpad. Doubles as the in-call keypad: while a call is up, presses are
 * shown as DTMF but not sent — the voice-engine has no DTMF-out endpoint yet
 * (it only *receives* ChannelDtmfReceived), so this stays an honest stub.
 */
function Dialpad({
  value,
  onChange,
  onCall,
  disabled = false,
  isInCall = false,
  onDtmfPreview,
}) {
  function handleKey(key) {
    if (key === "0" && isInCall) {
      onDtmfPreview?.("0");
      return;
    }

    if (value.length >= MAX_NUMBER_LENGTH) {
      return;
    }

    onChange(`${value}${key}`);
  }

  function handleKeyDown(event) {
    const key = event.key;

    if (/^[0-9*#+]$/.test(key)) {
      event.preventDefault();
      handleKey(key);
    } else if (key === "Backspace") {
      event.preventDefault();
      onChange(value.slice(0, -1));
    } else if (key === "Enter") {
      event.preventDefault();
      onCall();
    }
  }

  return (
    <div className="dialpad">

      <div className="dialpad-display">

        <input
          className="dialpad-number"
          value={value}
          onChange={(event) =>
            onChange(event.target.value.replace(/[^0-9+*#\s]/g, ""))
          }
          onKeyDown={handleKeyDown}
          placeholder="Enter a phone number"
          inputMode="tel"
          autoComplete="off"
          aria-label="Phone number"
        />

        {value && (
          <button
            type="button"
            className="dialpad-clear"
            onClick={() => onChange("")}
            title="Clear number"
          >
            ✕
          </button>
        )}

      </div>

      <div className="dialpad-keys">

        {DIALPAD_KEYS.map(([key, letters]) => (
          <button
            key={key}
            type="button"
            className="dialpad-key"
            onClick={() => handleKey(key)}
            disabled={disabled}
          >
            <span className="dialpad-key-digit">
              {key === "0" && isInCall ? "0" : key}
            </span>
            <span className="dialpad-key-letters">
              {key === "0" ? "+" : letters}
            </span>
          </button>
        ))}

      </div>

      <div className="dialpad-actions">

        <button
          type="button"
          className="call-button"
          onClick={onCall}
          disabled={disabled || value.replace(/\D/g, "").length < 3}
          title="Place the call"
        >
          <span className="call-button-icon">
            📞
          </span>

          <span className="call-button-label">
            {isInCall ? "Call in progress" : "Call"}
          </span>
        </button>

        <button
          type="button"
          className="backspace-button"
          onClick={() => onChange(value.slice(0, -1))}
          disabled={!value}
          title="Delete last digit"
        >
          ⌫
        </button>

      </div>

    </div>
  );
}

export default Dialpad;
