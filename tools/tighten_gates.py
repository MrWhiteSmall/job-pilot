"""Tighten quality gates: require skill evidence, block placeholder companies."""
import json
import urllib.request
from collections import Counter

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(path, body=None, timeout=900):
    req = urllib.request.Request(
        'http://127.0.0.1:8765' + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type': 'application/json'},
        method='POST' if body is not None else 'GET',
    )
    return json.loads(OPENER.open(req, timeout=timeout).read().decode())


rules = dict(call('/api/state')['rules'])
for name in ('某中型', '某小型', '某知名'):
    if name not in rules['blacklist']:
        rules['blacklist'].append(name)
call('/api/rules', rules)
call('/api/analyze', {})
state = call('/api/state')
print(Counter(j['status'] for j in state['jobs']))
top = [j for j in state['jobs'] if j['status'] == 'matched']
print('matched scores', Counter(j['score'] for j in top).most_common(6))
print(json.dumps(call('/api/automation', {'enabled': True, 'mode': 'live', 'daily_limit': 150,
                                          'interval_seconds': 70, 'min_score': 55,
                                          'auto_approve': True, 'auto_collect': True}), ensure_ascii=False))
