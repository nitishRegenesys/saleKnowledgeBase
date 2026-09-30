/**
 * Call log persisted in localStorage.
 *
 * The voice-engine keeps calls in memory only (a finished call disappears
 * from /api/threecx/calls), so the dashboard owns the log until the call
 * history API is provided — swap the four functions below for fetch() calls
 * and nothing else in the app has to change.
 */

const STORAGE_KEY = "skb.call-history.v1";

const MAX_RECORDS = 50;

function isBrowser() {
  return typeof window !== "undefined" && Boolean(window.localStorage);
}

export function loadCallHistory() {
  if (!isBrowser()) {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);

    if (!raw) {
      return [];
    }

    const parsed = JSON.parse(raw);

    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveCallHistory(records) {
  if (!isBrowser()) {
    return records;
  }

  try {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(records.slice(0, MAX_RECORDS)),
    );
  } catch {
    // Storage full or blocked: keep the in-memory list usable
  }

  return records;
}

export function addCallRecord(records, record) {
  const next = [record, ...records].slice(0, MAX_RECORDS);

  return saveCallHistory(next);
}

export function clearCallHistory() {
  if (!isBrowser()) {
    return [];
  }

  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Ignore
  }

  return [];
}

/**
 * One finished (or failed) call attempt. `conversation` is carried through so
 * the transcript of a live call stays readable from the log; the future
 * history API will own this field instead.
 */
export function createCallRecord({
  channelId = null,
  phone = "",
  contactName = null,
  status = "COMPLETED",
  note = null,
  startedAt = Date.now(),
  durationSec = 0,
  turnCount = 0,
  conversation = [],
}) {
  return {
    id: `${channelId || "call"}-${startedAt}`,
    channel_id: channelId,
    phone,
    contact_name: contactName,
    direction: "outbound",
    status,
    note,
    started_at: startedAt,
    duration_sec: durationSec,
    turn_count: turnCount,
    conversation,
  };
}
