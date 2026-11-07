"""Update screening rules, then report how jobs classify under them."""
import json
import urllib.request
from collections import Counter

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(path, body=None, timeout=900):
    req = urllib.request.Request(
        'http://127.0.0.1:8765' + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type': 'application/json'},
        method='POST' if body is not None else 'GET',
    )
    return json.loads(OPENER.open(req, timeout=timeout).read().decode())


state = call('/api/state')
rules = dict(state['rules'])
rules['titles'] = ['AI应用', '大模型应用', 'Agent', '智能体', 'AI工程师', 'LLM', '全栈']
print('rules:', json.dumps({k: rules[k] for k in ('titles', 'min_salary', 'max_salary', 'company_min', 'company_max')}, ensure_ascii=False))
call('/api/rules', rules)
call('/api/analyze', {})
state = call('/api/state')
print(Counter(j['status'] for j in state['jobs']))
print(Counter((j.get('reason') or '').split('；')[0] for j in state['jobs'] if j['status'] == 'rejected').most_common(6))
print(json.dumps(state['stats'], ensure_ascii=False))
