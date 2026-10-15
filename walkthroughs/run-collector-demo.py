#!/usr/bin/env python3
"""Show durable continuation against fixed offline pages, then remove demo state."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

package = Path(__file__).resolve().parents[1] / 'public-source-collector'
config = package / 'examples/config.demo.json'


def main():
    if sys.version_info < (3, 12):
        raise SystemExit('Python 3.12 or later is required.')
    print('OFFLINE DEMONSTRATION: fixed fictional pages, no external requests.')
    with tempfile.TemporaryDirectory(prefix='benian-collector-demo-') as directory:
        os.chmod(directory, 0o700)
        state = Path(directory) / 'demo.sqlite'

        def run(action, *args):
            command = [sys.executable, str(package / 'collector.py'), action,
                       '--config', str(config), '--state', str(state), *args]
            result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=15)
            return json.loads(result.stdout)

        run('plan')
        discovery = run('discover', '--input', str(package / 'examples/discovery.demo.json'))
        print('Completed synthetic discovery import:', json.dumps(discovery, sort_keys=True))
        replay = run('discover', '--input', str(package / 'examples/discovery.demo.json'))
        print('Same discovery import again:', json.dumps(replay, sort_keys=True))
        deadline = time.monotonic() + 45
        while True:
            # Each CLI call opens a fresh process against the same SQLite state.
            receipt = run('tick')
            print('Fresh-process tick:', json.dumps(receipt, sort_keys=True))
            if receipt['state'] != 'running':
                break
            wait = max(0.05, receipt.get('wait_seconds', 0))
            if time.monotonic() + wait > deadline:
                raise RuntimeError('Demo did not finish within its 45-second local limit.')
            time.sleep(wait)
        summary = run('status')
        assert summary['state'] == 'complete', summary
        assert summary['pages'] == 3 and summary['unique_documents'] == 2, summary
        assert summary['requests'] == 4, summary
        assert run('tick') == receipt, 'Terminal replay changed its receipt'
        print('Final summary:', json.dumps(summary, indent=2, sort_keys=True))
        print('Final receipt replay matched; 3 URLs, 2 unique bodies, 4 requests including robots.')
    print('Temporary synthetic state removed. No live source or n8n engine was used.')


if __name__ == '__main__':
    main()
