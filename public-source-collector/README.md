# Public page discovery and collection

A complete, local collection service and n8n controller for an explicitly permitted set of public HTML pages. It discovers links inside configured boundaries, saves a durable queue, and continues in paced batches until the queue is exhausted or a budget stops it.

This is a clean reusable adaptation of a larger discovery and enrichment pipeline. It includes an optional importer for completed Apify exports. It does not launch paid actors, select commercial audiences, harvest contact details, verify leads or send outreach.

## Included files

- `collector.py`: validation, URL normalization, robots policy, fixed HTTPS GET transport, SQLite frontier, request reservations, content deduplication, discovery import and receipts.
- `serve.py`: authenticated loopback controller for one configured job.
- `workflow.json`: manual n8n controller with seven executable nodes and setup notes.
- `examples/`: entirely synthetic configuration and completed discovery export.
- `tests/`: synthetic policy, failure, continuation, local TLS, local HTTP and workflow tests.
- `build_workflow.py`: reproducible workflow export generator.

Python 3.12 or later on macOS or Linux is required. The service uses only the Python standard library. Tests also use Node.js 22 or later and OpenSSL. The workflow is designed for self-hosted n8n, tested with n8n 2.41.6. It requires the service to share its host or network namespace. An n8n Cloud instance cannot access this loopback service as supplied.

## Run the offline demo

The default transport serves a small in-memory documentation site. It opens no web connections. The demo's `permission_confirmed: true` applies only to its synthetic source.

From this package directory:

```sh
mkdir -m 700 .runtime
python3 collector.py plan --config examples/config.demo.json --state .runtime/demo.sqlite
python3 collector.py discover --config examples/config.demo.json --state .runtime/demo.sqlite --input examples/discovery.demo.json
python3 collector.py tick --config examples/config.demo.json --state .runtime/demo.sqlite
python3 collector.py status --config examples/config.demo.json --state .runtime/demo.sqlite
```

Repeat `tick` after the returned `wait_seconds`, or use the n8n workflow below. A completed demo has three collected page URLs, two unique document bodies, one robots-blocked URL and four total requests including robots. The optional discovery import changes queue ordering, not those final totals. Repeating its stable source/run ID and same URL list returns a replay receipt. Changing that list under the same ID is refused. Accepted import counts count in-scope input rows; duplicate rows do not create duplicate queue entries.

## Connect n8n

Generate a controller token directly into a private file. The command does not print its value:

```sh
python3 - <<'PY'
import os, secrets
fd = os.open('.runtime/controller.token', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as f:
    f.write(secrets.token_hex(32))
PY
python3 serve.py --config examples/config.demo.json --state .runtime/demo.sqlite --token-file .runtime/controller.token
```

1. Import `workflow.json` through n8n's workflow import UI. It has no instance-specific ID and imports inactive. Inspect the seven nodes before execution.
2. Create a local Header Auth credential. Header name is `Authorization`; its value is `Bearer ` followed by the private token, transferred through your own secure local credential UI. Restrict the credential to `127.0.0.1` if the n8n version exposes allowed-domain controls. Never place the value in a Code node or export it.
3. Select that credential on **Collect bounded batch**. The node calls the included service at `http://127.0.0.1:8787/v1/tick`.
4. Confirm **Select collection job** matches the service's `job_id`. Run manually. The workflow validates each receipt, waits, and continues until a final receipt returns.

The service binds only to `127.0.0.1`. A container's loopback is its own network namespace. Run the service and n8n on the same host or deliberately place them in the same isolated namespace. Merely running Python on a Docker host does not make its loopback available inside a normal n8n container. Do not change the service to a public bind to work around this requirement.

The HTTP node uses a three-minute timeout, no automatic retries and no redirects. A batch admits at most ten serial pages. Each live request has a child-process timeout of at most ten seconds, covering DNS, TLS, headers and body, with child termination and reaping. The service uses a five-second socket read timeout for incoming requests. Successful/error/manual execution data persistence is disabled in the exported workflow; n8n can still retain operational execution metadata and in-progress Wait state. It receives aggregate receipts, not page bodies.

## Configure permitted public sources

Copy the demo config to a private working file. Select only sources and content paths that you have permission to collect and retain. Set `permission_confirmed` to true after that review. A public URL and a permissive robots file do not themselves grant reuse rights.

- `origins` maps exact HTTPS origins to allowed path prefixes. `/guides` permits that path and its descendants, not `/guides-other`. No wildcard hosts, IP URLs, credentials, alternate ports or HTTP downgrade.
- `seeds` starts the frontier. Discovered links and redirect targets must pass the same scope checks. Redirects become queued work with their own robots checks, not transparent requests.
- `query_keys` is an explicit allowlist. Unknown query keys and repeated keys are rejected. Known tracking parameters are dropped. Fragments and default port 443 are removed; unreserved percent encodings are normalized. Ambiguous encoded separators, nested percent encodings and dot segments are refused.
- `contact_url` becomes part of the honest `PublicPageCollector` user-agent. Supply an informational page for your operator identity before live use.
- `limits` bounds requests, collected page URLs, frontier URLs, depth, attempts, body bytes, wall-clock job lifetime, pacing and batch size. Hard upper bounds are enforced in code.

Use a fresh private SQLite path for a new config or transport mode. Its containing directory must belong to the current user with mode `0700`; the SQLite file is mode `0600`. Config and mode are bound to its state; changing them in place is refused. A live command must include `--live` explicitly:

```sh
python3 collector.py plan --config .runtime/permitted-source.json --state .runtime/live.sqlite --live
python3 serve.py --config .runtime/permitted-source.json --state .runtime/live.sqlite --token-file .runtime/controller.token --live
```

No live source is enabled by this package. There are no provider tokens, paid API calls, proxy options, cookies, browser sessions or authentication headers in the collection transport. DNS answers must all be globally routable. The connection pins a validated IP and verifies TLS against the original hostname, avoiding a second DNS lookup and ignoring environment proxy settings. Outbound redirects cannot escape the allowlist.

## Robots and content policy

The collector fetches `/robots.txt` on each allowed origin before its pages. It merges exact `PublicPageCollector` groups, falls back to `*`, supports longest-match rules, wildcard `*`, end anchor `$`, allow ties, and a conservative crawl-delay extension. It caches successful policy for up to 24 hours.

This is a deliberately conservative implementation profile, not a claim of complete RFC conformance. Only robots 404/410 are treated as missing. Other errors, redirects, non-text responses and transport failures block page fetches. The robots response must fit the configured body limit. Site-specific encoding or nonstandard directives may require an explicitly reviewed extension; there is no bypass flag.

The HTML parser extracts a bounded title, visible text and links without running JavaScript. It omits script/style/noscript/SVG text, honors page-level meta `noindex`/`nofollow` and link `rel=nofollow`, and stores one text body for identical extracted content. It is not a browser renderer or an automatic personal-data/redaction system. Choose content paths accordingly. PDF, browser rendering, login walls, CAPTCHA handling, paywalls and custom extraction schemas are not implemented.

References: [Robots Exclusion Protocol](https://www.rfc-editor.org/rfc/rfc9309.html), [Python HTTP client](https://docs.python.org/3/library/http.client.html), [n8n workflow export and import](https://docs.n8n.io/build/manage-workflows/export-and-import.md).

## Completed-export discovery

The optional local importer accepts this wrapper:

```json
{
  "source": "apify-export",
  "run_id": "your-completed-run-id",
  "status": "SUCCEEDED",
  "items": [{"url": "https://docs.example.com/guides"}]
}
```

`website` is also accepted as a URL field. Other item fields are ignored and never copied into the collector. This wrapper is an operator-supplied assertion about a completed export; the adapter does not contact Apify to certify run status or retrieve datasets. No paid discovery is launched. Import only an export you may use, before starting the job. Use a new stable source/run ID for a distinct completed export. There is no automatic commercial targeting or geography expansion.

## Durable state and honest results

SQLite retains the normalized frontier, per-origin pacing/robots cache, documents, discovery receipts, request reservations and the latest 1,000 distinct batch receipts. Unchanged receipts are idempotent, including repeated terminal ticks. The request ledger is never trimmed by that retention rule. At most 100 distinct completed discovery imports are accepted per job. Each request reserves its full possible body charge before the GET. A clean response releases unused reserved bytes. A crashed or failed request keeps the full charge because its received size may be unknown. Requests and charged body bytes are cumulative across restarts. They are not provider cost or total network-bandwidth accounting.

Only one writer may tick/import a state file. A file lock rejects concurrent work. An interrupted in-flight GET becomes an `unknown` request receipt and can be retried within the existing attempt budget; this is at-least-once GET behavior, not exactly-once remote access. No paid or mutating provider operation is retried.

| Final state | Meaning |
|---|---|
| `complete` | The bounded queue is exhausted. Some URLs may be robots-blocked, skipped or redirected. Inspect the counts. It does not mean every page on a site was collected. |
| `partial` | The queue is exhausted but requests failed or the frontier limit discarded further in-scope links. |
| `paused` | A hard request, page, body-byte or job-lifetime budget stopped pending work. Automatic continuation ends. |
| `running` | Work remains within budget. Wait for `wait_seconds` before another tick. |

The job lifetime starts when its state is created and includes downtime. A budget pause is a deliberate cap, not an instruction to reset counters. Review its receipts before deciding whether a separately configured new job is appropriate. Increasing a cap in the existing config is refused by the state fingerprint. Source delays and `Retry-After` can exhaust lifetime without collecting a page.

If n8n loses a response, inspect authenticated `GET /v1/status` or local `collector.py status` first. Resume with the same config/state only after reconciling its receipt. A completed queue is harmless to tick again. Do not delete state to hide an uncertain result.

Export collected documents explicitly:

```sh
python3 collector.py export --config examples/config.demo.json --state .runtime/demo.sqlite > .runtime/documents.json
```

For a live state, include `--live` even for status/export so its transport-mode fingerprint matches; those actions do not fetch. Treat the database and exports as private working data until reviewed. Nothing automatically publishes them. Stop the service normally, retain or delete only your own state according to your retention policy, and remove its n8n credential when no longer needed.

## Verification

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
node tests/test_workflow.mjs
python3 build_workflow.py
```

The tests use synthetic fixtures and a generated local TLS certificate. The HTTP controller test starts a disposable loopback service, verifies authentication and restart continuation, then tears it down. No test scrapes a public website, reads a provider credential, sends outreach or invokes a paid service. The Node test checks the exported graph and receipt validator; it does not itself prove n8n engine execution.

Publication should use only files listed in `PUBLIC-MANIFEST.json`. Runtime state, logs, private provenance and review evidence are excluded. Current package status: locally implemented and synthetically validated; public-source production behavior and publication acceptance require separate verification.
