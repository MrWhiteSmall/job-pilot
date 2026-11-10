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


state = call('/api/state')
rules = dict(state['rules'])
extra = ['AI应用架构', 'AI平台开发', 'Prompt工程师', '大模型工程师', 'RAG工程师',
         '智能体平台', 'AI中台', 'LLM工程师', 'Agent平台', 'AI系统']
titles = list(rules.get('collect_titles') or [])
for word in extra:
    if word not in titles:
        titles.append(word)
rules['collect_titles'] = titles
print('collect_titles', len(titles))
call('/api/rules', rules)
state = call('/api/state')
print('pending', state['stats']['pending'])

for _ in range(20):
    if not call('/api/state')['stats']['pending']:
        break
    call('/api/analyze', {})

auto = dict(call('/api/state')['automation'])
auto['auto_collect'] = True
auto['enabled'] = True
print('automation ->', json.dumps(call('/api/automation', auto), ensure_ascii=False))
print('stats ->', json.dumps(call('/api/state')['stats'], ensure_ascii=False))
