import json
import urllib.request

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
BASE = 'http://127.0.0.1:8765'


def call(path, body=None):
    data = json.dumps(body).encode('utf-8') if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method='POST' if data else 'GET',
                                     headers={'Content-Type': 'application/json'})
    with OPENER.open(request, timeout=600) as response:
        return json.loads(response.read().decode('utf-8'))


rules = call('/api/state')['rules']
rules['collect_titles'] = ['AI应用', '大模型', 'Agent', '智能体', '全栈', 'Python']
print(json.dumps(call('/api/rules', rules)['rules'].get('collect_titles'), ensure_ascii=False))
print(json.dumps(call('/api/automation', {'enabled': True, 'mode': 'live', 'daily_limit': 150,
                                          'interval_seconds': 70, 'min_score': 40,
                                          'auto_approve': True, 'auto_collect': True}), ensure_ascii=False))
