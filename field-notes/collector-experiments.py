#!/usr/bin/env python3
"""Exercise the real collector CLI against its fixed offline transport only."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

PACKAGE = Path(__file__).resolve().parents[1] / 'public-source-collector'


def main():
    if sys.version_info < (3, 12):
        raise SystemExit('Python 3.12 or later is required.')
    print('FICTIONAL OFFLINE FIXTURES. No external source or n8n graph is executed.')
    with tempfile.TemporaryDirectory(prefix='benian-field-note-') as folder:
        directory = Path(folder)
        os.chmod(directory, 0o700)

        def command(action, config, state, *args, expected=0):
            result = subprocess.run([sys.executable, str(PACKAGE / 'collector.py'), action,
                                     '--config', str(config), '--state', str(state), *args],
                                    capture_output=True, text=True, timeout=15)
            assert result.returncode == expected, (action, result.stdout, result.stderr)
            if expected:
                assert result.stdout == ''
                assert result.stderr.strip() == 'collector_failed: inspect configuration and local state; no remote response logged'
                return {'exitCode': result.returncode, 'message': result.stderr.strip()}
            return json.loads(result.stdout)

        def complete(config, state):
            deadline = time.monotonic() + 45
            while True:
                result = command('tick', config, state)
                if result['state'] != 'running':
                    return result
                wait = max(0.05, result['wait_seconds'])
                if time.monotonic() + wait > deadline:
                    raise RuntimeError('Offline experiment exceeded its local deadline.')
                time.sleep(wait)

        config = PACKAGE / 'examples/config.demo.json'
        state = directory / 'complete.sqlite'
        export = PACKAGE / 'examples/discovery.demo.json'
        first = command('discover', config, state, '--input', str(export))
        replay = command('discover', config, state, '--input', str(export))
        assert first == {'accepted': 2, 'rejected': 1, 'replay': False}
        assert replay == {'accepted': 2, 'rejected': 1, 'replay': True}
        print(json.dumps({'case': 'discovery-replay', 'first': first, 'repeat': replay}, indent=2))
        changed = json.loads(export.read_text())
        changed['items'].append({'url': 'https://docs.example.com/guides/copy'})
        changed_path = directory / 'changed-discovery.json'
        changed_path.write_text(json.dumps(changed))
        refused = command('discover', config, state, '--input', str(changed_path), expected=1)
        assert command('discover', config, state, '--input', str(export)) == replay
        print(json.dumps({'case': 'same-import-id-changed-urls', 'result': refused}, indent=2))
        final = complete(config, state)
        assert final['state'] == 'complete' and final['pages'] == 3 and final['unique_documents'] == 2 and final['requests'] == 4
        assert final['frontier']['blocked'] == 1
        assert command('tick', config, state) == final
        documents = command('export', config, state)
        assert len(documents) == 3 and sum(bool(d['duplicate_of']) for d in documents) == 1
        print(json.dumps({'case': 'completed-queue', 'result': final,
                          'documents': [{k: d[k] for k in ['url', 'title', 'text', 'duplicate_of']} for d in documents]}, indent=2))
        limited = json.loads(config.read_text())
        limited['limits']['max_requests'] = 2
        limited_path = directory / 'limited-config.json'
        limited_path.write_text(json.dumps(limited))
        limited_state = directory / 'limited.sqlite'
        paused = complete(limited_path, limited_state)
        assert paused['state'] == 'paused' and paused['reason'] == 'request_budget'
        assert paused['requests'] == 2 and paused['pages'] == 1 and not paused['continue']
        assert command('tick', limited_path, limited_state) == paused
        print(json.dumps({'case': 'two-request-budget', 'result': paused}, indent=2))
        limited['limits']['max_requests'] = 3
        limited_path.write_text(json.dumps(limited))
        mismatch = command('status', limited_path, limited_state, expected=1)
        print(json.dumps({'case': 'change-config-on-existing-state', 'result': mismatch}, indent=2))
        limited['limits']['max_requests'] = 2
        limited_path.write_text(json.dumps(limited))
        assert command('status', limited_path, limited_state) == paused
    print('All expected results matched. Temporary synthetic state removed.')


if __name__ == '__main__':
    main()
