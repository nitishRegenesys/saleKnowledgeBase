/**
 * Offline fallback for the contact list.
 *
 * The dashboard reads its users from `GET /api/v1/calls/contacts`
 * (app/api/routes/calls.py -> MOCK_CALL_CONTACTS). These few records are only
 * used when that endpoint cannot be reached (backend not running), so the
 * dashboard is still explorable — they are flagged as samples in the UI.
 */
export const OFFLINE_CONTACTS = [
  {
    id: "offline-1",
    name: "Thandi Nkosi",
    phone: "0734567891",
    company: "Meridian Retail",
    role: "Procurement Lead",
    status: "warm",
  }
];
