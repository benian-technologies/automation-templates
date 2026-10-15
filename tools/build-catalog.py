#!/usr/bin/env python3
"""Build the public catalog and reproduce its four fictional-data demonstrations."""
import hashlib
import html
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
REPO = 'https://github.com/benian-technologies/automation-templates'
SITE = 'https://benian-technologies.github.io/automation-templates/'
RAW = 'https://raw.githubusercontent.com/benian-technologies/automation-templates/main/'
ICONS = {
    'Support and scheduling': '<path d="M7 10h10M7 14h6M5 3h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H9l-6 3V5a2 2 0 0 1 2-2Z"/>',
    'Content and knowledge': '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8ZM14 2v6h6M8 12h8M8 16h6"/>',
    'Operations and data': '<path d="M4 5h16v5H4ZM4 14h16v5H4ZM8 7.5h.01M8 16.5h.01"/>',
    'search': '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    'check': '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
    'download': '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
}


def esc(value):
    return html.escape(str(value), quote=True)


def icon(name):
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ICONS[name] + '</svg>'


def objects_in(text):
    """Extract the JSON objects printed by the existing public demonstration tools."""
    decoder = json.JSONDecoder()
    values = []
    at = 0
    while True:
        start = text.find('{', at)
        if start < 0:
            return values
        try:
            value, end = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            at = start + 1
            continue
        values.append(value)
        at = start + end


def reproduce():
    specifications = {
        'faq': ('approved-faq-chatbot.json', ['node', 'walkthroughs/run-workflow-demo.cjs', 'faq']),
        'editorial': ('cited-editorial-packet.json', ['node', 'walkthroughs/run-workflow-demo.cjs', 'editorial']),
        'office': ('office-hours-status.json', ['node', 'walkthroughs/run-workflow-demo.cjs', 'office']),
        'collector': ('public-source-collector/workflow.json', ['python3', 'walkthroughs/run-collector-demo.py']),
    }
    proofs = {}
    for key, (workflow, command) in specifications.items():
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True, timeout=60)
        values = objects_in(result.stdout)
        assert values, key
        if key == 'faq':
            assert len(values) == 4 and values[1]['result']['status'] == 'answered_from_approved_faq'
            assert values[2]['result']['status'] == 'human_handoff' and values[3]['httpStatus'] == 502
        elif key == 'editorial':
            assert len(values) == 3 and values[0]['result']['status'] == 'needs_editor_review'
            assert values[1]['httpStatus'] == 502 and values[2]['httpStatus'] == 400
        elif key == 'office':
            assert len(values) == 9 and values[1]['office_is_open'] is True and values[4]['office_is_open'] is False
        else:
            assert values[0]['replay'] is False and values[1]['replay'] is True
            assert values[-1]['state'] == 'complete' and values[-1]['pages'] == 3
            assert values[-1]['unique_documents'] == 2 and values[-1]['requests'] == 4
            assert values[-1]['frontier']['blocked'] == 1
            # Keep the stable discovery and final results, not variable pacing receipts.
            values = [values[0], values[1], values[-1]]
        dependencies = [workflow, command[1]]
        if key == 'collector':
            dependencies.extend(['public-source-collector/collector.py', 'public-source-collector/examples/config.demo.json', 'public-source-collector/examples/discovery.demo.json'])
        proofs[key] = {
            'command': ' '.join(command),
            'scope': 'Actual offline collector CLI with built-in fictional transport; no n8n controller execution.' if key == 'collector' else 'Actual exported Code in a local harness with fictional provider responses or a fixed clock; not the full n8n graph.',
            'external_network_calls': False,
            'workflow_sha256': hashlib.sha256((ROOT / workflow).read_bytes()).hexdigest(),
            'runner_sha256': hashlib.sha256((ROOT / command[1]).read_bytes()).hexdigest(),
            'source_dependencies': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in dependencies},
            'results': values,
        }
    return proofs


def proof_html(item, proofs):
    key = item.get('proof')
    if not key:
        return ''
    proof = proofs[key]
    summaries = {
        'faq': ('The model can select an approved answer. It cannot supply new answer prose.', 'Approved hours returned. Invented answer ID rejected.'),
        'editorial': ('An exact source quote is retained for review. A fabricated quotation fails validation.', 'Cited packet returned. Invented quote rejected.'),
        'office': ('A fixed Chicago schedule exposes the exact opening, lunch, closing and overnight decisions.', 'Nine schedule checks matched their expected result.'),
        'collector': ('A new CLI process resumes the same local queue. Duplicate discovery and final receipts are reconciled.', '3 URLs collected, 2 unique bodies, 1 robots block.'),
    }
    explanation, result = summaries[key]
    shown = proof['results']
    command_id = 'command-' + item['id']
    return f'''<section class="proof" aria-labelledby="proof-{esc(item['id'])}">
      <div class="proof-top"><h3 id="proof-{esc(item['id'])}">Inspect a fictional run</h3><span class="proof-tag">{'Offline CLI' if key == 'collector' else 'Code-node demo'}</span></div>
      <p class="proof-summary">{esc(explanation)}</p>
      <div class="proof-results"><div class="proof-result-line">{icon('check')}<span>{esc(result)}</span></div>
      <details><summary>Read the actual example output</summary><pre>{esc(json.dumps(shown, indent=2))}</pre></details></div>
      <div class="reproduce"><code id="{command_id}">{esc(proof['command'])}</code><button class="copy-command" type="button" data-command="{command_id}" aria-label="Copy command for {esc(item['name'])}">Copy</button></div>
      <div class="proof-links"><a href="{REPO}/blob/main/{esc(item['tutorial'])}">Follow the walkthrough</a><a href="proofs.json">Inspect all proof data</a></div>
      <p class="proof-boundary">Run from the downloaded library folder. {'Python 3.12 or later.' if key == 'collector' else 'Node.js 22 or later.'} {esc(proof['scope'])} No provider calls or customer data.</p>
    </section>'''


def main():
    content = json.loads((ROOT / 'tools/catalog-content.json').read_text())
    assert len(content) == 14 and len({row['id'] for row in content}) == 14
    proofs = reproduce()
    DOCS.mkdir(exist_ok=True)
    entries = []
    articles = []
    structured = []
    for index, item in enumerate(content, 1):
        workflow_path = item.get('workflow', item['id'] + '.json')
        guide_path = item.get('guide', item['id'] + '.md')
        workflow = json.loads((ROOT / workflow_path).read_text())
        assert workflow['active'] is False and (ROOT / guide_path).is_file()
        assert not any(node.get('credentials') for node in workflow['nodes'])
        item['workflow'] = workflow_path
        item['guide'] = guide_path
        item['workflow_sha256'] = hashlib.sha256((ROOT / workflow_path).read_bytes()).hexdigest()
        item['processing_nodes'] = sum(node['type'] != 'n8n-nodes-base.stickyNote' for node in workflow['nodes'])
        search = ' '.join([item['name'], item['category'], item['description'], item['terms'], *item['needs']]).lower()
        entries.append(f'''<li><a class="template-link" href="#{esc(item['id'])}" data-category="{esc(item['category'])}" data-search="{esc(search)}"><span class="template-mark">{icon(item['category'])}</span><span class="template-name">{esc(item['name'])}<span class="template-kind">{'Runnable example included' if item.get('proof') else esc(', '.join(item['needs'][:2]))}</span></span><span class="template-arrow" aria-hidden="true">›</span></a></li>''')
        needs = ''.join('<li>' + esc(need) + '</li>' for need in item['needs'])
        note = f'<a href="{REPO}/blob/main/{esc(item["note"])}">Read the implementation note</a>' if item.get('note') else ''
        listing = f'<a href="{esc(item["listing"])}">View on n8n</a>' if item.get('listing') else ''
        implementation = 'https://benian.ai/' + item['implementation'] + '?utm_source=github_pages&utm_medium=referral&utm_campaign=automation_templates&utm_content=' + item['id'].replace('-', '_')
        articles.append(f'''<article class="template-detail" id="{esc(item['id'])}" aria-labelledby="title-{esc(item['id'])}">
          <header class="detail-header"><p class="detail-category">{icon(item['category'])}{esc(item['category'])}</p><h2 id="title-{esc(item['id'])}" tabindex="-1">{esc(item['name'])}</h2><p class="detail-lead">{esc(item['description'])}</p>
          <div class="actions"><a class="button" href="{REPO}/blob/main/{esc(guide_path)}">Read setup guide</a><a class="button secondary" href="{RAW}{esc(workflow_path)}">Open workflow JSON</a><a class="text-link" href="{REPO}/blob/main/{esc(workflow_path)}">View source</a></div></header>
          <dl class="recipe"><div><dt>Input</dt><dd>{esc(item['input'])}</dd></div><div><dt>Checks</dt><dd>{esc(item['check'])}</dd></div><div><dt>Result</dt><dd>{esc(item['result'])}</dd></div></dl>
          <div class="requirements"><span>Installation needs</span><ul>{needs}</ul></div>
          {proof_html(item, proofs)}
          <div class="detail-bottom"><div><h3>Before you connect real data</h3><p>{esc(item['boundary'])}</p></div><nav class="next-links" aria-label="More about {esc(item['name'])}">{note}{listing}<a href="{esc(implementation)}">Implementation help</a></nav></div>
          <footer class="workflow-meta"><span>Imports inactive. Credentials are not included.</span><span>{item['processing_nodes']} processing nodes</span></footer>
        </article>''')
        structured.append({'@type': 'ListItem', 'position': index, 'name': item['name'], 'url': SITE + '#' + item['id']})
    schema = json.dumps({'@context': 'https://schema.org', '@type': 'ItemList', 'name': 'Benian automation templates', 'numberOfItems': 14, 'itemListElement': structured}).replace('<', '\\u003c')
    reading = [
        ('approved-faq-assistant', 'Build a support assistant that can decline to answer', 'See why approved answer text can still be irrelevant, and test where a person must take over.'),
        ('cited-editorial-review', 'Keep AI editorial review tied to its sources', 'Compare a fabricated quote with a genuine quote attached to a misleading claim.'),
        ('bounded-public-source-research', 'Make public-source research stop and resume predictably', 'Inspect discovery replay, duplicate content and a budget pause that survives a restart.'),
    ]
    reading_links = ''.join(f'<li><a href="{REPO}/blob/main/field-notes/{slug}.md">{esc(title)}</a><p>{esc(description)}</p></li>' for slug, title, description in reading)
    document = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Automation templates with runnable examples | Benian</title>
<meta name="description" content="Browse 14 n8n workflows for support, scheduling, content and operations. Inspect four reproducible fictional-data demonstrations, setup guides and source files.">
<link rel="canonical" href="{SITE}"><meta name="theme-color" content="#2259d6"><meta property="og:title" content="Automations you can inspect | Benian"><meta property="og:description" content="14 workflows, practical setup guides and four reproducible demonstrations."><meta property="og:type" content="website"><meta property="og:url" content="{SITE}">
<link rel="stylesheet" href="catalog.css"><script src="catalog.js" defer></script><script type="application/ld+json">{schema}</script></head>
<body><a class="skip-link" href="#library">Skip to the template library</a><div class="shell">
<header class="site-header"><a class="brand" href="https://benian.ai/"><strong>BENIAN</strong><span>Automation library</span></a><nav class="header-links" aria-label="Library links"><a href="{REPO}">View repository</a><a class="button" href="{REPO}/releases/latest">{icon('download')}Download library</a></nav></header>
<section class="intro" aria-labelledby="page-title"><div><h1 id="page-title">Automations you can inspect.</h1><p>14 workflows for support, scheduling, content and operations. Read the setup, inspect a fictional run, then adapt the pattern to your business.</p></div><aside class="intro-note"><strong>Built to be understood.</strong>Clear inputs. Explicit checks. Results you can read before connecting your accounts.</aside></section>
<main class="library" id="library"><aside class="browse" aria-label="Choose a workflow"><div class="js-only"><label class="search-label" for="search">Find a workflow</label><div class="search-wrap">{icon('search')}<input type="search" id="search" placeholder="Try chatbot, calendar or CSV" autocomplete="off"></div><div class="filters" role="group" aria-label="Filter by workflow category"><button type="button" class="filter" data-filter="all" aria-pressed="true">All</button><button type="button" class="filter" data-filter="Support and scheduling" aria-pressed="false">Support</button><button type="button" class="filter" data-filter="Content and knowledge" aria-pressed="false">Content</button><button type="button" class="filter" data-filter="Operations and data" aria-pressed="false">Operations</button></div></div><div class="index-heading"><p id="result-count" aria-live="polite">14 templates</p><button type="button" class="reset js-only" data-reset>Reset filters</button></div><nav aria-label="Templates"><ul class="template-index">{''.join(entries)}</ul></nav><p class="index-empty" id="index-empty" hidden>No matching workflows.</p></aside>
<div class="workspace"><noscript><p class="nojs-message">All templates are shown below. Enable JavaScript for search and a focused detail view.</p></noscript>{''.join(articles)}<section id="empty-state" class="empty-state" hidden><h2>No match yet.</h2><p>Try a task such as “calendar” or “content”, or clear the filters to see all 14 workflows.</p><button type="button" class="button" data-reset>Show all workflows</button></section></div></main>
<section class="field-notes" aria-labelledby="field-notes-title"><div class="reading-heading"><h2 id="field-notes-title">Read the implementation decisions.</h2><p>Three field notes with executable fictional examples, observed failures and the work still required for a real installation.</p></div><ul>{reading_links}</ul></section>
<footer class="library-footer"><p>These are reusable starting points with fictional examples. Synthetic checks are separate from live provider acceptance, production delivery and business results. Read the <a href="{REPO}/blob/main/VALIDATION.md">validation boundaries</a> before connecting your accounts. GitHub publication does not mean every template is approved by n8n.</p><a href="https://n8n.io/creators/emre/">Benian on n8n</a></footer><p class="sr-only" id="copy-status" role="status"></p></div></body></html>
'''
    (DOCS / 'index.html').write_text(document)
    (DOCS / 'catalog.json').write_text(json.dumps(content, indent=2) + '\n')
    (DOCS / 'proofs.json').write_text(json.dumps(proofs, indent=2) + '\n')
    (DOCS / '.nojekyll').write_text('')
    (DOCS / 'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: ' + SITE + 'sitemap.xml\n')
    (DOCS / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>' + SITE + '</loc></url></urlset>\n')
    print('Built 14 static template entries and reproduced four fictional-data proof sets.')


if __name__ == '__main__':
    main()
