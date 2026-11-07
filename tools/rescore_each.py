"""Force a full re-score of every non-terminal job (used after rule-logic changes)."""
import json
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


state = call('/api/state')
ids = [j['id'] for j in state['jobs'] if j['status'] not in ('sent', 'blocked', 'uncertain', 'pending')]
print('rescoring', len(ids))
for jid in ids:
    try:
        call('/api/analyze', {'id': jid}, timeout=120)
    except Exception as exc:
        print('skip', jid, exc)

state = call('/api/state')
print(Counter(j['status'] for j in state['jobs']))
print(json.dumps(state['stats'], ensure_ascii=False))
reasons = Counter((j.get('reason') or '').split('；')[0].split('：')[0] for j in state['jobs'] if j['status'] == 'rejected')
for key, count in reasons.most_common(12):
    print(count, key)
