import json
import urllib.request

o = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(path, body=None, timeout=900):
    req = urllib.request.Request(
        'http://127.0.0.1:8765' + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type': 'application/json'},
        method='POST' if body is not None else 'GET',
    )
    return json.loads(o.open(req, timeout=timeout).read().decode())


for i in range(40):
    before = call('/api/state')['stats']['pending']
    if not before:
        break
    call('/api/analyze', {})
    after = call('/api/state')['stats']['pending']
    print('round', i, before, '->', after)
state = call('/api/state')
print('stats', json.dumps(state['stats'], ensure_ascii=False))
