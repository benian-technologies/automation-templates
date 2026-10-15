# Validation and limitations

Validated on October 14, 2026. This library contains 14 inactive workflow exports. Validation uses fictional inputs and isolated systems.

## Runnable walkthroughs

The four [walkthroughs](walkthroughs/README.md) use fictional inputs. Their JavaScript runner reads the exported Code nodes directly: four FAQ cases, three editorial cases and nine schedule cases. Configuration enablement and the schedule clock are replaced only in the local harness; model responses are fixtures. These commands do not execute n8n's complete graph or call a provider.

The collector walkthrough runs its real CLI in separate processes against one temporary SQLite file, checks discovery replay, completes the offline queue, verifies three page URLs/two unique bodies/four requests and verifies an unchanged terminal replay. It uses the built-in fixed transport, then removes its state. It does not run the n8n controller or crawl a public source.

These walkthrough checks supplement the earlier native validation below. No workflow export changed for their publication.

## What was checked

| Area | Evidence and boundary |
|---|---|
| All 14 workflows | Structural checks reject bound credentials, retained payloads, top-level deployment identities and invalid graph references. A fresh n8n 2.41.6 instance imported all 14 and exported matching names, nodes, connections, settings and inactive state. The CLI import copies added only private, fresh workflow IDs. |
| FAQ, editorial packet, WordPress draft and transcript handoff | 42 focused synthetic tests and 17 native n8n execution cases passed. Native cases preserved the executable decision logic while replacing ingress, provider and response boundaries with fixtures. |
| Failure recovery to Linear | Focused assertions and one native synthetic execution covered the issue creation and independent readback path. A read-only Linear query verified the lookup contract. No Linear issue was created during provider validation. |
| Public-source collector | 27 Python tests covered policy, budgets, retries, durable state, discovery replay, a local TLS response, request timeout cleanup and authenticated controller restart. Sixteen negative receipt cases checked the exported workflow. A native n8n run completed three ticks against a synthetic local controller. No public site was crawled. |
| Public files | The complete publication set was reviewed for client identities, private source material, credentials and runtime data. New implementations use generic code and fictional fixtures. The collector's manifest lists its exact public files. |

Native tests ran in disposable containers with external networking disabled. Containers were removed afterward. Logs and deployment-specific import copies are kept outside the public repository.

## What remains to test in your account

These checks do not establish live acceptance by Anthropic, Google, Instantly, ZeroBounce, WordPress or Linear's write API. Configure your own credentials and run controlled acceptance tests before enabling a deployment. Model output quality depends on the model, prompt inputs and approved source material. Citation validation checks the quoted text, not whether an inference is correct.

The scheduling workflows still require your own concurrency and booking-policy acceptance. The WordPress and Linear workflows perform serial lookup and readback; their lookup-before-create behavior is not an atomic lock across simultaneous executions. Follow their guides when retrying an uncertain write.

The collector requires Python 3.12 or later and a self-hosted n8n network arrangement. Its default demonstration is offline. A live collection run requires explicit source scope and permission configuration. Public availability alone does not mean material may be copied or republished. The package does not launch paid discovery, harvest contact lists or send outreach.

No test result here demonstrates customer delivery, adoption, search rankings, leads or revenue. The library publishes reusable starting points; each installation needs its own operational acceptance.
