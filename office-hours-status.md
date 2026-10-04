# Check business hours for an AI receptionist

Return the current open or closed status from a weekly schedule, a local time zone and date-specific closures. The authenticated webhook can serve a voice assistant, chatbot or other workflow. It uses n8n only.

## Setup

1. Import `office-hours-status.json`. It imports inactive.
2. In Receive Request, select a Webhook Header Auth credential and choose a unique webhook path. Keep the header value in n8n Credentials and in the calling system's secure configuration.
3. In Configure Office, replace `YOUR_TIME_ZONE` with an IANA time zone such as `America/Chicago`. Replace the sample weekly hours with your actual hours. Each weekday takes an array of `[start, end]` intervals; an empty array is closed.
4. Add closure dates as `YYYY-MM-DD` strings in `closed_dates`.
5. Listen on the test webhook and send an authenticated POST with `{}` as its JSON body. Check the configured boundary and closure cases before activating a production webhook.

## Behavior and limits

Hours use 24-hour `HH:MM` format. Opening time is inclusive and closing time exclusive. Multiple intervals support lunch breaks. An interval such as `['22:00','02:00']` continues into the next day; equal start and end times are invalid. A closure on the current date overrides all hours, and a closure on the previous date prevents its overnight interval from carrying forward.

The result includes `status`, `office_is_open`, local date/day/time, time zone, today's configured intervals and the closure flag. The workflow uses the current n8n server clock interpreted in the configured zone. Request-body timestamps do not override it. It does not retrieve holidays, check staff presence, transfer calls or find appointments.

## Validation

The exact JSON imported successfully into an isolated n8n 2.41.6 container. Earlier local synthetic checks covered schedule logic; a live authenticated webhook integration has not been tested. No external provider is required. Execution retention is disabled in the export; choose settings appropriate to your deployment.
