# Implementation field notes

Three source-based articles explain decisions inside the public templates. Each includes executable fictional examples, observed outputs and the limits that remain for a real installation.

| Note | What to inspect | Run from the repository root |
|---|---|---|
| [Support assistant with abstention](https://github.com/benian-technologies/automation-templates/blob/main/field-notes/approved-faq-assistant.md) | Exact approved answers, explicit human requests, and a valid but irrelevant FAQ selection | `node field-notes/replay.cjs faq` |
| [Cited editorial review](https://github.com/benian-technologies/automation-templates/blob/main/field-notes/cited-editorial-review.md) | Invented quote rejection and a misleading claim that still needs an editor | `node field-notes/replay.cjs editorial` |
| [Bounded source research](https://github.com/benian-technologies/automation-templates/blob/main/field-notes/bounded-public-source-research.md) | Discovery replay, deduplication, a request-budget pause and configuration binding | `python3 field-notes/collector-experiments.py` |

The JavaScript replay requires Node.js 22 or later. It runs the actual exported preparation/validation Code nodes, with configuration enabled only in memory and fictional provider responses. Eight FAQ and six editorial cases assert their expected results. It executes trusted code from this repository; the VM is not a security boundary for arbitrary scripts.

The collector experiments require Python 3.12 or later. Each operation runs the real CLI in a fresh process against temporary private state. They demonstrate five scenarios with the fixed offline transport and remove their temporary files. No live mode, provider credential, external website or complete n8n graph is used by these commands.

These are implementation notes and test harnesses for existing exports, not additional n8n templates. They were produced by AI agents and checked against the exported source. Existing [validation and limitations](https://github.com/benian-technologies/automation-templates/blob/main/VALIDATION.md) still apply. No client information, runtime data or invented client outcome is included.
