# Create and verify a WordPress draft after editor approval

Create a WordPress draft from an editor-approved title and plain-text paragraphs. The workflow checks the exact stable slug before creating, then independently reads the exact post ID and compares draft status, slug, raw title and raw content. It returns an editor URL. It never publishes a post.

## Setup

1. Import `approved-wordpress-draft.json` into a new inactive workflow. It has no fixed workflow ID.
2. In **Prepare Request**, set `siteOrigin` to your HTTPS WordPress origin without a trailing slash or path, such as `https://your-site.org`. This version supports WordPress at the domain root. Set `enabled: true` after reviewing configuration.
3. Create a WordPress Application Password for a dedicated user with only the permissions needed to read and create drafts. Store the username and application password in an n8n Basic Auth credential. Bind it to **Find Exact Slug**, **Create Draft** and **Read Draft By ID**. All calls must use TLS. Do not put credentials into the export, request body or URL.
4. Bind a separate Header Auth credential to **Receive Request**. Only an authenticated editorial backend or trusted operator should call it. A browser or an unreviewed model must not hold this credential. The backend must authenticate the actual editor and permit `editorApproved: true` only after approval of the exact payload.
5. Serialize requests for each stable slug in your caller. Use a new slug only for a new article. Test on a staging site with the supplied fictional input, including a second identical request and a conflicting-content request.
6. Inspect the returned draft in WordPress. Publishing is a separate editor action in WordPress; this workflow contains no publish action.

## Input

```json
{
  "requestId":"draft-001",
  "slug":"demo-onboarding-checklist",
  "title":"An onboarding checklist",
  "paragraphs":["Agree on the scope before implementation.","Use fictional records for the first acceptance test."],
  "editorApproved":true,
  "editorReference":"review-demo-001"
}
```

`requestId` is opaque, up to 80 letters, digits, underscores or hyphens. The stable `slug` uses lowercase letters, digits and single separating hyphens, up to 80 characters. Title: 180 characters, no angle brackets. Paragraphs: 1-30, each at most 2,500 characters and 30,000 combined. Square brackets are rejected in both title and paragraphs to prevent WordPress shortcode interpretation. Paragraph HTML is escaped and wrapped in paragraph tags. This template deliberately does not accept rich HTML, shortcodes, media or scripts. The editor reference is a non-secret review-record pointer, not a token or permission check. Unknown fields and missing approval are rejected.

## Results and retry rules

- `draft_created_and_verified`: creation returned a post ID, and a separate GET matched status, slug, raw title and raw content.
- `existing_draft_verified`: the exact same draft already existed; no POST was made, and a separate ID read verified it.
- `existing_slug_conflict`: a post uses this slug but is not the same draft. No update is made.
- `possible_concurrent_create`: WordPress returned a different, potentially suffixed slug. Inspect the reported post before doing anything else.
- `create_outcome_unknown`: the POST result was not verifiable. A draft may exist. Search for the requested slug and suffixed drafts before retrying.
- `draft_readback_failed`: a post ID exists, but its fresh state did not match. Inspect it; do not treat this as success.

HTTP 400 is invalid input, 503 disabled setup, 409 a conflict and 502 an unverified provider result. No HTTP retries or redirects are enabled. The workflow checks at most two exact-slug results and rejects ambiguity.

WordPress does not provide an atomic unique-key reservation for this sequence. The lookup makes serial replays safe, but concurrent requests can race and plugins may transform content. Keep one writer per slug, and reconcile unknown outcomes manually. A reused request ID alone does not prevent duplicates. Existing posts are never updated or deleted, including when the editor changes the content.

WordPress Application Passwords and role capabilities are configured by the site operator. Verify your plugins and user permissions on staging. The export disables execution payload saving, but WordPress retains the created draft and your proxy or instance may have separate logs.

## Validation state

Synthetic exact-Code and whole-graph tests cover create/readback, serial replay without a second POST, content/status conflicts, markup escaping, approval rejection, ambiguous/failed lookup, unknown POST outcomes, concurrent slug suffixes and failed readback. No live WordPress site or application password has been used. Native n8n 2.41.6 also passed seven fixture-graph cases: creation/readback, existing-draft replay, conflicting post, unknown create, concurrent slug, failed readback and shortcode rejection. The imported executable graph and settings were unchanged; an ephemeral workflow ID was added for the CLI. Execution tests enabled configuration and replaced ingress, provider calls and the final webhook response with synthetic fixtures. Actual processing Code and If branches ran in the native engine. The test container had no network. These checks do not establish live-provider acceptance.

References: [WordPress Posts REST API](https://developer.wordpress.org/rest-api/reference/posts/), [WordPress REST authentication](https://developer.wordpress.org/rest-api/using-the-rest-api/authentication/), [n8n HTTP Request](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/).
