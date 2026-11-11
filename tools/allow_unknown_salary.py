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


rules = dict(call('/api/state')['rules'])
rules['allow_unknown_salary'] = True
call('/api/rules', rules)
print('allow_unknown_salary', call('/api/state')['rules'].get('allow_unknown_salary'))
