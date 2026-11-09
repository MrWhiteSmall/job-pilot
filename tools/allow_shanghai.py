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
cities = list(rules.get('cities') or [])
if '上海' not in cities:
    cities.append('上海')
payload = {**rules, 'cities': cities}
call('/api/rules', payload)
state = call('/api/state')
print('cities ->', state['rules']['cities'])
print('districts ->', state['rules'].get('districts'))
print('stats', json.dumps(state['stats'], ensure_ascii=False))
