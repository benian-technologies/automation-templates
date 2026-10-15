# Check appointment availability in Google Calendar

## Quick Overview

Check a proposed appointment interval through an authenticated webhook. This workflow validates the requested times, reads Google Calendar availability, and returns a structured available or busy result. It suits booking forms, voice assistants, chat assistants, and internal scheduling tools that already have a proposed start and end time.

## How It Works

The webhook accepts a JSON body with start and end. A Code node requires complete timestamps with seconds and an explicit time-zone offset, checks that the start is in the future, and allows an interval greater than zero and no longer than 24 hours. Valid requests reach Google Calendar. A response is reported as available or busy only when the provider returns a boolean availability value. Invalid requests and unconfirmed provider results take separate response branches.

## Setup

1. Import the workflow and leave it inactive while configuring it.
2. In Receive Request, create a Header Auth credential with your chosen header name and secret value. Set a unique webhook path. Keep the secret in credentials and in your calling application, never in the workflow JSON.
3. In Check Calendar, connect your Google Calendar OAuth credential and replace YOUR_CALENDAR_ID with a calendar that credential can access. Start with a dedicated test calendar.
4. Send Content-Type: application/json and the configured authentication header. The request body needs start and end, such as {"start":"2030-01-15T14:00:00-06:00","end":"2030-01-15T14:30:00-06:00"}. Replace these example dates with a future interval you intend to test.
5. Test one free interval and one busy interval. Test invalid times and a provider permission failure. Verify that a provider failure never returns an available result.
6. Activate only after these checks, then use the production webhook URL shown by n8n.

## Requirements

An n8n installation with Webhook, Code, IF, Respond to Webhook, and Google Calendar nodes; a Google account and accessible calendar; Google Calendar OAuth credentials; and a calling application that can send an authenticated JSON POST request. No AI provider or model subscription is required.

## Customization

Change the webhook path and calendar. Add your own scheduling rules before the availability check if you need office hours, staff eligibility, lead time, buffers, or holidays. Keep the separate invalid-request and provider-error branches when adapting the workflow.

## Additional Info

HTTP 200 returns status available or busy, a boolean available, and the normalized UTC start and end. HTTP 400 returns invalid_request and validation errors. HTTP 502 returns unavailable without claiming that the interval is free. This is a snapshot for one interval. It neither generates a slot catalogue nor holds or creates an appointment. Calendar state can change after the check. Successful, error, and manual execution saving are disabled in the export; review your instance logging and retention before using real requests. Prepared by Benian Technologies: https://benian.ai/integrations/n8n-automation

## Related implementation

For adapting this pattern to your process, see [Benian's n8n implementation approach](https://benian.ai/integrations/n8n-automation?utm_source=github&utm_medium=referral&utm_campaign=automation_templates&utm_content=calendar_availability_guide).
