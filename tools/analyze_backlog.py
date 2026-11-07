"""Analyze the whole backlog in batches, then report the pipeline state."""
import json
import time
import urllib.request
from collections import Counter

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(path, body=None, timeout=600):
    req = urllib.request.Request(
        'http://127.0.0.1:8765' + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type': 'application/json'},
        method='POST' if body is not None else 'GET',
    )
    return json.loads(OPENER.open(req, timeout=timeout).read().decode())


for round_no in range(14):
    state = call('/api/state', timeout=120)
    if state['stats']['pending'] == 0:
        break
    call('/api/analyze', {})
    print(round_no, 'pending', state['stats']['pending'], flush=True)
    time.sleep(1)

state = call('/api/state', timeout=120)
print(Counter(j['status'] for j in state['jobs']))
print(json.dumps(state['stats'], ensure_ascii=False))
print(Counter((j.get('reason') or '').split('；')[0] for j in state['jobs'] if j['status'] == 'rejected').most_common(6))
