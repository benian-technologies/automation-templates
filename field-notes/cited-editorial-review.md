# Keep AI editorial review tied to its sources

An editor needs to see where a proposed claim came from before deciding whether it belongs in an article. An AI content workflow can make that review easier by keeping the claim, source and supporting quote together. It also needs to expose what those checks leave unresolved.

The [cited editorial packet](https://github.com/benian-technologies/automation-templates/blob/main/cited-editorial-packet.json) in Benian's public library takes reviewed excerpts and returns an outline for a person to inspect. It checks that each cited source was supplied and that each quote occurs in that source's excerpt. A successful response remains `needs_editor_review`.

This field note runs the actual exported Code nodes with fictional provider output. One case contains an invented quote and is rejected. Another contains a real quote attached to a misleading claim and is accepted for review. That second case explains why source validation cannot substitute for editorial judgment.

## Separate source approval, drafting and release

The implementation has a fixed sequence:

```text
Operator selects excerpts and asserts permission to process them
  -> validate topic, source IDs, URLs and size limits
  -> fixed model request proposes an outline
  -> validate shape, source IDs and literal quotes
  -> return a review packet

Separate work still required:
  -> store and assign the packet
  -> editor checks meaning and approves an exact version
  -> an explicitly connected publication process uses that version
```

Only the first sequence is implemented in this template. It does not fetch source URLs, store a review queue, obtain editorial approval or publish content. The authenticated caller's `sourceUseApproved: true` is an assertion, not an independent rights check.

That scope makes the integration decision concrete. If a team already has an editorial system, the packet can become an input to that system after mapping and testing. If the team has no approval process, a successful HTTP response does not create one.

## Reproduce a packet with a traceable point

Clone the [library](https://github.com/benian-technologies/automation-templates) and run this command from its root with Node.js 22 or later:

```sh
node field-notes/replay.cjs editorial
```

The runner reads **Prepare Request** and **Validate Model Output** directly from the exported workflow. It enables configuration in memory and substitutes fixed, fictional provider responses. It makes no provider call and does not execute the complete n8n graph.

The [request fixture](https://github.com/benian-technologies/automation-templates/blob/main/field-notes/examples/editorial-request.json) supplies one invented guide:

```json
{
  "requestId": "field-note-editorial-001",
  "topic": "Make implementation review easier to follow",
  "sourceUseApproved": true,
  "sources": [{
    "id": "fictional-review-guide",
    "title": "Fictional implementation review guide",
    "url": "https://example.com/review-guide",
    "excerpt": "Assign a named reviewer before implementation begins. Record changes to the agreed scope. The reviewer checks the revised work before release."
  }]
}
```

The [fictional provider response](https://github.com/benian-technologies/automation-templates/blob/main/field-notes/examples/editorial-provider-response.json) proposes a headline, angle, section and point. Its point says:

```json
{
  "claim": "Assign a reviewer before implementation starts.",
  "sourceId": "fictional-review-guide",
  "evidenceQuote": "Assign a named reviewer before implementation begins."
}
```

The executed validator finds the source ID and literal quote, attaches the source URL from the approved input, and returns HTTP 200. These fields in its result describe the boundary precisely:

```json
{
  "status": "needs_editor_review",
  "checks": {
    "sourceIdsKnown": true,
    "quotesFoundInSuppliedExcerpts": true,
    "semanticAccuracy": "requires_human_review",
    "publication": "not_attempted"
  }
}
```

The full result also contains the headline, angle, sections and a plain-text `reviewText` that places each proposed claim beside its URL and quote. The runner prints that result so the review format can be inspected before any account is connected.

## Demonstrate the gap between a quote and a claim

In the second case, the fictional response substitutes this quotation:

```text
The process guarantees that projects never change.
```

That text is absent from the supplied excerpt. Validation returns HTTP 502 and `status: unavailable`. The workflow does not return the unverifiable packet as successful.

The third case keeps the genuine quotation but changes the claim:

```json
{
  "claim": "A named reviewer guarantees that a project will never change.",
  "sourceId": "fictional-review-guide",
  "evidenceQuote": "Assign a named reviewer before implementation begins."
}
```

The result is HTTP 200, `needs_editor_review`. The quoted sentence is present, so the code's checks pass. The guarantee is unsupported. A reviewer should reject or rewrite it.

This is an intentionally misleading fixture, not advice or a reported project result. It shows the distinction between **traceability** and **entailment**: locating a quote does not establish that the quote supports the surrounding claim. It also does not establish source reliability, freshness, or permission to republish.

The other executed cases check missing source approval, an unknown source ID and a provider response whose stop reason indicates truncation. They return 400, 502 and 502 respectively. None is promoted to an accepted review packet.

## Design the approval around the exact version

When connecting this starter to a real editorial operation, keep at least four things explicit.

**The evidence set.** Record which excerpts the editor reviewed. This template accepts one to ten sources, at most 6,000 characters per excerpt and 24,000 characters combined. It validates unique IDs and URLs. It does not download a fresh copy of the URL or detect a source changing later.

**The review decision.** Have an editor check whether each claim follows from its evidence, whether material context is missing and whether the wording is appropriate. Also inspect the headline and angle: their strings are validated, but they do not carry separate citation requirements in this schema. A headline can overstate an otherwise careful packet.

**The approved version.** In the surrounding system, bind approval to the exact final content. Editing the title, claim or evidence after approval should require review again. A generic boolean attached to an evolving document is a weak representation of what someone approved. This versioned approval mechanism is an implementation recommendation, not a feature included in the template.

**The publication result.** Track approval, publishing attempt and provider readback separately. The library's [WordPress draft workflow](https://github.com/benian-technologies/automation-templates/blob/main/approved-wordpress-draft.md) is a separate starting point that accepts an explicitly approved title and paragraphs. These two templates are not connected. Creating a draft still does not mean an article was published.

## Make the review useful to the team

Render the returned text safely as text. Source material can contain hostile instructions or markup; the model prompt treats excerpts as data, but that does not remove the need for careful rendering and review. Keep webhook and provider credentials separate. The [setup guide](https://github.com/benian-technologies/automation-templates/blob/main/cited-editorial-packet.md) explains the provider request, disabled execution-payload saving and remaining retention responsibilities.

Use reviewed examples from the intended publication to evaluate the real model. Include supported claims, unsupported extrapolations, quotes taken out of context and stale evidence. Count corrections and rejected packets as well as successful output. This offline replay establishes deterministic handling of the supplied fixtures, not editorial quality or the amount of work saved.

The practical implementation question is where your editor sees the evidence and records the decision. Once that is clear, the automation can support the existing responsibility instead of leaving a JSON packet without an owner.

Related: [how Benian separates model judgment from fixed workflow steps](https://benian.ai/compare/ai-agents-vs-workflows?utm_source=github&utm_medium=referral&utm_campaign=implementation_field_notes&utm_content=cited_editorial_review), and the [public-source collection field note](https://github.com/benian-technologies/automation-templates/blob/main/field-notes/bounded-public-source-research.md).

Produced by AI agents and checked against the exported workflow. All source excerpts and provider outputs in these examples are fictional. No personal client experience or live-provider acceptance is claimed. [Validation scope](https://github.com/benian-technologies/automation-templates/blob/main/VALIDATION.md).
