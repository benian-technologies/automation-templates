# Benian automation templates

Reusable n8n workflows for operations and documentation, prepared by [Benian Technologies](https://benian.ai).

| Template | Purpose | Setup |
|---|---|---|
| [Instantly opt-out sync](instantly-opt-out-sync.json) | Reconcile unsubscribed contacts against the block list, preview missing entries, then add and verify them. | [Guide](instantly-opt-out-sync.md) |
| [Google Sheets email validation](google-sheets-email-validation.json) | Deduplicate a bounded sheet range, validate addresses with ZeroBounce and produce a reconciled CSV report. | [Guide](google-sheets-email-validation.md) |
| [Markdown to Google Docs](markdown-to-google-docs.json) | Create a formatted document from Markdown and verify its returned file identity. | [Guide](markdown-to-google-docs.md) |
| [Inventory update plan](inventory-update-plan.json) | Compare complete warehouse and store snapshots and produce a reviewable update CSV. This planner does not update a store. | [Guide](inventory-update-plan.md) |

Import a JSON file into n8n, read its guide and configure your own credentials through n8n's credential manager. Every workflow imports inactive. Provider credentials and account identifiers are deliberately unbound. Start with synthetic data or a small test you control before connecting business data.

The files were imported into an isolated n8n 2.41.6 container. The inventory planner's synthetic example also executed successfully there. Local synthetic checks cover validation, completeness and failure handling. The Google, Instantly and ZeroBounce integrations have not been executed against live providers. These results establish import and tested local behavior, not production delivery.

The Instantly sync defaults to preview. Google Docs requires an explicit create switch. Email validation can consume ZeroBounce credits. Each guide describes setup, limits and retry behavior.
