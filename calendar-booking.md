# Book confirmed appointments in Google Calendar

Validate a confirmed request, check one calendar and create a private event when the requested interval is available. The workflow checks the creation response before reporting a booking.

## Setup

1. Import `calendar-booking.json`. It imports inactive.
2. Configure Webhook Header Auth and a unique path on Receive Request.
3. Select your Google Calendar OAuth credential on both Check Calendar and Create Appointment. Replace `YOUR_CALENDAR_ID` in both nodes with the same calendar the account can read and write.
4. Start with a dedicated test calendar. Send an authenticated JSON POST with a future interval:

```json
{"start":"2030-01-15T10:00:00-06:00","end":"2030-01-15T10:30:00-06:00","summary":"Consultation","request_id":"0123456789abcdef0123456789abcdef","confirmed":true}
```

Generate a unique `request_id` for each intended appointment and retain it for retries of that appointment. Never reuse the sample ID for unrelated bookings. Verify successful, busy, invalid and uncertain-result cases before activation.

## Input and behavior

Start and end must be real RFC3339 timestamps with seconds and an explicit offset or `Z`. Start must be in the future, and the interval must be positive and no longer than 24 hours. Summary is required and limited to 160 characters. `confirmed` must be the boolean `true`. The request ID must contain 16 to 64 characters from lowercase `a` through `v` or digits.

A successful HTTP 201 response reports `booked`, appointment ID and normalized times only when Google's create response contains the expected event ID, `confirmed` status and matching interval. This verifies the creation response; it does not perform a separate event readback. The event is private, blocks the calendar and has no guests or configured default reminders.

Invalid requests return HTTP 400. A busy interval returns HTTP 409. Calendar-check failures return HTTP 502 `unavailable`; failed or mismatched creation responses return HTTP 502 `unconfirmed`.

## Concurrency and retries

Availability checking and creation are separate operations. Serialize all writers to that calendar if overlapping bookings are unacceptable. The template does not provide a distributed lock or enforce business hours and buffers.

A repeated successful request may return busy because its event now occupies the interval. The request ID is used as the event ID, but the workflow does not automatically resolve an earlier result. After an uncertain response, look up that ID in the calendar before retrying. Do not treat a timeout as proof that no event was created.

## Validation

The exact JSON imported successfully into an isolated n8n 2.41.6 container. Local synthetic checks covered validation and response handling. Google OAuth, live event creation and the authenticated webhook have not been tested against a provider. Execution retention is disabled in the export.
