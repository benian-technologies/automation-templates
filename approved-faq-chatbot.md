# Answer website questions from approved FAQs with human handoff

Give a website visitor an answer from a small, operator-reviewed FAQ library. A language model selects relevant article IDs. The workflow returns only the exact approved answer text and its configured source links. It never renders model-written answer prose or executes a model-selected tool.

## Setup

1. Import `approved-faq-chatbot.json` into a new workflow. It is inactive and has no fixed workflow ID.
2. In **Prepare Request**, replace the three fictional FAQ records with your approved content. Keep each unique ID, title, answer and HTTPS source URL. The limit is 25 records, 1,800 characters per answer and 18,000 answer characters in total. Set the handoff instruction to your actual support route. It must not claim that a ticket has been opened.
3. Review the model in the same node, then set `enabled` to `true`. The example uses `claude-haiku-4-5-20251001`; select an available Messages API model in your account. Confirm the current provider pricing and data terms before sending real data.
4. Create a Header Auth credential for **Request Model**, with header name `x-api-key` and your Anthropic API key. Do not paste its value into a node or JSON export. The node already sets `anthropic-version: 2023-06-01` and uses the fixed HTTPS Messages endpoint.
5. Create a different Header Auth credential for **Receive Request**. Put the webhook behind your own backend with request limits. Never embed this credential in browser JavaScript. Your backend sends the authenticated POST and renders the response as text.
6. Test the documented examples with fictional data, then activate only when the input, model and support route have been reviewed. Configure your backend timeout above the workflow's 20-second provider timeout, with an appropriate user-facing failure message.

## Input

```json
{"requestId":"faq-001","question":"When is support open?","requestHuman":false}
```

`requestId` is a caller-supplied opaque ID of up to 80 letters, digits, underscores or hyphens. `question` is required and limited to 1,500 characters. `requestHuman` is optional and must be a boolean. Other fields are rejected. Do not put personal or secret information in the request ID.

## Output and boundaries

An answered response has `status: answered_from_approved_faq`, exact approved `answer` text and source objects. An empty selection or `requestHuman: true` returns `status: human_handoff`. `contactCreated` is always false. The caller must provide any separate support-contact flow.

The explicit human request bypasses the model. The model can choose up to three approved records; the workflow rejects unknown or repeated IDs and extra output fields. Selection can still be irrelevant. Test real questions, ambiguous wording and prompt-injection attempts before deployment. This is a stateless FAQ endpoint, not a conversation store, booking agent or account-access assistant.

HTTP 400 means invalid input, 503 means configuration is disabled, and 502 means the provider result could not be verified. Errors do not include raw provider responses. Automatic provider retries and redirects are disabled. Repeating a valid request can incur another model charge; the request ID is traceability, not a durable deduplication key.

Successful, failed and manual execution payload saving is disabled in the export. Review your instance, proxy and provider retention independently. The approved FAQ library and question are sent to Anthropic. No external contact, CRM record or booking is created.

## Validation state

The delivered package has exact-Code and graph tests with synthetic provider responses, including disabled configuration, explicit handoff, invented article IDs, duplicate IDs, provider errors and strict output rejection. Live Anthropic quality, latency and credentials have not been tested. Native n8n 2.41.6 also passed four fixture-graph cases: answered FAQ, explicit handoff, unknown answer and provider failure. The imported executable graph and settings were unchanged; an ephemeral workflow ID was added for the CLI. Execution tests enabled configuration and replaced ingress, provider calls and the final webhook response with synthetic fixtures. Actual processing Code and If branches ran in the native engine. The test container had no network. These checks do not establish live-provider acceptance.

References: [n8n Webhook](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/), [HTTP Request](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/), [Claude Messages API](https://platform.claude.com/docs/en/api/messages/create).

## Related implementation

Try the [runnable fictional-data walkthrough](walkthroughs/approved-faq-chatbot.md) before connecting your accounts. For adapting this pattern to your process, see [Benian's chatbot implementation approach](https://benian.ai/industries/enterprise/ai-chatbot?utm_source=github&utm_medium=referral&utm_campaign=automation_templates&utm_content=approved_faq_chatbot_guide).
