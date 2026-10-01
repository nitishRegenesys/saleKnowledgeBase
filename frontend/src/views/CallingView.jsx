import { useCallback, useEffect, useMemo, useState } from "react";

import CallHistoryList from "../components/calling/CallHistoryList";
import CallPanel from "../components/calling/CallPanel";
import ContactList from "../components/calling/ContactList";
import Dialpad from "../components/calling/Dialpad";

import useCallSession from "../hooks/useCallSession";

import {
  getCallContacts,
  getCallingStatus,
} from "../services/callingApi";

import {
  addCallRecord,
  clearCallHistory,
  loadCallHistory,
} from "../services/callHistory";

import { OFFLINE_CONTACTS } from "../data/contacts";

const ENGINE_POLL_MS = 15000;

function samePhone(a = "", b = "") {
  return (
    String(a).replace(/\D/g, "") === String(b).replace(/\D/g, "")
  );
}

/**
 * AI Calling dashboard: users on the left, dialpad + call log in the middle,
 * live-call panel on the right.
 */
function CallingView({ onNavigateHome }) {

  const [contacts, setContacts] = useState([]);
  const [loadingContacts, setLoadingContacts] = useState(true);
  const [isOfflineSource, setIsOfflineSource] = useState(false);

  const [search, setSearch] = useState("");
  const [selectedContact, setSelectedContact] = useState(null);
  const [dialValue, setDialValue] = useState("");

  const [history, setHistory] = useState(loadCallHistory);
  const [engineStatus, setEngineStatus] = useState(null);
  const [showConversation, setShowConversation] = useState(false);
  const [dtmfPreview, setDtmfPreview] = useState(null);

  // ---- live call ------------------------------------------------------

  const handleCallResolved = useCallback((record) => {
    setHistory((current) => addCallRecord(current, record));
  }, []);

  const {
    activeCall,
    elapsedSeconds,
    isPlacingCall,
    isHangingUp,
    callError,
    dial,
    hangup,
    dismissCallError,
  } = useCallSession({ onCallResolved: handleCallResolved });

  // Open the transcript as soon as the user dials (event-driven, so the
  // manual toggle stays the only other thing that changes it).
  const openConversation = useCallback(() => {
    setShowConversation(true);
  }, []);

  // ---- data -----------------------------------------------------------

  useEffect(() => {
    let cancelled = false;

    getCallContacts()
      .then((list) => {
        if (cancelled) {
          return;
        }

        setContacts(list);
        setIsOfflineSource(false);
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }

        // Backend down: keep the dashboard explorable with sample users.
        setContacts(OFFLINE_CONTACTS);
        setIsOfflineSource(true);
        console.warn("Contact list unavailable:", error.message);
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingContacts(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadStatus() {
      const status = await getCallingStatus();

      if (!cancelled) {
        setEngineStatus(status);
      }
    }

    loadStatus();

    const timer = setInterval(loadStatus, ENGINE_POLL_MS);

    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  // ---- actions --------------------------------------------------------

  const handleSelectContact = useCallback((contact) => {
    setSelectedContact(contact);
    setDialValue(contact.phone);
  }, []);

  const handleCallContact = useCallback(
    (contact) => {
      setSelectedContact(contact);
      setDialValue(contact.phone);
      openConversation();

      dial({ phone: contact.phone, contact });
    },
    [dial, openConversation]
  );

  const handleDialpadCall = useCallback(() => {
    const matchesSelection =
      selectedContact &&
      samePhone(selectedContact.phone, dialValue);

    openConversation();

    dial({
      phone: dialValue.trim(),
      contact: matchesSelection ? selectedContact : null,
    });
  }, [dial, dialValue, openConversation, selectedContact]);

  const handleRecall = useCallback(
    (record) => {
      const contact =
        contacts.find((item) =>
          samePhone(item.phone, record.phone)
        ) ||
        (record.contact_name
          ? { name: record.contact_name, phone: record.phone }
          : null);

      setDialValue(record.phone);
      setSelectedContact(contact);
      openConversation();

      dial({ phone: record.phone, contact });
    },
    [contacts, dial, openConversation]
  );

  const handleClearHistory = useCallback(() => {
    setHistory(clearCallHistory());
  }, []);

  const handleDtmfPreview = useCallback((digit) => {
    setDtmfPreview(digit);
  }, []);

  useEffect(() => {
    if (!dtmfPreview) {
      return undefined;
    }

    const timer = setTimeout(() => setDtmfPreview(null), 4000);

    return () => clearTimeout(timer);
  }, [dtmfPreview]);

  // ---- derived --------------------------------------------------------

  const visibleContacts = useMemo(() => {
    const term = search.trim().toLowerCase();

    if (!term) {
      return contacts;
    }

    return contacts.filter((contact) =>
      [contact.name, contact.phone, contact.company, contact.role]
        .filter(Boolean)
        .some((field) =>
          String(field).toLowerCase().includes(term)
        )
    );
  }, [contacts, search]);

  const engineReady = Boolean(
    engineStatus?.engine_reachable && engineStatus?.connected
  );

  const engineLabel = !engineStatus
    ? "Checking gateway..."
    : engineReady
      ? "3CX gateway connected"
      : engineStatus.engine_reachable
        ? "Gateway not connected"
        : "Calling engine offline";

  return (
    <div className="calling-shell">
      <header className="calling-header">

        <div className="calling-header-left">

          <button
            type="button"
            className="back-button"
            onClick={onNavigateHome}
            title="Back to the home screen"
          >
            ←
          </button>

          <div>

            <h1>
              AI Calling
            </h1>

            <p>
              Place outbound calls that the AI agent answers for you.
            </p>

          </div>

        </div>

        <div
          className={`connection-status ${
            engineReady ? "" : "connection-status-muted"
          }`}
        >

          <span
            className={
              engineStatus?.engine_reachable
                ? ""
                : "connection-status-dot-off"
            }
          />

          {engineLabel}

        </div>

      </header>


      <div className="calling-body">

        {/* ---------------- Users ---------------- */}

        <aside className="calling-users">

          <div className="panel-title">
            Users
          </div>

          <input
            className="calling-search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search name, number, company"
            aria-label="Search users"
          />

          <div className="calling-users-scroll">

            <ContactList
              contacts={visibleContacts}
              loading={loadingContacts}
              isOfflineSource={isOfflineSource}
              selectedId={selectedContact?.id || null}
              activePhone={activeCall?.phone || null}
              isCalling={isPlacingCall || Boolean(activeCall)}
              onSelect={handleSelectContact}
              onCall={handleCallContact}
            />

          </div>

        </aside>

        {/* ------------- Dialpad + history ------------- */}

        <main className="calling-main">

          <section className="dialpad-card">

            <div className="panel-title">
              Dialpad
            </div>

            {selectedContact && (
              <div className="dialpad-selection">

                <span>
                  Calling {selectedContact.name}
                </span>

                <button
                  type="button"
                  onClick={() => setSelectedContact(null)}
                  title="Clear selected user"
                >
                  ✕
                </button>

              </div>
            )}

            <Dialpad
              value={dialValue}
              onChange={setDialValue}
              onCall={handleDialpadCall}
              disabled={isPlacingCall || Boolean(activeCall)}
              isInCall={Boolean(activeCall)}
              onDtmfPreview={handleDtmfPreview}
            />

            {dtmfPreview && (
              <div className="dtmf-note">
                DTMF “{dtmfPreview}” recorded locally — the calling engine
                cannot receive in-call keypad digits yet.
              </div>
            )}

          </section>

          <CallHistoryList
            history={history}
            isBusy={isPlacingCall || Boolean(activeCall)}
            onRecall={handleRecall}
            onClear={handleClearHistory}
          />

        </main>


        {/* ---------------- Live call ---------------- */}

        <CallPanel
          activeCall={activeCall}
          elapsedSeconds={elapsedSeconds}
          isPlacingCall={isPlacingCall}
          isHangingUp={isHangingUp}
          callError={callError}
          engineStatus={engineStatus}
          showConversation={showConversation}
          onToggleConversation={() =>
            setShowConversation((current) => !current)
          }
          onHangup={hangup}
          onDismissError={dismissCallError}
        />

      </div>

    </div>
  );
}

export default CallingView;
