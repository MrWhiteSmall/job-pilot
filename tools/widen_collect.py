"""Broaden collection keywords and pull a fresh batch of postings."""
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


rules = dict(call('/api/state')['rules'])
rules['collect_titles'] = ['AI应用开发', '大模型应用', 'Agent开发', '智能体开发', 'AI Agent',
                           'LLM应用', 'RAG', '全栈工程师']
print('collect_titles:', rules['collect_titles'])
call('/api/rules', rules)
print('collect:', json.dumps(call('/api/browser/collect', {}, timeout=1800), ensure_ascii=False)[:200])
state = call('/api/state')
print(Counter(j['status'] for j in state['jobs']))
print(json.dumps(state['stats'], ensure_ascii=False))
