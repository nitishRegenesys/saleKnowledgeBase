export function getInitials(name = "") {
  const parts = name
    .trim()
    .split(/\s+/)
    .filter(Boolean);

  if (parts.length === 0) {
    return "#";
  }

  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }

  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/**
 * Groups dial-string digits the way a phone app does
 * ("0734567891" -> "073 456 7891"), leaving anything odd at the end.
 */
export function formatPhoneNumber(value = "") {
  const digits = String(value).replace(/[^0-9+]/g, "");

  if (digits.length <= 3) {
    return digits;
  }

  const body = digits.replace(/^\+/, "");
  const groups = body.match(/(\d{1,3})/g) || [];

  const formatted = groups
    .map((group) => group.padEnd(3, " ").trim())
    .join(" ")
    .trim();

  return digits.startsWith("+") ? `+${formatted}` : formatted;
}

export function formatDuration(totalSeconds = 0) {
  const seconds = Math.max(0, Math.floor(Number(totalSeconds) || 0));

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const rest = seconds % 60;

  const pad = (value) => String(value).padStart(2, "0");

  return hours > 0
    ? `${hours}:${pad(minutes)}:${pad(rest)}`
    : `${pad(minutes)}:${pad(rest)}`;
}

export function formatCallTime(timestamp) {
  if (!timestamp) {
    return "";
  }

  const date = new Date(timestamp);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  const isToday = date.toDateString() === new Date().toDateString();

  return isToday
    ? `Today ${date.toLocaleTimeString(undefined, {
        hour: "2-digit",
        minute: "2-digit",
      })}`
    : date.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
}

/**
 * Engine CallState values (NEW/DIALING/RINGING/ANSWERED/WELCOME/LISTENING/
 * THINKING/SPEAKING/ENDED) plus call-log statuses mapped to a human label and
 * a CSS tone modifier.
 */
const STATUS_META = {
  NEW: { label: "Starting", tone: "neutral" },
  DIALING: { label: "Dialing", tone: "warn" },
  RINGING: { label: "Ringing", tone: "warn" },
  ANSWERED: { label: "Connected", tone: "live" },
  WELCOME: { label: "AI greeting", tone: "live" },
  LISTENING: { label: "AI listening", tone: "live" },
  THINKING: { label: "AI thinking", tone: "live" },
  SPEAKING: { label: "AI speaking", tone: "live" },
  ENDED: { label: "Ended", tone: "neutral" },
  COMPLETED: { label: "Completed", tone: "positive" },
  BUSY: { label: "Busy", tone: "warn" },
  NO_ANSWER: { label: "No answer", tone: "warn" },
  FAILED: { label: "Failed", tone: "danger" },
  IDLE: { label: "No active call", tone: "neutral" },
};

export function getStatusMeta(status) {
  return (
    STATUS_META[String(status || "").toUpperCase()] || {
      label: status || "Idle",
      tone: "neutral",
    }
  );
}

/** True while the engine reports the call as still up. */
export function isLiveState(status) {
  return [
    "NEW",
    "DIALING",
    "RINGING",
    "ANSWERED",
    "WELCOME",
    "LISTENING",
    "THINKING",
    "SPEAKING",
  ].includes(String(status || "").toUpperCase());
}
