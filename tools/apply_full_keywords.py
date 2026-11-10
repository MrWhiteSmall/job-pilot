import json
import urllib.request

o = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(path, body=None, timeout=1800):
    req = urllib.request.Request(
        'http://127.0.0.1:8765' + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type': 'application/json'},
        method='POST' if body is not None else 'GET',
    )
    return json.loads(o.open(req, timeout=timeout).read().decode())


FULL = [
    'AI应用开发', '大模型应用', 'Agent开发', '智能体开发', 'AI Agent', 'LLM应用', 'RAG',
    '全栈工程师', '大模型开发', 'AI平台', '后端开发', '服务端开发', 'Python开发', 'Java开发',
    '应用开发', 'Agent工程师', 'AI应用架构', 'AI平台开发', 'Prompt工程师', '大模型工程师',
    'RAG工程师', '智能体平台', 'AI中台', 'LLM工程师', 'Agent平台', 'AI系统',
    '平台开发', '平台开发工程师', 'Python后端', 'Python后端开发', '后端开发工程师',
]

state = call('/api/state')
rules = dict(state['rules'])
rules['collect_titles'] = FULL
call('/api/rules', rules)
state = call('/api/state')
print('collect_titles', len(state['rules']['collect_titles']))
print('pending', state['stats']['pending'])
for _ in range(40):
    if not call('/api/state')['stats']['pending']:
        break
    call('/api/analyze', {})

auto = dict(call('/api/state')['automation'])
auto['enabled'] = True
call('/api/automation', auto)

print('collect start')
res = call('/api/browser/collect', {}, timeout=1800)
print('collect ->', json.dumps(res, ensure_ascii=False)[:300])
print('stats', json.dumps(call('/api/state')['stats'], ensure_ascii=False))
