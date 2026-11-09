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


cities = ['杭州', '上海', '宁波', '嘉兴', '绍兴', '南京', '苏州', '泰州']
state = call('/api/state')
rules = dict(state['rules'])
rules['cities'] = cities
call('/api/rules', rules)
state = call('/api/state')
print('cities ->', state['rules']['cities'])
print('automation ->', json.dumps(state['automation'], ensure_ascii=False))
print('stats ->', json.dumps(state['stats'], ensure_ascii=False))
