import { getInitials } from "../../utils/format";

/**
 * The "users" list the dashboard dials from: searchable, click to load the
 * number into the dialpad, or call directly.
 */
function ContactList({
  contacts,
  loading,
  error,
  isOfflineSource,
  selectedId,
  activePhone,
  isCalling,
  onSelect,
  onCall,
}) {
  if (loading) {
    return (
      <div className="panel-empty">
        Loading users...
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel-empty panel-empty-error">
        {error}
      </div>
    );
  }

  if (contacts.length === 0) {
    return (
      <div className="panel-empty">
        No users to call yet.
      </div>
    );
  }

  return (
    <>
      {isOfflineSource && (
        <div className="panel-note">
          Backend unreachable — showing sample users.
        </div>
      )}

      <div className="contact-list">

        {contacts.map((contact) => {
          const isActive =
            Boolean(activePhone) &&
            contact.phone.replace(/\D/g, "") ===
              activePhone.replace(/\D/g, "");

          return (
            <div
              key={contact.id}
              className={`contact-item ${
                selectedId === contact.id
                  ? "contact-item-selected"
                  : ""
              } ${isActive ? "contact-item-active" : ""}`}
              onClick={() => onSelect(contact)}
            >

              <div className="contact-avatar">
                {getInitials(contact.name)}
              </div>

              <div className="contact-details">

                <div className="contact-name">
                  {contact.name}
                </div>

                <div className="contact-phone">
                  {contact.phone}
                </div>

                <div className="contact-meta">
                  {contact.company}
                  {contact.role
                    ? ` · ${contact.role}`
                    : ""}
                </div>

              </div>

              <div className="contact-side">

                {contact.status && (
                  <span
                    className={`contact-tag contact-tag-${contact.status}`}
                  >
                    {contact.status}
                  </span>
                )}

                <button
                  type="button"
                  className="contact-call-button"
                  onClick={(event) => {
                    event.stopPropagation();
                    onCall(contact);
                  }}
                  disabled={isCalling}
                  title={`Call ${contact.name}`}
                >
                  {isActive ? "●" : "📞"}
                </button>

              </div>

            </div>
          );
        })}

      </div>
    </>
  );
}

export default ContactList;
