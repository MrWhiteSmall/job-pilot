import json
import urllib.error
import urllib.request

o = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(path, body=None, timeout=300):
    req = urllib.request.Request(
        'http://127.0.0.1:8765' + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type': 'application/json'},
        method='POST' if body is not None else 'GET',
    )
    try:
        return json.loads(o.open(req, timeout=timeout).read().decode())
    except urllib.error.HTTPError as exc:
        return {'http_status': exc.code, 'body': exc.read().decode()[:400]}


payload = {
    'enabled': True,
    'mode': 'live',
    'daily_limit': 150,
    'interval_seconds': 60,
    'min_score': 55,
    'auto_approve': True,
    'auto_collect': True,
}
print('enable ->', json.dumps(call('/api/automation', payload), ensure_ascii=False)[:500])
state = call('/api/state')
print('automation ->', json.dumps(state['automation'], ensure_ascii=False))
print('stats ->', json.dumps(state['stats'], ensure_ascii=False))
