# Validate Google Sheets email addresses with ZeroBounce

Read a selected sheet range, normalize and deduplicate addresses, validate each unique address with ZeroBounce, and return a reconciled result table and copyable CSV. It does not modify the sheet or send messages.

## Setup

1. Import `google-sheets-email-validation.json`. It starts manually and is inactive.
2. Connect Google Sheets OAuth2 to Read selected sheet range. Enable the Sheets API and give that account access to the source spreadsheet.
3. Connect an HTTP Query Auth credential to Validate with ZeroBounce. Use `api_key` as the parameter name and keep the value inside n8n Credentials.
4. Set your spreadsheet ID, an explicit finite A1 range such as `Contacts!A1:B1000` and `maxUniqueEmails` in Sheet settings. Ranges are limited to 1,000 rows and 26 columns; whole-column and named ranges are rejected. The first row of the range must contain exactly one column named `email`. Other columns are ignored. The default upper limit is 100 unique addresses per run.
5. Test with a small range you control, then inspect the final report. ZeroBounce requires validation credits. Imported credential references are empty.

## Behavior

Blank email cells are skipped. Addresses are trimmed and lowercased, and duplicates are checked once. Invalid syntax, ambiguous headers or a limit breach stop the run before validation calls. The report contains email, provider status, sub-status and a review flag. Only `valid` avoids the review flag; all other supported statuses require review. A deliverability result does not establish permission to contact an address.

The result reconciles provider-returned addresses against the exact requested set. Missing, unexpected or duplicate results and provider errors fail the run. A failed run may have consumed credits for earlier validations; inspect the provider before rerunning. The template does not automatically retry. Increase volume by selecting additional bounded ranges. Data outside the selected range is not inspected.

## Validation and references

Synthetic checks cover deduplication, input limits, invalid syntax, provider errors, reordered responses and incomplete result sets. The exact JSON imported successfully into an isolated n8n 2.41.6 container. A live Sheets/ZeroBounce execution has not been performed. Execution retention is disabled in the export; choose retention settings appropriate to the input data.

Uses [Google Sheets values.get](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/get), [ZeroBounce single-email validation](https://zerobounce.net/docs/email-validation-api-quickstart/v2-validate-emails) and [n8n HTTP Request credentials](https://docs.n8n.io/integrations/builtin/credentials/httprequest/). The exported endpoint is ZeroBounce's default region; choose its documented regional endpoint if required for your data handling.
