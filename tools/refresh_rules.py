"""Refresh matching rules: wider skill coverage, senior roles excluded, more query terms."""
import json
import urllib.request

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
rules['titles'] = ['AI应用', '大模型应用', 'Agent', '智能体', 'AI工程师', 'LLM', '全栈', '大模型', 'RAG', 'AI开发']
rules['collect_titles'] = ['AI应用开发', '大模型应用', 'Agent开发', '智能体开发', 'AI Agent',
                           'LLM应用', 'RAG', '全栈工程师', '大模型开发', 'AI平台']
rules['exclude_titles'] = ['产品经理', '项目经理', '销售', '运营', '讲师', '顾问', '售前', '市场',
                           '商务', '实施', '交付', '主管', '总监', '负责人', '架构师', '合伙人', 'CTO']
rules['skills'] = ['Python', 'LangGraph', 'Agent', 'MCP', 'Redis', 'Milvus', 'Elasticsearch',
                   'RAG', 'LLM', 'Prompt', '大模型', '微服务', 'Docker', 'Kubernetes', 'MySQL',
                   'PostgreSQL', 'FastAPI', 'Flask', 'Django', 'TypeScript', 'React', 'Vue',
                   'Java', 'Go', 'NLP', '多模态', 'PyTorch', '向量数据库', '检索', '推荐系统']
rules['greeting'] = ''
print(json.dumps(call('/api/rules', rules), ensure_ascii=False)[:120])
print('collect:', json.dumps(call('/api/browser/collect', {}, timeout=1800), ensure_ascii=False)[:160])
call('/api/analyze', {}, timeout=1200)
state = call('/api/state')
from collections import Counter
print(Counter(j['status'] for j in state['jobs']))
print(json.dumps(state['stats'], ensure_ascii=False))
