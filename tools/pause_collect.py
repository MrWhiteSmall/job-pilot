import json
import urllib.request

o = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(path, body=None, timeout=120):
    req = urllib.request.Request(
        'http://127.0.0.1:8765' + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type': 'application/json'},
        method='POST' if body is not None else 'GET',
    )
    return json.loads(o.open(req, timeout=timeout).read().decode())


cfg = call('/api/state')['automation']
cfg['auto_collect'] = False
print('set ->', json.dumps(call('/api/automation', cfg), ensure_ascii=False))
print('stats ->', json.dumps(call('/api/state')['stats'], ensure_ascii=False))
