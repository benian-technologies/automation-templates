# Create a formatted Google Doc from Markdown

Turn supplied Markdown into HTML, import it into a new Google Doc through Drive, and read back the file identity and type before returning its link. Useful for project briefs, meeting summaries and internal documentation.

## Setup

1. Import `markdown-to-google-docs.json`. The workflow is inactive and starts manually.
2. Connect your Google Drive OAuth2 credential to both HTTP Request nodes and enable the Drive API for that credential. Store authorization in n8n Credentials, never in the JSON or input data.
3. Edit Document input with a title and trusted Markdown. Set `parentFolderId` to a folder you can write to, or leave it empty for My Drive. Do not supply untrusted HTML or externally supplied Markdown without your own content validation.
4. Set `createDocument` to true. Run once with a small test document, open the resulting link and inspect the formatting.

The workflow uses built-in Markdown, Code and HTTP Request nodes. HTTP Request uses typeVersion 4.2, Code version 2 and Markdown version 1. Title length is capped at 200 characters and Markdown at 500,000 characters.

## Behavior and limits

Each run creates a new document. There is no automatic retry on creation. If a request times out or the final readback fails, check Drive before rerunning because creation may already have succeeded. Metadata readback confirms the returned file ID, Google Docs MIME type and non-trashed status. It does not verify the rendered body. Images, advanced tables and unusual Markdown may require adjustment after import.

The HTTP Request credential selector is deliberately unbound. The export contains no account, folder, document or credential identifiers. Manual and successful/error execution retention are disabled in the export; choose retention settings appropriate to your documents.

## Validation and references

Synthetic logic, MIME-body and workflow graph checks pass locally. The exact JSON imported successfully into an isolated n8n 2.41.6 container. Google OAuth and a provider round trip have not been tested.

The upload uses Google's documented [multipart upload and import](https://developers.google.com/workspace/drive/api/guides/manage-uploads) with a Google Docs target MIME type. See [n8n HTTP Request](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/) for credential setup. The current [Markdown node definition](https://github.com/n8n-io/n8n/blob/master/packages/nodes-base/nodes/Markdown/Markdown.node.ts) supports the chosen conversion settings.
