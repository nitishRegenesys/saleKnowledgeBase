import ConversationPanel from "./ConversationPanel";

import {
  formatDuration,
  formatPhoneNumber,
  getStatusMeta,
  isLiveState,
} from "../../utils/format";

/**
 * Live-call panel: engine state, timer, transcript toggle and the controls.
 *
 * Mute / transfer stay as clearly-labelled stubs because the voice-engine has
 * no endpoint for either yet.
 */
function CallPanel({
  activeCall,
  elapsedSeconds,
  isPlacingCall,
  isHangingUp,
  callError,
  engineStatus,
  showConversation,
  onToggleConversation,
  onHangup,
  onDismissError,
}) {
  const state = activeCall?.state || "IDLE";
  const statusMeta = getStatusMeta(state);
  const live = isLiveState(state);

  const engineOffline = engineStatus && !engineStatus.engine_reachable;
  const engineDisabled =
    engineStatus &&
    engineStatus.engine_reachable &&
    !engineStatus.connected;

  return (
    <aside className="call-panel">

      <div className="call-panel-header">

        <div className="call-panel-title">
          Live call
        </div>

        <span
          className={`status-pill status-pill-${statusMeta.tone} ${
            live ? "status-pill-live" : ""
          }`}
        >
          {statusMeta.label}
        </span>

      </div>

      {callError && (
        <div className="call-error">

          <span>{callError}</span>

          <button
            type="button"
            onClick={onDismissError}
            title="Dismiss"
          >
            ✕
          </button>

        </div>
      )}

      {engineOffline && (
        <div className="call-warning">
          Calling engine offline. Start the voice-engine service to place
          calls.
        </div>
      )}

      {engineDisabled && (
        <div className="call-warning">
          Calling engine is not connected to Asterisk/3CX yet
          (ASTERISK_ENABLED / ARI).
        </div>
      )}

      <div className="call-stage">

        {activeCall ? (
          <>

            <div className="call-avatar">
              📞
            </div>

            <div className="call-who">
              {activeCall.contact_name || "Outbound call"}
            </div>

            <div className="call-phone">
              {formatPhoneNumber(activeCall.phone)}
            </div>

            <div className="call-timer">
              {formatDuration(elapsedSeconds)}
            </div>

            <div className="call-facts">

              <div className="call-fact">
                <span>Turns</span>
                <strong>
                  {activeCall.turn_number ?? 0}
                </strong>
              </div>

              <div className="call-fact">
                <span>From</span>
                <strong>
                  {activeCall.from_extension || "—"}
                </strong>
              </div>

            </div>

          </>
        ) : (
          <>

            <div className="call-avatar call-avatar-idle">
              💤
            </div>

            <div className="call-who">
              {isPlacingCall
                ? "Placing your call..."
                : "No active call"}
            </div>

            <div className="call-phone">
              {isPlacingCall
                ? "Contacting the gateway"
                : "Pick a user or dial a number"}
            </div>

          </>
        )}

      </div>

      <div className="call-controls">

        <button
          type="button"
          className="call-control"
          disabled={!activeCall}
          title="Mute is not wired to the engine yet"
        >
          🎙
          <span>Mute</span>
        </button>

        <button
          type="button"
          className="call-button call-button-hangup"
          onClick={onHangup}
          disabled={!activeCall || isHangingUp}
        >
          {isHangingUp ? "Ending..." : "Hang up"}
        </button>

        <button
          type="button"
          className="call-control"
          disabled={!activeCall}
          title="Transfer is not wired to the engine yet"
        >
          ⇄
          <span>Transfer</span>
        </button>

      </div>

      <button
        type="button"
        className={`conversation-toggle ${
          showConversation ? "conversation-toggle-open" : ""
        }`}
        onClick={onToggleConversation}
      >
        {showConversation
          ? "Hide conversation"
          : "Conversation history"}
      </button>

      {showConversation && (
        <ConversationPanel
          conversation={activeCall?.conversation || []}
          hasCall={Boolean(activeCall)}
        />
      )}

    </aside>
  );
}

export default CallPanel;
