import {
  formatCallTime,
  formatDuration,
  formatPhoneNumber,
  getStatusMeta,
} from "../../utils/format";

/**
 * Call log. Persisted locally by services/callHistory.js until the backend
 * call-history API is provided.
 */
function CallHistoryList({
  history,
  isBusy,
  onRecall,
  onClear,
}) {
  return (
    <section className="history-card">

      <div className="history-header">

        <div>

          <h2>
            Call history
          </h2>

          <p>
            {history.length === 0
              ? "No calls placed yet from this browser."
              : `${history.length} call${
                  history.length === 1 ? "" : "s"
                } on this device.`}
          </p>

        </div>

        {history.length > 0 && (
          <button
            type="button"
            className="history-clear"
            onClick={onClear}
          >
            Clear
          </button>
        )}

      </div>

      {history.length === 0 ? (
        <div className="panel-empty">
          Place your first call with the dialpad or a user on the left.
        </div>
      ) : (
        <div className="history-list">

          <div className="history-row history-row-head">
            <span>When</span>
            <span>Who</span>
            <span>Number</span>
            <span>Status</span>
            <span>Duration</span>
            <span />
          </div>

          {history.map((record) => {
            const statusMeta = getStatusMeta(
              record.status
            );

            return (
              <div
                key={record.id}
                className="history-row"
              >

                <span className="history-when">
                  {formatCallTime(record.started_at)}
                </span>

                <span className="history-who">
                  {record.contact_name || "Unknown"}
                </span>

                <span className="history-phone">
                  {formatPhoneNumber(record.phone)}
                </span>

                <span>
                  <span
                    className={`status-pill status-pill-${statusMeta.tone}`}
                  >
                    {statusMeta.label}
                  </span>

                  {record.note && (
                    <span
                      className="history-note"
                      title={record.note}
                    >
                      {record.note}
                    </span>
                  )}
                </span>

                <span className="history-duration">
                  {formatDuration(record.duration_sec)}
                </span>

                <span className="history-actions">

                  <button
                    type="button"
                    className="history-recall"
                    onClick={() => onRecall(record)}
                    disabled={isBusy}
                    title={`Call ${record.phone} again`}
                  >
                    📞
                  </button>

                  {record.conversation?.length > 0 && (
                    <span
                      className="history-transcript"
                      title={`${record.turn_count} exchange(s) captured`}
                    >
                      💬
                    </span>
                  )}

                </span>

              </div>
            );
          })}

        </div>
      )}

    </section>
  );
}

export default CallHistoryList;
