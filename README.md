# Benian automation templates

Reusable n8n workflows for scheduling, support, content and operations. Each includes a setup guide, explicit failure behavior and fictional examples. The public-source collector also includes its Python service.

## See a workflow in action

Browse the [searchable automation catalog](https://benian-technologies.github.io/automation-templates/) to compare inputs, outputs and installation needs, then inspect four reproducible fictional-data demonstrations.

Start with the [short, runnable walkthroughs](walkthroughs/README.md): an approved-answer chatbot, cited content review, restartable source collection and business-hours decisions. Each runs with fictional data and shows both a useful result and a boundary. No provider credentials are needed for these demonstrations.

The [implementation field notes](field-notes/README.md) go deeper into FAQ abstention, misleading claims with genuine quotes, and collection budgets that survive restarts. Each includes executable fictional examples and the decisions still needed for a real installation.

## Download or use the n8n listing

Download the ZIP from the [latest release](https://github.com/benian-technologies/automation-templates/releases/latest) for the complete library, setup guides and demonstrations. Each release includes a checksum file. Unzip it, choose one workflow and import its JSON into a new inactive workflow; the ZIP itself is not an n8n import file.

The [confirmed appointment-booking template is also published in n8n's template catalog](https://n8n.io/workflows/20494-book-confirmed-webhook-appointments-in-google-calendar-using-a-post-endpoint/). See [Benian's n8n creator profile](https://n8n.io/creators/emre/) for provider-published listings. Availability in this GitHub library does not imply n8n has reviewed or approved every export.

## Support and scheduling

| Workflow | Result | Setup |
|---|---|---|
| [Approved FAQ chatbot](approved-faq-chatbot.json) | Answer from an operator-reviewed FAQ library or direct the visitor to a person. | [Guide](approved-faq-chatbot.md) |
| [Business-hours status](office-hours-status.json) | Return open or closed status from weekly hours, a time zone and date-specific closures. | [Guide](office-hours-status.md) |
| [Appointment availability](calendar-availability.json) | Check a requested Google Calendar interval and return available, busy or unavailable. | [Guide](calendar-availability.md) |
| [Confirmed appointment booking](calendar-booking.json) | Validate confirmation, check availability and create a private calendar event. | [Guide](calendar-booking.md) |
| [Callback notification](callback-notification.json) | Send a validated callback request to a configured staff inbox through Gmail. | [Guide](callback-notification.md) |

## Content and knowledge

| Workflow | Result | Setup |
|---|---|---|
| [Cited editorial packet](cited-editorial-packet.json) | Turn approved excerpts into an editorial review packet with verifiable source quotes. | [Guide](cited-editorial-packet.md) |
| [Approved WordPress draft](approved-wordpress-draft.json) | Create an editor-approved draft, check for an existing slug and read back the exact post. | [Guide](approved-wordpress-draft.md) |
| [Transcript handoff](transcript-handoff-review.json) | Extract evidence-linked decisions and proposed actions for participant review. | [Guide](transcript-handoff-review.md) |
| [Markdown to Google Docs](markdown-to-google-docs.json) | Create a formatted document and verify its returned file identity. | [Guide](markdown-to-google-docs.md) |
| [Public-source collection](public-source-collector/workflow.json) | Collect permitted pages with durable budgets, deduplication and restartable state. Includes a completed discovery-export importer. | [Complete package](public-source-collector/README.md) |

## Operations and data

| Workflow | Result | Setup |
|---|---|---|
| [n8n failures to Linear](n8n-error-to-linear.json) | Find or create a recovery issue using a stable failure reference, then verify it. | [Guide](n8n-error-to-linear.md) |
| [Instantly opt-out sync](instantly-opt-out-sync.json) | Preview missing suppression entries, optionally add them and verify each result. | [Guide](instantly-opt-out-sync.md) |
| [Google Sheets email validation](google-sheets-email-validation.json) | Deduplicate a bounded range, validate with ZeroBounce and produce a reconciled CSV. | [Guide](google-sheets-email-validation.md) |
| [Inventory update plan](inventory-update-plan.json) | Compare complete snapshots and produce an update CSV for review. | [Guide](inventory-update-plan.md) |

## Start with one workflow

Import its JSON into a **new workflow** in the n8n editor, read its guide and configure your own credentials through n8n Credentials. Exports import inactive. Templates with additional enable/create gates keep those off until the operator deliberately configures them. Begin with fictional data in systems you control.

The JSON files omit top-level workflow identities. For the n8n 2.41.6 CLI importer, prepare a separate copy with a fresh identity:

```sh
python3 tools/prepare-cli-import.py approved-faq-chatbot.json /tmp/faq-import.json
n8n import:workflow --input=/tmp/faq-import.json
```

The helper refuses to overwrite an existing output file. Keep generated import copies outside this public library. Repeated imports create separate workflows; they are not updates to an existing deployment.

The source collector requires a self-hosted service and the network arrangement documented in its guide. It is not an n8n Cloud-only workflow. Its default demonstration uses fixed in-memory pages and makes no external requests.

## Validation and data

Read [validation and limitations](VALIDATION.md) before connecting production data. Synthetic tests and native engine checks do not establish live provider acceptance, model answer quality, customer delivery or business outcomes.

The public files contain generic implementations and fictional fixtures. They include no client exports, private prompts, lead lists, transcripts, bound credentials or stored execution payloads. Guides explain which data an installed workflow sends to a provider. API usage may incur charges in the importer's account.

Run the portable structure checks and failure-workflow tests with:

```sh
python3 tests/validate-library.py
node tests/error-to-linear.cjs
```

The collector's guide includes its offline test command. Keep runtime databases, credentials and real inputs outside this repository.

Current publication: 14 workflow exports, their setup guides and four runnable walkthroughs. The walkthroughs demonstrate existing workflows; they are not additional templates. See [validation and limitations](VALIDATION.md) for what was actually exercised.

The [catalog source and rebuild instructions](docs/README.md) explain how its static entries and proof data are generated from these exports. Search and browsing need no account or provider credentials.

## Implementation help

[Benian Technologies](https://benian.ai/integrations/n8n-automation?utm_source=github&utm_medium=referral&utm_campaign=automation_templates&utm_content=library) is an AI implementation partner. We adapt workflows to a business's process, build in accounts the business owns and train its team to run the result. These templates are starting points for that work.
