#!/usr/bin/env python3
"""Create a private n8n CLI import copy with a fresh workflow identity."""
import argparse
import json
import os
from pathlib import Path
import uuid

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('input', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
workflow = json.loads(args.input.read_text())
if not isinstance(workflow, dict) or not isinstance(workflow.get('nodes'), list) or workflow.get('active') is not False:
    raise SystemExit('Expected one inactive workflow export')
if any(workflow.get(key) for key in ('pinData', 'staticData', 'credentials', 'shared')):
    raise SystemExit('Retained state detected; review the input before importing')
if any(node.get('credentials') for node in workflow['nodes']):
    raise SystemExit('Bound credentials detected; use a clean library export')
workflow['id'] = str(uuid.uuid4())
workflow.pop('versionId', None)
# Exclusive creation prevents overwriting a user's existing file.
fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as output:
    json.dump(workflow, output, indent=2)
    output.write('\n')
print('Created an inactive import copy with a fresh workflow ID. Keep the copy outside the public repository.')
