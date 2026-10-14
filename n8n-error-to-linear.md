# Record n8n failures in Linear with duplicate checks

Create a recovery issue for an automatically failed n8n workflow. Before creating it, search the chosen Linear team for the same instance, workflow and original execution reference. Retry executions that identify the same original execution reuse the issue. Trigger failures use their recorded timestamp instead.

## Setup

1. Import `n8n-error-to-linear.json`. It imports inactive. Open Recovery settings and set your Linear team UUID, a stable nonsecret `instanceKey`, and your n8n HTTPS origin. Keep `createIssue: false` initially.
2. Bind an HTTP Header Auth credential to all three HTTP Request nodes. Use `Authorization` as the header name and store your Linear personal API key as its value. Restrict it to the team and issue permissions you need. The credential remains unbound in this export.
3. Save the workflow. In a workflow you own, select it under Settings > Error workflow. The n8n Error Trigger listens for automatic workflow failures. A manual execution of the failing workflow does not invoke it.
4. Produce a controlled automatic failure in a test workflow. Preview still reads Linear, but creates nothing. Inspect the proposed issue and its source link.
5. Set `createIssue: true` only when ready. Run another controlled failure and open the returned Linear issue. Repeat the same error input in a test harness to check sequential deduplication.

The workflow does not forward raw errors, stack traces, input payloads, node labels or workflow names. It sends the configured instance label, workflow/execution IDs and links. Those references may be operationally sensitive, so choose the destination team appropriately. Execution saving is disabled in the export; review your instance-wide retention separately.

## Failure and retry behavior

The search includes archived issues and refuses to create when it sees multiple matches, incomplete pagination, GraphQL errors or an identity mismatch. Creation is followed by a separate issue readback. A successful result is `created_and_verified`; an existing match returns `existing_issue`. Preview returns the proposed title and description.

Search then create is not an atomic operation. Serialize runs for a given failure reference. Concurrent runs may create duplicates. This template does not promise exactly-once creation or reopen previously closed issues. If the original execution has not been saved and no stable trigger timestamp exists, the run stops without writing.

There are no automatic write retries. If creation times out or readback fails, inspect Linear for the exact failure marker before trying again. Failure of this error workflow itself needs an independent operational alert route.

## Validation

Focused synthetic tests cover retry identity, trigger failures, rejected configuration, missing identity, existing and duplicate issues, GraphQL errors, preview, creation and mismatched readback. No authenticated Linear issue has been created by the template during preparation. Import and native engine checks are listed in the repository validation record.

References: [Linear GraphQL](https://linear.app/developers/graphql), [Linear filtering](https://linear.app/developers/filtering), [n8n Error Trigger](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.errortrigger/).
