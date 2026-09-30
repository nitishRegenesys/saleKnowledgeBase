import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  getActiveCalls,
  hangupCall,
  startOutboundCall,
} from "../services/callingApi";

import { createCallRecord } from "../services/callHistory";

const POLL_INTERVAL_MS = 2000;

/**
 * Grace period for the engine to register the channel it just dialed. If the
 * session never shows up in /calls, the attempt is logged as failed instead of
 * leaving the dashboard stuck on "Dialing".
 */
const SETTLE_TIMEOUT_MS = 45000;

/**
 * Owns one outbound call: place it, poll the engine while it is up, expose the
 * live state/duration/transcript, and hand a finished record to
 * `onCallResolved` (the dashboard writes it to the call log).
 *
 * The engine only reports calls it still holds in memory, so the moment a
 * channel leaves the active list the call is treated as finished.
 */
export default function useCallSession({
  onCallResolved,
} = {}) {
  const [activeCall, setActiveCall] = useState(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [isPlacingCall, setIsPlacingCall] = useState(false);
  const [isHangingUp, setIsHangingUp] = useState(false);
  const [callError, setCallError] = useState(null);

  const pollRef = useRef(null);
  const tickRef = useRef(null);
  const callRef = useRef(null);
  const resolvedRef = useRef(onCallResolved);

  useEffect(() => {
    resolvedRef.current = onCallResolved;
  }, [onCallResolved]);

  function clearTimers() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }

    if (tickRef.current) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
  }

  // Unmount: stop polling. The engine-side call is untouched (a real phone
  // call keeps running if you navigate away); no log entry is written for it.
  useEffect(() => clearTimers, []);

  const finishCall = useCallback(
    (status, note = null) => {
      clearTimers();

      const call = callRef.current;

      callRef.current = null;
      setActiveCall(null);
      setElapsedSeconds(0);

      if (!call) {
        return;
      }

      resolvedRef.current?.(
        createCallRecord({
          channelId: call.channel_id,
          phone: call.phone,
          contactName: call.contact_name,
          status,
          note,
          startedAt: call.started_at,
          durationSec: call.duration_sec || 0,
          turnCount: call.turn_number || 0,
          conversation: call.conversation || [],
        })
      );
    },
    []
  );

  const poll = useCallback(async () => {
    const call = callRef.current;

    if (!call) {
      return;
    }

    const data = await getActiveCalls();

    const session = (data.active_calls || []).find(
      (item) => item.channel_id === call.channel_id
    );

    if (session) {
      call.seen_active = true;
      call.state = session.state || call.state;
      call.turn_number =
        session.turn_number ?? call.turn_number;
      call.conversation =
        session.conversation || call.conversation;
      call.duration_sec =
        typeof session.duration_sec === "number"
          ? Math.round(session.duration_sec)
          : call.duration_sec;

      setElapsedSeconds(call.duration_sec || 0);
      setActiveCall({ ...call });

      if (session.state === "ENDED") {
        finishCall(session.final_status || "COMPLETED");
      }

      return;
    }

    // The channel is gone from the engine registry.
    if (call.seen_active) {
      finishCall(
        data.engine_reachable === false
          ? "FAILED"
          : call.final_status_hint || "COMPLETED",
        data.engine_reachable === false
          ? "Calling engine stopped responding."
          : null
      );

      return;
    }

    // Never appeared as an active channel.
    if (Date.now() - call.started_at > SETTLE_TIMEOUT_MS) {
      finishCall(
        data.engine_reachable === false ? "FAILED" : "NO_ANSWER",
        data.engine_reachable === false
          ? "Calling engine stopped responding."
          : "The call did not connect within 45 seconds."
      );
    }
  }, [finishCall]);

  const startTimers = useCallback(() => {
    clearTimers();

    tickRef.current = setInterval(() => {
      const call = callRef.current;

      if (!call) {
        return;
      }

      // Before the answer there is no engine duration, so count locally.
      setElapsedSeconds(
        call.duration_sec > 0
          ? call.duration_sec
          : Math.round((Date.now() - call.started_at) / 1000)
      );
    }, 1000);

    pollRef.current = setInterval(poll, POLL_INTERVAL_MS);

    poll();
  }, [poll]);

  const dial = useCallback(
    async ({ phone, contact = null }) => {
      clearTimers();

      setCallError(null);
      setIsPlacingCall(true);

      try {
        const result = await startOutboundCall({
          phone,
          customerId: contact?.id || null,
        });

        const call = {
          channel_id: result.channel_id,
          phone: result.to || phone,
          contact_name: contact?.name || null,
          from_extension: result.from_extension || null,
          state: (result.status || "dialing").toUpperCase(),
          started_at: Date.now(),
          duration_sec: 0,
          turn_number: 0,
          conversation: [],
          seen_active: false,
          final_status_hint: null,
        };

        callRef.current = call;

        setElapsedSeconds(0);
        setActiveCall({ ...call });
        startTimers();

        return result;
      } catch (error) {
        setCallError(error.message);

        // A rejected dial still belongs in the call log.
        resolvedRef.current?.(
          createCallRecord({
            phone,
            contactName: contact?.name || null,
            status: "FAILED",
            note: error.message,
            durationSec: 0,
          })
        );

        return null;
      } finally {
        setIsPlacingCall(false);
      }
    },
    [startTimers]
  );

  const hangup = useCallback(async () => {
    const call = callRef.current;

    if (!call) {
      return;
    }

    setCallError(null);
    setIsHangingUp(true);

    try {
      await hangupCall(call.channel_id);
      call.final_status_hint = "COMPLETED";
    } catch (error) {
      // "Unknown channel id" is expected when the call already ended;
      // close locally either way so the UI never sticks on a live call.
      setCallError(error.message);
      call.final_status_hint = "COMPLETED";
    } finally {
      setIsHangingUp(false);
      finishCall(call.final_status_hint || "COMPLETED");
    }
  }, [finishCall]);

  const dismissCallError = useCallback(() => {
    setCallError(null);
  }, []);

  return {
    activeCall,
    elapsedSeconds,
    isPlacingCall,
    isHangingUp,
    callError,
    dial,
    hangup,
    dismissCallError,
  };
}

