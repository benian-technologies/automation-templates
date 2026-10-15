# Run a small demonstration before connecting your accounts

These walkthroughs show what the existing templates do when an answer is available, a source cannot be verified or a process needs to continue after a restart. All examples are fictional. No customer data, credentials, model calls or public scraping is required.

Clone the library and enter its directory:

```sh
git clone https://github.com/benian-technologies/automation-templates.git
cd automation-templates
```

| Walkthrough | What to watch | Run |
|---|---|---|
| [Approved FAQ chatbot](approved-faq-chatbot.md) | Exact approved answer, explicit human handoff and an invented answer ID rejected | `node walkthroughs/run-workflow-demo.cjs faq` |
| [Cited content packet](cited-editorial-packet.md) | Source evidence carried into review; fabricated quote refused | `node walkthroughs/run-workflow-demo.cjs editorial` |
| [Public-source collector](public-source-collector.md) | Durable queue, discovery replay, robots decision and duplicate body handling | `python3 walkthroughs/run-collector-demo.py` |
| [Business-hours endpoint](office-hours-status.md) | Opening/closing boundaries, lunch breaks, overnight shifts and closures | `node walkthroughs/run-workflow-demo.cjs office` |

Use Node.js 22 or later for the JavaScript demonstrations and Python 3.12 or later for the collector. The JavaScript runner executes Code text from the actual workflow exports in a small local harness. It enables configuration only in memory and supplies fictional model responses or a fixed test clock. It does not reproduce n8n's complete runtime. The collector runs the actual Python CLI repeatedly against temporary private state, then removes that state.

The demonstrated behaviors are not evidence of live provider quality, a customer deployment or business results. Each walkthrough links the configuration and acceptance work needed for an installation.
