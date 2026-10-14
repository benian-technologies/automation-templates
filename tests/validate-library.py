#!/usr/bin/env python3
"""Check portable workflow structure and reject retained execution/credential state."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = sorted(root.glob('*.json'))
controller = root / 'public-source-collector' / 'workflow.json'
if controller.exists():
    files.append(controller)
errors = []
for path in files:
    workflow = json.loads(path.read_text())
    def check(ok, reason):
        if not ok:
            errors.append(f'{path.relative_to(root)}: {reason}')
    check(workflow.get('active') is False, 'must import inactive')
    for key in ('pinData', 'staticData', 'meta', 'shared', 'tags', 'versionId', 'id'):
        check(not workflow.get(key), f'nonportable or retained {key}')
    nodes = workflow.get('nodes', [])
    names = [n.get('name') for n in nodes]
    ids = [n.get('id') for n in nodes]
    check(bool(nodes) and len(names) == len(set(names)), 'node names missing or duplicated')
    check(all(ids) and len(ids) == len(set(ids)), 'node IDs missing or duplicated')
    for n in nodes:
        check(not n.get('credentials'), 'bound credential reference')
        check(n.get('webhookId') in (None, path.stem, 'template-' + path.stem + '-entry'), 'unexpected webhook identity')
        if n.get('type') == 'n8n-nodes-base.webhook':
            check(n.get('parameters', {}).get('authentication') == 'headerAuth', 'unprotected webhook')
    for source, channels in workflow.get('connections', {}).items():
        check(source in names, 'connection source missing')
        for ports in channels.values():
            for targets in ports:
                for target in targets:
                    check(target.get('node') in names, 'connection target missing')
    settings = workflow.get('settings', {})
    check(settings.get('saveDataErrorExecution') == 'none', 'error payload retention enabled')
    check(settings.get('saveDataSuccessExecution') == 'none', 'success payload retention enabled')
    check(settings.get('saveManualExecutions') is False, 'manual payload retention enabled')
if errors:
    raise SystemExit('\n'.join(errors))
print(f'{len(files)} portable workflow exports passed structural and retained-state checks')
