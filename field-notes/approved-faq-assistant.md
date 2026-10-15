# Build a support assistant that can decline to answer

A support assistant needs a clear contract with the business: which answers it may give, which decisions belong to a person, and what happens when it cannot verify a response. Those decisions are part of implementation. A model subscription does not settle them.

At Benian, we published a small n8n example that makes one version of that contract inspectable. The model selects records from a reviewed FAQ library. Code supplies the answer text and source links. An empty selection returns instructions for reaching a person.

The useful part is the boundary you can test. The example rejects an invented FAQ ID, but it can still return an irrelevant answer when the model selects a real ID. Both behaviors are demonstrated below. Understanding that difference helps a team decide what it must validate before exposing a chatbot to customers.

This is a fictional support example, not a client case study. The support hours and source URLs belong to the demonstration. No live model-quality or customer-outcome claim is made.

## Give the model a small, explicit job

The [published workflow](https://github.com/benian-technologies/automation-templates/blob/main/approved-faq-chatbot.json) has two important Code nodes: **Prepare Request** and **Validate Model Output**. Between them sits a fixed provider request. The model cannot choose another tool or endpoint.

```text
Authenticated backend request
  -> validate setup, question and FAQ library
  -> explicit person request? Return handoff instructions
  -> otherwise ask model to select up to three article IDs
  -> validate returned IDs
       known IDs: return exact stored answers and source links
       empty list: return handoff instructions
       invalid result: return unavailable
```

Each configured article contains an ID, title, approved answer and HTTPS source URL. The model sees the question and those records. Its requested output is only:

```json
{"articleIds":["hours"]}
```

The validator rejects extra fields. Even if the model returns its own `answer` alongside a valid ID, that result is refused. This keeps the visible answer within the reviewed library. Source URLs also come from configuration, so the model does not invent citations.

That design fits a small, stable FAQ. The export accepts at most 25 records, with limits on individual and combined answer length. A large permissioned document corpus needs a different retrieval and access design. This starter does not implement one.

## Run the actual decision code

Clone the [public library](https://github.com/benian-technologies/automation-templates), enter its directory, and use Node.js 22 or later:

```sh
node field-notes/replay.cjs faq
```

The [runner](https://github.com/benian-technologies/automation-templates/blob/main/field-notes/replay.cjs) reads the two Code nodes from the exported workflow. It enables the disabled configuration in memory and supplies fictional provider responses. It does not change the workflow file, call a provider, or execute n8n's complete graph. No credentials are required.

The [input fixture](https://github.com/benian-technologies/automation-templates/blob/main/field-notes/examples/faq-request.json) is:

```json
{
  "requestId": "field-note-faq-001",
  "question": "When is support open?",
  "requestHuman": false
}
```

When the fictional provider response selects `hours`, the executed validator returns HTTP 200 and this result object:

```json
{
  "requestId": "field-note-faq-001",
  "status": "answered_from_approved_faq",
  "answer": "Our fictional demonstration support team is available Monday through Friday, 09:00 to 17:00 UTC.",
  "sources": [
    {
      "id": "hours",
      "title": "Support hours",
      "url": "https://example.com/support"
    }
  ],
  "contactCreated": false
}
```

The assertion checks that the answer equals the stored article text. This establishes the output boundary for that fixture. It does not measure whether a live model usually chooses the right article.

## Make declining to answer a normal result

For the fictional provider output `{"articleIds":[]}`, the same validator returns:

```json
{
  "requestId": "field-note-faq-001",
  "status": "human_handoff",
  "answer": "This needs a person to review it. Please use the support contact shown on the website. This chat has not created a support request.",
  "sources": [],
  "contactCreated": false
}
```

The same response is available without a model call when the visitor explicitly sets `requestHuman: true`. The input and configuration are still validated first.

This distinction affects the customer experience. A request for a person can route immediately. A valid but empty model selection can explain the next step. An invalid provider response returns HTTP 502 with `status: unavailable`. The frontend needs to handle all three states deliberately.

The name `human_handoff` deserves attention: in this template it means **instructions for contacting support**. It does not mean a ticket exists, an employee was notified, or someone accepted the work. `contactCreated: false` makes that explicit. If the operation requires a ticket, implement that action separately and verify its receipt before telling the visitor it was created.

## Test the failure the schema cannot detect

The runner includes eight cases:

| Fictional input or provider behavior | Observed result |
|---|---|
| Select the approved `hours` record | 200, exact stored answer |
| Select no record | 200, handoff instructions |
| Visitor requests a person | 200, handoff instructions; model bypassed |
| Invent an article ID | 502, unavailable |
| Repeat the same article ID | 502, unavailable |
| Add an `answer` field to the model output | 502, unavailable |
| Select `hours` for an account-address question | 200, irrelevant stored answer |
| Leave the export disabled | 503, setup required |

The account-address case is intentional. The question asks to change an account address, but the fictional model returns the real ID `hours`. The schema accepts it and the visitor receives support hours.

The output is approved text, but it does not answer the question. The prompt asks for an empty list when no record applies; code cannot prove the model followed that semantic instruction. The test exposes a limitation rather than hiding it behind a successful status code.

Before launch, build a reviewed question set containing ordinary questions, ambiguous phrasing, account-specific requests and attempts to override instructions. Record the expected article or handoff decision for each. Test the live model against those expectations. Review wrong answers separately from successful abstentions. A high answer rate can be a poor result if it includes confident mismatches.

## Fit the workflow to the support operation

Three implementation decisions sit outside this starter.

**Who owns the answer library?** Assign an owner for policies, links and changes. If the support hours change, the stored answer needs review. If a policy depends on an authenticated account, a generic FAQ should not turn that policy into an account-specific decision.

**What completes the handoff?** Choose an actual support destination and make it usable. If a separate system creates a request, keep its success, failure and uncertain outcomes distinct. The assistant should reflect the verified result of that system.

**What happens on retries?** The request ID supports traceability. It is not a stored deduplication key. Repeating a valid request may produce another provider call and charge. The backend needs its own timeout, rate limit and retry behavior. The export disables automatic provider retries and redirects; it does not supply an application-wide retry policy.

The [setup guide](https://github.com/benian-technologies/automation-templates/blob/main/approved-faq-chatbot.md) explains separate webhook and provider credentials. Keep the webhook secret in a backend, render returned strings as text, and review retention across the proxy, n8n instance and provider. The configured FAQ records and question are sent to the model provider when the model branch runs.

The workflow is stateless. It does not supply employee identity, document permissions, account lookup, conversation storage or booking. Those are separate implementation responsibilities when a business needs them.

## Use the example to make one concrete decision

Take five questions your support team answers repeatedly and five it should hand to a person. Write the expected response before changing the template. Then run the fixtures, replace the fictional library with reviewed material, and test the real provider in your own account. Keep the workflow inactive until the backend and support destination behave as expected.

Benian is an [AI implementation partner](https://benian.ai/industries/enterprise/ai-chatbot?utm_source=github&utm_medium=referral&utm_campaign=implementation_field_notes&utm_content=approved_faq_assistant). These decisions are the work: map the process, build around the business's rules, validate the boundaries and train the team to run the result. The downloadable starter makes that work easier to inspect; adapting it still requires an owner for the operation.

Produced by AI agents and checked against the exported workflow. The examples execute its Code nodes with fictional inputs and provider responses. This is not a statement of personal client experience. [Validation scope and limitations](https://github.com/benian-technologies/automation-templates/blob/main/VALIDATION.md).
