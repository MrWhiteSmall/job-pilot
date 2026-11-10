import json
import urllib.request

o = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(path, body=None, timeout=1200):
    req = urllib.request.Request(
        'http://127.0.0.1:8765' + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type': 'application/json'},
        method='POST' if body is not None else 'GET',
    )
    return json.loads(o.open(req, timeout=timeout).read().decode())


state = call('/api/state')
print('before:', json.dumps(state['rules'].get('collect_titles'), ensure_ascii=False))
rules = dict(state['rules'])
titles = list(rules.get('collect_titles') or [])
for word in ('平台开发', '平台开发工程师', 'Python后端', 'Python后端开发', '后端开发工程师'):
    if word not in titles:
        titles.append(word)
rules['collect_titles'] = titles
call('/api/rules', rules)
state = call('/api/state')
print('after :', len(state['rules']['collect_titles']), json.dumps(state['rules']['collect_titles'], ensure_ascii=False))
print('pending', state['stats']['pending'])
for _ in range(30):
    if not call('/api/state')['stats']['pending']:
        break
    call('/api/analyze', {})
print('stats', json.dumps(call('/api/state')['stats'], ensure_ascii=False))
