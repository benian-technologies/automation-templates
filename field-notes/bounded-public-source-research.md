# Make public-source research stop and resume predictably

A research collector needs to answer a few operational questions every time it runs: what may it fetch, what has it already fetched, how much work remains and why did it stop? A successful request loop is only one part of that job.

Benian's [public-source collection package](https://github.com/benian-technologies/automation-templates/tree/main/public-source-collector) makes those decisions in a local Python service. A separate n8n controller requests bounded batches and waits for the returned continuation time. The collector uses fixed rules and no language model.

This field note runs its real CLI against its built-in fictional documentation site. It demonstrates completed discovery imports, durable continuation, duplicate content, a deliberate budget pause and rejected configuration changes. No public website is contacted, paid discovery is launched or contact list is collected.

## Put scope and state ahead of the request loop

The collector accepts exact HTTPS origins and permitted path prefixes. Seeds, discovered links and redirect targets pass the same scope checks. The example config permits `https://docs.example.com/guides` and its descendants. It does not permit a similarly named path such as `/guides-other` or another host.

```text
Reviewed source scope and request budgets
  -> normalize seeds and completed discovery URLs
  -> persist unique URLs in a SQLite frontier
  -> check robots policy, pacing and remaining budget
  -> reserve request capacity and fetch a bounded batch
  -> extract text, deduplicate bodies and save a receipt
  -> continue with the same state, or stop with an explicit reason
```

The SQLite file holds the queue, request reservations, pacing, robots cache, documents and receipts. Configuration and transport mode are bound to that state. The local service permits one writer at a time. These choices prevent an ordinary restart from quietly resetting the work budget or changing the job's scope.

The [implementation guide](https://github.com/benian-technologies/automation-templates/blob/main/public-source-collector/README.md) describes the precise live transport restrictions. The example here stays in `offline_demo` mode throughout.

## Run the experiments without external access

Clone the [library](https://github.com/benian-technologies/automation-templates), enter its root, and use Python 3.12 or later:

```sh
python3 field-notes/collector-experiments.py
```

The [experiment runner](https://github.com/benian-technologies/automation-templates/blob/main/field-notes/collector-experiments.py) starts a fresh collector CLI process for each operation. Processes share temporary SQLite state with restricted filesystem permissions. The runner follows returned wait times, checks outcomes and removes its synthetic state when finished.

It uses the existing [demo configuration](https://github.com/benian-technologies/automation-templates/blob/main/public-source-collector/examples/config.demo.json) and [discovery fixture](https://github.com/benian-technologies/automation-templates/blob/main/public-source-collector/examples/discovery.demo.json). It does not execute the n8n controller. Temporary files are demonstration data, not a client database or an export of production research.

## Distinguish accepted rows from new URLs

The completed discovery fixture contains these three items:

```json
{
  "source": "apify-export",
  "run_id": "synthetic-completed-run",
  "status": "SUCCEEDED",
  "items": [
    {"url": "https://docs.example.com/guides/setup"},
    {"website": "https://docs.example.com/guides/setup?utm_source=fixture"},
    {"url": "https://outside.example.org/guides"}
  ]
}
```

The first import returns:

```json
{"accepted":2,"rejected":1,"replay":false}
```

The two accepted input rows normalize to the same URL. They produce one queue entry, not two. The outside origin is rejected. Importing the unchanged wrapper again returns the same counts with `replay: true`.

Next, the runner adds a different URL while retaining the same discovery run ID. The CLI exits with code 1 and its generic error message. The original unchanged import still replays successfully afterward. The implementation binds each source/run identity to its original URL list, so a changed list must not masquerade as a replay.

The wrapper's `SUCCEEDED` status is supplied by the operator. This adapter does not contact Apify to verify that status, retrieve a dataset or launch an actor. Review and provenance of a real discovery export remain outside this importer.

## Read the completed result without overstating it

After the paced ticks complete, the experiment returns these selected receipt fields:

```json
{
  "mode": "offline_demo",
  "state": "complete",
  "continue": false,
  "reason": null,
  "frontier": {"blocked":1,"done":3},
  "requests": 4,
  "pages": 3,
  "unique_documents": 2,
  "wait_seconds": 0
}
```

Three URLs produced document records. One body duplicated an earlier document, so only two unique text bodies were retained. The duplicate record preserves its URL and a `duplicate_of` pointer; its text field is empty. Consumers need to resolve that pointer rather than treating the empty text as an extraction failure.

The four requests include the robots policy request. One discovered URL was blocked by that policy and was not fetched. A repeated terminal tick returns the identical receipt. These are observed results for the fixture, not a throughput benchmark or evidence that a real website has been fully collected.

`complete` means this bounded queue is exhausted. It does not mean that every page on the source site is known, that every discovered page was retained, or that the extracted material may be republished.

## Prove that a budget really ends continuation

The next experiment uses a separate state file with `max_requests` reduced from 30 to 2. This leaves room for the robots request and one page request. The executed result includes:

```json
{
  "state": "paused",
  "continue": false,
  "reason": "request_budget",
  "frontier": {"done":1,"pending":2},
  "requests": 2,
  "pages": 1,
  "unique_documents": 1
}
```

The queue still contains work, but automatic continuation stops. Repeating the tick returns the same paused result. The runner then changes the configured maximum to 3 while keeping that state file. The command is refused. Restoring the original configuration returns the unchanged paused status.

That refusal matters operationally. A budget is part of the job definition. Quietly editing it or discarding the state would remove the context needed to explain why the run stopped. If additional collection is justified, review the receipts and define the next job deliberately.

Other limits cover pages, frontier size, depth, attempts, response size, cumulative charged bytes and job lifetime. Lifetime includes downtime. Charged bytes track the collector's request reservations and observed bodies; they are not a provider bill or a measurement of all network traffic.

## Plan for an uncertain response

An interrupted request may have reached the remote server even if the local process never recorded its response. The implementation marks interrupted reservations as `unknown` and keeps their full reserved byte charge. It can retry a GET within the remaining attempt budget.

That is at-least-once remote access. It is not an exactly-once fetch guarantee. The interrupted-request behavior is explained in the source and covered by the package's existing tests; the CLI experiment in this field note does not simulate a process crash.

If n8n loses a batch response, the operator should read the collector's status using the same state and configuration before deciding to continue. The [controller setup](https://github.com/benian-technologies/automation-templates/blob/main/public-source-collector/README.md#connect-n8n) explains the authenticated loopback service and its network arrangement. The supplied controller cannot reach that local service from n8n Cloud without a different deployment design.

## Decide what happens to the collected material

For a real installation, agree the permitted content paths, operator identity, retention and destination before enabling live mode. Public availability and robots permission do not independently establish reuse rights. The collector does not automatically identify or redact personal information, so source selection is part of the implementation.

The parser extracts HTML text and links without executing JavaScript. It does not render browser applications, sign in, pass login walls, collect PDFs or bypass access controls. A conservative robots policy can block collection on an uncertain response. These limits should be visible in the research plan, rather than discovered only when a report is incomplete.

The output is collected material. Turning it into an article is another process. The [cited editorial field note](https://github.com/benian-technologies/automation-templates/blob/main/field-notes/cited-editorial-review.md) shows one review pattern, but the templates are not preconnected. Someone still needs to choose excerpts, check their meaning and approve the final text.

Start by running the offline experiment and inspecting the paused result. Then decide what the next person in your operation needs to see: the source scope, current queue state, collected documents, duplicate references and reasons for stopping. That handoff is as useful as the collection loop itself.

Related: [Benian's n8n implementation approach](https://benian.ai/integrations/n8n-automation?utm_source=github&utm_medium=referral&utm_campaign=implementation_field_notes&utm_content=bounded_source_research).

Produced by AI agents and checked against the published collector code. The experiments use its fixed fictional transport; no client or live-source outcome is claimed. [Validation scope](https://github.com/benian-technologies/automation-templates/blob/main/VALIDATION.md).
