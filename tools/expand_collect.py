import json
import urllib.request

o = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(path, body=None, timeout=300):
    req = urllib.request.Request(
        'http://127.0.0.1:8765' + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type': 'application/json'},
        method='POST' if body is not None else 'GET',
    )
    return json.loads(o.open(req, timeout=timeout).read().decode())


rules = call('/api/state')['rules']
collect = list(rules.get('collect_titles') or [])
for kw in ('后端开发', '服务端开发', 'Python开发', 'Java开发', '应用开发', 'Agent工程师'):
    if kw not in collect:
        collect.append(kw)
payload = {**rules, 'collect_titles': collect}
saved = call('/api/rules', payload)
print('collect_titles ->', call('/api/state')['rules']['collect_titles'])
print('titles ->', call('/api/state')['rules']['titles'])
