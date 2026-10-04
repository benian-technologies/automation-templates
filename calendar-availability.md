# Check appointment availability in Google Calendar

Validate a requested interval, check one Google Calendar and return a clear available or busy response. No event is created or reserved.

## Setup

1. Import `calendar-availability.json`. It imports inactive.
2. Configure a Webhook Header Auth credential and unique path on Receive Request.
3. Connect your Google Calendar OAuth credential to Check Calendar. Replace `YOUR_CALENDAR_ID` with a calendar the account can read.
4. Use a dedicated test calendar. Listen on the test webhook and send an authenticated JSON POST containing `start` and `end`, for example:

```json
{"start":"2030-01-15T10:00:00-06:00","end":"2030-01-15T10:30:00-06:00"}
```

Replace the sample with a future interval. Test free and busy periods plus a provider failure before activating the production webhook. Keep credentials in n8n Credentials, not in the JSON.

## Input and responses

Both timestamps must be real RFC3339 dates with seconds and an explicit offset or `Z`. Optional fractional seconds may have one to three digits. Start must be in the future; end must follow start, with a maximum interval of 24 hours. Valid times are normalized to UTC in the response.

- HTTP 200: `status` is `available` or `busy`, with boolean `available` and normalized start/end.
- HTTP 400: `invalid_request` with validation errors.
- HTTP 502: `unavailable` when the calendar request fails or its result is not a boolean availability answer.

Availability is a snapshot. It does not hold a slot, enforce business hours, apply appointment buffers, combine multiple calendars or guarantee a later booking will succeed.

## Validation

The exact JSON imported successfully into an isolated n8n 2.41.6 container. Local synthetic checks covered validation and response handling. Google OAuth, the live Calendar request and the authenticated webhook have not been exercised against a provider. Execution retention is disabled in the export.
