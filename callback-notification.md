# Email staff when a caller requests a callback

## Quick Overview

Turn an authenticated callback request into a plain-text email to a fixed staff inbox. This workflow validates the caller name, phone number, and message, sends through Gmail, and returns a distinct response for mail-provider acceptance, invalid input, or an unconfirmed send.

## How It Works

A webhook receives a JSON POST request. A Code node trims and validates name, phone, and message before any email is sent. The Gmail node sends the formatted request to the staff address configured by the workflow owner. The workflow returns HTTP 202 only when Gmail returns a nonempty message ID. Provider errors and malformed acceptance results return HTTP 502 so the calling system does not mistake uncertainty for confirmed acceptance.

## Setup

1. Import the workflow and leave it inactive while configuring it.
2. In Receive Request, create a Header Auth credential with your chosen header name and secret value. Set a unique webhook path. Store the authentication secret in credentials and in your calling application, never in the workflow JSON.
3. In Send Staff Email, connect your Gmail OAuth credential and replace YOUR_STAFF_EMAIL with the receiving staff inbox. Use a test sender and test inbox first. The recipient is fixed in the node; it is not taken from caller input.
4. Send Content-Type: application/json and the configured authentication header. A synthetic body is {"name":"Alex Example","phone":"+1 202-555-0147","message":"Please call me back about scheduling."}.
5. Test valid input, a missing message, an invalid phone number, and a Gmail permission failure. For the valid case, verify actual receipt in the test inbox separately from the HTTP response.
6. Activate only after these checks, then switch your calling application to the production webhook URL shown by n8n.

## Requirements

An n8n installation with Webhook, Code, IF, Respond to Webhook, and Gmail nodes; a Google account able to send through Gmail; Gmail OAuth credentials; a receiving staff inbox; and a calling application that can send an authenticated JSON POST request. No voice or AI provider is required.

## Customization

Set the receiving staff address and email subject. Adapt the plain-text message to your team process. Add persistent request IDs and a deduplication store before enabling automatic retries or multiple delivery paths. Keep the recipient controlled by the workflow owner and preserve the explicit provider-acceptance check.

## Additional Info

The name is required and limited to 120 characters. Phone accepts common formatting characters and requires 7 to 15 digits; this is a format check, not proof that a number is reachable. The message is required and limited to 2,000 characters. HTTP 202 returns accepted_by_mail_provider. It does not confirm delivery, reading, or a completed callback. HTTP 400 returns invalid_request and validation errors. HTTP 502 means acceptance is unconfirmed: inspect the sender and staff inbox before retrying, because the first attempt may have sent. The template has no persistent deduplication, makes no call, and sends no customer receipt. Execution saving is disabled in the export, but Gmail stores sent messages and your instance may keep other logs. Review data handling and retention before using real caller information. Prepared by Benian Technologies: https://benian.ai/integrations/n8n-automation
