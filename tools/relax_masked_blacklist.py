"""Drop the over-broad 某中型/某小型 blacklist entries so real SMEs can be scored."""
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
rules['blacklist'] = [x for x in rules.get('blacklist', []) if x not in ('某中型', '某小型')]
print('blacklist size', len(rules['blacklist']))
call('/api/rules', rules)
for _ in range(14):
    state = call('/api/state')
    if state['stats']['pending'] == 0:
        break
    call('/api/analyze', {})
state = call('/api/state')
print(Counter(j['status'] for j in state['jobs']))
print(json.dumps(state['stats'], ensure_ascii=False))
