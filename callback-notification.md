# Email staff when a caller requests a callback

Receive an authenticated callback request, validate its fields and send a plain-text notification to a configured staff inbox through Gmail. The response distinguishes provider acceptance from an unconfirmed send.

## Setup

1. Import `callback-notification.json`. It imports inactive.
2. Configure Webhook Header Auth and a unique path on Receive Request.
3. Connect your Gmail OAuth credential to Send Staff Email. Replace `YOUR_STAFF_EMAIL` with the staff inbox that should receive notifications. The request cannot select its own recipient.
4. Listen on the test webhook and send an authenticated JSON POST, using a dedicated test inbox first:

```json
{"name":"Test Caller","phone":"+1 202 555 0142","message":"Please call me back about my appointment."}
```

Confirm actual inbox receipt before activating the production webhook. Keep authentication values in n8n Credentials and the caller's secure configuration.

## Input and responses

Name is required and limited to 120 characters. Message is required and limited to 2,000 characters. Phone may contain digits, spaces, `+`, parentheses, periods and hyphens, and must contain 7 to 15 digits. This is format validation, not verification that a number is reachable or belongs to the caller.

- HTTP 202 `accepted_by_mail_provider`: Gmail returned a nonempty message ID.
- HTTP 400 `invalid_request`: required data is missing or invalid.
- HTTP 502 `unconfirmed`: sending failed or a message ID was not returned.

A provider-accepted message is not proof of inbox delivery, staff review or a completed callback. The workflow does not call the person, create a CRM task or suppress duplicate submissions. For an uncertain send, check the sender and staff inbox before retrying. Repeated requests can generate repeated emails.

## Validation

The exact JSON imported successfully into an isolated n8n 2.41.6 container. Local synthetic checks covered request validation and receipt handling. Gmail OAuth, a real send and the authenticated webhook have not been exercised against a provider. Execution retention is disabled in the export.
