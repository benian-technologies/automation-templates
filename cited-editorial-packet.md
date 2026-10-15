# Build a cited editorial review packet from approved sources

Turn a topic and a bounded set of approved source excerpts into an editorial outline with supporting quotes. Each proposed point carries an exact excerpt quote and the source URL. An editor receives a structured packet and a plain-text review version, rather than an automatically published article.

## Setup

1. Import `cited-editorial-packet.json` into a new inactive workflow. It has no fixed workflow ID.
2. In **Prepare Request**, choose an available Anthropic Messages model and set `enabled: true`. Bind an n8n Header Auth credential named `x-api-key` to **Request Model**. The example model is `claude-haiku-4-5-20251001`. API charges and provider data processing apply.
3. Bind a separate Header Auth credential to **Receive Request**. Only your trusted backend or an authorized operator should call it. Apply rate limits outside the workflow. Do not put the webhook credential in a public page.
4. Use source material you have permission to process. Review the sources before setting `sourceUseApproved: true`. The boolean is an assertion by the authenticated caller, not an independent rights check. Keep source excerpts short and relevant.
5. Send a synthetic fixture first. Save the successful response in your chosen editorial system or present it to an editor. This template returns the packet; it does not persist a review queue or approve, schedule or publish content.

## Input

```json
{
  "requestId":"editorial-001",
  "topic":"Make small-business onboarding clearer",
  "sourceUseApproved":true,
  "sources":[{
    "id":"source-one",
    "title":"Fictional onboarding guide",
    "url":"https://example.com/onboarding-guide",
    "excerpt":"A written scope gives the team a shared reference. Assign a named reviewer before implementation begins."
  }]
}
```

Limits: topic 300 characters; 1-10 unique source IDs and URLs; source title 200 characters; each excerpt 20-6,000 characters; all excerpts together at most 24,000 characters. IDs allow letters, digits, underscores and hyphens, up to 80 characters. URLs must be HTTPS. Extra fields and repeated source IDs/URLs are rejected.

The workflow never fetches a supplied URL. A collector can supply this normalized input after its own access, rate-limit and rights checks. A URL proves neither authorship nor truth.

## Result and review

The response contains `status: needs_editor_review`, a headline, angle, 1-5 sections, cited points and `reviewText`. Each point must name a supplied source and quote a literal substring from it. Unknown references, invented quotes, malformed JSON and truncated model output fail closed.

Exact quote matching checks traceability, not whether the surrounding claim is justified. An editor still checks meaning, source reliability, freshness, wording, copyright and fit. Render `reviewText` and other strings as text, never unsanitized HTML. Source excerpts can contain hostile instructions; the model is instructed to ignore them, but human review remains necessary.

No publication endpoint, media upload, email or social action exists in this workflow. The output is not approved content. If moving it into a publication workflow, an editor must separately approve the exact final title and paragraphs.

HTTP 400 means invalid input, 503 means disabled setup and 502 means unverified provider output. There are no automatic retries or redirects. Repeated requests can cause repeated API charges. Execution payload saving is disabled in the export; review other logging/retention separately.

## Validation state

Synthetic exact-Code and whole-graph tests cover valid packets, duplicate sources, unsafe URL schemes, missing approval, excessive input, forged quotes, invented source IDs, provider errors and malformed/truncated outputs. No live model, source collector, editorial storage or publication integration has been tested by this package. Native n8n 2.41.6 also passed three fixture-graph cases: valid packet, forged-quote rejection and missing-approval rejection. The imported executable graph and settings were unchanged; an ephemeral workflow ID was added for the CLI. Execution tests enabled configuration and replaced ingress, provider calls and the final webhook response with synthetic fixtures. Actual processing Code and If branches ran in the native engine. The test container had no network. These checks do not establish live-provider acceptance.

References: [Claude Messages API](https://platform.claude.com/docs/en/api/messages/create), [n8n HTTP Request](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/).

## Related implementation

Try the [runnable fictional-data walkthrough](walkthroughs/cited-editorial-packet.md) before connecting your accounts. For adapting this pattern to your process, see [Benian's AI agents and workflows approach](https://benian.ai/compare/ai-agents-vs-workflows?utm_source=github&utm_medium=referral&utm_campaign=automation_templates&utm_content=cited_editorial_packet_guide).
