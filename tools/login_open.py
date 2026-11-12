import json
import urllib.request

o = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def post(path, body=None, timeout=180):
    req = urllib.request.Request(
        'http://127.0.0.1:8765' + path,
        data=json.dumps(body or {}).encode(),
        headers={'Content-Type': 'application/json'},
    )
    try:
        return json.loads(o.open(req, timeout=timeout).read().decode())
    except urllib.error.HTTPError as exc:
        return json.loads(exc.read().decode())


print(json.dumps(post('/api/browser/login'), ensure_ascii=False))
