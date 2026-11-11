import json
import urllib.request

o = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(path, body=None, timeout=1800):
    req = urllib.request.Request(
        'http://127.0.0.1:8765' + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type': 'application/json'},
        method='POST' if body is not None else 'GET',
    )
    return json.loads(o.open(req, timeout=timeout).read().decode())


NEW = ['前沿部署', '前沿部署工程师', 'FDE', 'Forward Deployed']

rules = dict(call('/api/state')['rules'])
rules['dedupe_companies'] = False
titles = list(rules.get('titles') or [])
collect = list(rules.get('collect_titles') or [])
for word in NEW:
    if word not in titles:
        titles.append(word)
    if word not in collect:
        collect.append(word)
rules['titles'] = titles
rules['collect_titles'] = collect
call('/api/rules', rules)

state = call('/api/state')
print('dedupe_companies', state['rules'].get('dedupe_companies'))
print('titles', len(state['rules']['titles']), state['rules']['titles'][-6:])
print('collect_titles', len(state['rules']['collect_titles']))

for _ in range(60):
    if not call('/api/state')['stats']['pending']:
        break
    call('/api/analyze', {})

auto = dict(call('/api/state')['automation'])
auto['enabled'] = True
call('/api/automation', auto)
print('stats', json.dumps(call('/api/state')['stats'], ensure_ascii=False))
