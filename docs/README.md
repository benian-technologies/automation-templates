# Automation catalog

This folder is the public GitHub Pages source for the existing automation library. It contains a searchable static catalog, workflow/setup/source links and four fictional-data proof sets. All fourteen template entries are present in HTML before JavaScript runs.

## Rebuild and check

From the repository root, with Node.js 22 or later and Python 3.12 or later:

```sh
python3 tools/build-catalog.py
python3 tests/catalog-integrity.py
python3 -m http.server 8842 --bind 127.0.0.1 --directory docs
```

Open `http://127.0.0.1:8842/`. The build executes the existing fictional-data demonstrations and extracts their actual JSON output into `proofs.json`. The JavaScript cases execute exported Code in a harness, while the collector runs its real offline CLI. These are not live provider tests. Each proof records its workflow and runner hashes. The dependency manifest also includes the collector implementation and both demo input files, identifying the repository source exercised by that demonstration.

`tools/catalog-content.json` holds the curated descriptions, installation needs and boundaries. `tools/build-catalog.py` validates actual workflow exports and produces `index.html`, `catalog.json`, `proofs.json`, sitemap and robots files. `catalog.css` and `catalog.js` implement responsive presentation, search, category filtering, deep links and copyable commands. No analytics, external scripts, accounts, cookies or client inputs are required.

## Publish

Use the public repository's free GitHub Pages route, with `main` and `/docs` as the publishing source. No custom domain is required. Inspect the deployed build and normal public URL before claiming publication. Every linked field note must be present on main before deployment.

The existing downloadable release remains a separately versioned package. Publishing this catalog does not change workflow logic, activate an instance or add provider-approved templates.
