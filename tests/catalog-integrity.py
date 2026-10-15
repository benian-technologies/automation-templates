#!/usr/bin/env python3
"""Validate the generated public catalog against its actual source exports."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


class Catalog(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []
        self.articles = []
        self.stylesheets = []
        self.scripts = []
        self.labels = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'a':
            self.links.append(attrs.get('href', ''))
        if tag == 'article':
            self.articles.append(attrs)
        if tag == 'link' and attrs.get('rel') == 'stylesheet':
            self.stylesheets.append(attrs['href'])
        if tag == 'script' and attrs.get('src'):
            self.scripts.append(attrs['src'])
        if tag == 'label':
            self.labels.append(attrs.get('for'))


def main():
    catalog = json.loads((ROOT / 'docs/catalog.json').read_text())
    proofs = json.loads((ROOT / 'docs/proofs.json').read_text())
    parsed = Catalog()
    parsed.feed((ROOT / 'docs/index.html').read_text())
    assert len(parsed.ids) == len(set(parsed.ids)), 'Repeated HTML identity'
    assert len(catalog) == len(parsed.articles) == 14
    assert {entry['id'] for entry in catalog} == {article['id'] for article in parsed.articles}
    assert set(proofs) == {'faq', 'editorial', 'office', 'collector'}
    assert 'search' in parsed.labels
    allowed_hosts = {'github.com', 'raw.githubusercontent.com', 'benian.ai', 'n8n.io'}
    for link in parsed.links:
        assert link, 'Missing link destination'
        if link.startswith('#'):
            assert link[1:] in parsed.ids, link
        elif '://' in link:
            url = urlparse(link)
            assert url.scheme == 'https' and url.hostname in allowed_hosts, link
        else:
            assert (ROOT / 'docs' / link).is_file(), link
    for asset in parsed.stylesheets + parsed.scripts:
        assert (ROOT / 'docs' / asset).is_file(), asset
    for entry in catalog:
        workflow = ROOT / entry['workflow']
        content = json.loads(workflow.read_text())
        assert content['active'] is False
        assert not any(node.get('credentials') for node in content['nodes'])
        assert entry['workflow_sha256'] == hashlib.sha256(workflow.read_bytes()).hexdigest()
        assert (ROOT / entry['guide']).is_file()
        if entry.get('tutorial'):
            assert (ROOT / entry['tutorial']).is_file()
        if entry.get('proof'):
            proof = proofs[entry['proof']]
            assert proof['workflow_sha256'] == entry['workflow_sha256']
            assert proof['external_network_calls'] is False
            runner = proof['command'].split()[1]
            assert proof['runner_sha256'] == hashlib.sha256((ROOT / runner).read_bytes()).hexdigest()
            required = {entry['workflow'], runner}
            if entry['proof'] == 'collector':
                required.update({'public-source-collector/collector.py', 'public-source-collector/examples/config.demo.json', 'public-source-collector/examples/discovery.demo.json'})
            assert set(proof['source_dependencies']) == required
            for source, digest in proof['source_dependencies'].items():
                assert digest == hashlib.sha256((ROOT / source).read_bytes()).hexdigest(), source
    absent_notes = [entry['note'] for entry in catalog if entry.get('note') and not (ROOT / entry['note']).is_file()]
    assert not absent_notes, 'Linked field notes are missing: ' + ', '.join(absent_notes)
    print('Catalog integrity passed: 14 static entries, four source-matched proof sets, valid HTML identities and link contracts.')


if __name__ == '__main__':
    main()
