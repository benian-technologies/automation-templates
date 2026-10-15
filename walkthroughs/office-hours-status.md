# Give a receptionist an exact answer about business hours

“We close at five” hides several decisions. Is five o'clock still open? What happens during lunch, after midnight or on a closure date? This small n8n endpoint makes those rules explicit without asking a language model to calculate the schedule.

## Demonstrate the boundaries

From the [cloned library](README.md), with Node.js 22 or later:

```sh
node walkthroughs/run-workflow-demo.cjs office
```

The runner executes **Compute Office Status** from the published workflow. A fixed clock and fictional `America/Chicago` schedule are supplied only by the local harness. The actual webhook always uses the server's current clock; callers cannot override the time through its body.

| Local example | Expected status |
|---|---|
| Monday 08:59, opening at 09:00 | Closed |
| Monday 09:00 | Open |
| Monday 12:00, lunch until 13:00 | Closed |
| Monday 13:00 | Open |
| Monday 17:00, closing at 17:00 | Closed |
| Monday 09:00 on a configured closure date | Closed |
| Wednesday 01:59 after Tuesday's 22:00-02:00 interval | Open |
| Wednesday 02:00 | Closed |
| Wednesday 01:59 when Tuesday was a closure date | Closed |

The program checks each expected result and prints the local date, day, time and status. The overnight example is particularly useful: the interval belongs to Tuesday, even though part of it occurs on Wednesday.

## Configure the endpoint

Import [office-hours-status.json](../office-hours-status.json) into a new workflow. In **Configure Office**, set the real IANA time zone, weekly intervals and closure dates. Empty intervals mean closed. Use two intervals for a lunch break and an end earlier than its start for an overnight shift. Equal start/end times are invalid.

Bind a Header Auth credential to **Receive Request**, then test an authenticated request using n8n's test webhook. Keep the secret in the calling backend or voice platform's secure settings. The response describes hours; it does not show staff presence, book an appointment or transfer a call. The [complete setup guide](../office-hours-status.md) explains the response and retention settings.

Before production, test the actual webhook, your zone's daylight-saving transition where applicable and your business's closure policy. The nine fixed-clock examples above are Code-node checks, not a complete timezone test suite or a live authenticated webhook test.

## Use the result in a conversation

When `office_is_open` is true, the receptionist can follow your open-hours policy. When false, it can explain the next appropriate route. Keep that downstream behavior separately configured and tested. The [callback notification template](../callback-notification.md) is one possible next step when a caller explicitly requests a callback, but it is not wired into this endpoint automatically.

For implementation and acceptance around a real receptionist, see [Benian's n8n implementation approach](https://benian.ai/integrations/n8n-automation?utm_source=github&utm_medium=referral&utm_campaign=automation_templates&utm_content=office_hours_walkthrough).
