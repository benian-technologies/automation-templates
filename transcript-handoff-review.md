# Extract evidence-linked decisions and actions from a meeting transcript

Prepare a participant-review handoff from a transcript you are authorized to process. The result separates decisions, proposed actions and open questions. Every item points to an exact segment and quote. Owners and due dates remain proposed until a person confirms them.

## Setup

1. Import `transcript-handoff-review.json` into a new inactive workflow. It has no fixed workflow ID.
2. Select an available Anthropic Messages model in **Prepare Request** and set `enabled: true`. Bind an n8n Header Auth credential with header name `x-api-key` to **Request Model**. Model processing and charges apply.
3. Protect **Receive Request** with a different Header Auth credential. Call it from a trusted backend or operator, with external request limits. The credential must not be shipped to browsers.
4. Verify that you may send the transcript to the provider. Remove unnecessary personal or confidential information and resolve uncertain speaker labels before setting `processingApproved: true`.
5. Test a fictional meeting. Present the returned packet to participants. Only after confirmation should another system create tasks or send a client handoff.

## Input

```json
{
  "requestId":"handoff-001",
  "meetingId":"demo-meeting",
  "processingApproved":true,
  "participants":[{"id":"alex","name":"Alex"}],
  "segments":[{"id":"s1","speakerId":"alex","text":"I will write the acceptance checklist by 2026-10-20."}]
}
```

Use opaque request and meeting IDs of up to 80 letters, digits, underscores or hyphens. Limits: 1-12 participants with distinct IDs and names; 1-100 segments with unique IDs; each segment at most 2,000 characters; combined transcript at most 30,000 characters. Every speaker ID must resolve to a supplied participant. Extra fields are rejected. Disambiguate participants with the same name before calling this workflow.

## Result and limitations

The response has `status: needs_participant_review`, decisions, actions and open questions. Each includes a segment ID and exact quote. An action has `proposedOwner`, `proposedDueDate` and `confirmation: required`. A missing owner or date stays null.

An owner is accepted only if the supporting quote names that participant, or if that participant is the recorded speaker and the quote contains a first-person “I”. A date is accepted only if the literal valid ISO date appears in the quote. Relative dates are left unknown. These checks limit unsupported extraction; they do not prove a commitment or solve speaker-attribution errors. Participants must verify interpretation and responsibility.

No task, email, CRM record or Notion page is created. `tasksCreated` and `messagesSent` are zero. The complete bounded transcript goes to Anthropic; this is not a local transcription service. Model output is untrusted and should be rendered as text. No automatic retries or redirects are enabled, and execution payload saving is disabled in the export. Check the instance and provider retention separately.

HTTP 400 means invalid input, 503 means disabled setup and 502 means the provider response failed validation. Repetition can incur another API charge; request IDs are not persistent deduplication.

## Validation state

Exact-Code and whole-graph tests use synthetic transcripts and model responses. Cases include unsupported participants, repeated segment IDs, missing processing approval, forged quotes, invented owners/dates, null values and malformed/provider error responses. Live model quality and participant acceptance remain untested. Native n8n 2.41.6 also passed three fixture-graph cases: valid handoff, unknown-owner rejection and partial-name rejection. The imported executable graph and settings were unchanged; an ephemeral workflow ID was added for the CLI. Execution tests enabled configuration and replaced ingress, provider calls and the final webhook response with synthetic fixtures. Actual processing Code and If branches ran in the native engine. The test container had no network. These checks do not establish live-provider acceptance.

References: [Claude Messages API](https://platform.claude.com/docs/en/api/messages/create), [n8n Webhook](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/).
