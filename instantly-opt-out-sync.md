# Reconcile unsubscribed contacts with the Instantly block list

Read all unsubscribed leads and existing block-list entries, identify missing email blocks, and optionally add and verify them. Existing exact email blocks and exact domain blocks count as covered. The workflow only adds suppression entries.

## Setup

1. Import `instantly-opt-out-sync.json`. It starts manually and is inactive.
2. Create an n8n HTTP Header Auth credential. Set its header name to `Authorization` and store your Instantly API v2 Bearer value in the credential. Connect it to all four HTTP Request nodes. The key needs lead-read and block-list-read/create scopes. Your Instantly plan must support these endpoints.
3. Keep `applyChanges: false` in Sync settings. Run a preview and review the missing addresses. `maxNewBlocks` defaults to 25 and supports up to 1,000 per run.
4. Set `applyChanges: true` after reviewing the preview, then run again. Both lists are freshly read before any write. Every created block is fetched by its returned ID and checked against the planned email.
5. After successful account testing, replace or supplement Manual start with your desired schedule. Avoid concurrent runs.

## Completeness and failure behavior

Both list requests use the returned `next_starting_after` cursor with a 100-page ceiling. The planner refuses to write if the last page still has a cursor, a cursor repeats, a response is malformed, the lead filter includes a status other than unsubscribed, or the configured change cap is exceeded. Raise or redesign the pagination ceiling only after verifying your account volume. Missing or malformed lead emails require source review.

Preview output contains the missing-address list and counts. Applied output contains verified write counts. No-change output reports zero writes. A failed run may have added some blocks before a later request failed. There are no automatic write retries. Re-run a preview to read the current block list before retrying; existing blocks will be skipped. A concurrent change can still cause a provider conflict and stop the run. Domain matching covers the exact email domain only, not parent or wildcard domains.

## Validation and references

Local synthetic checks cover pagination truncation, cursor loops, deduplication, domain coverage, change caps and create/readback mismatches. The exact JSON imported successfully into an isolated n8n 2.41.6 container. The workflow has not been executed against Instantly. Execution retention is disabled in the export. API credentials remain unbound.

Uses the official [list leads](https://developer.instantly.ai/api-reference/lead/list-leads), [list block-list entries](https://developer.instantly.ai/api-reference/blocklistentry/list-block-list-entry), [create entry](https://developer.instantly.ai/api-reference/blocklistentry/create-block-list-entry) and [get entry](https://developer.instantly.ai/api-reference/blocklistentry/get-block-list-entry) contracts. Pagination uses the built-in [n8n HTTP Request node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/).
