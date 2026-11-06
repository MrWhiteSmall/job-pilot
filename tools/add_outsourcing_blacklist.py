import json
import urllib.request

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
BASE = 'http://127.0.0.1:8765'


def call(path, body=None):
    data = json.dumps(body).encode('utf-8') if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method='POST' if data else 'GET',
                                     headers={'Content-Type': 'application/json'})
    with OPENER.open(request, timeout=120) as response:
        return json.loads(response.read().decode('utf-8'))


extra = ['科锐国际', '科锐', '任仕达', '埃摩森', '米高蒲志', '猎聘', '智联招聘', '前程无忧',
         '中智', '上海外服', 'FESCO', 'Adecco', 'Manpower', '人力外包', '人才外包', '劳务派遣',
         '猎头', '第三方外包', '外包驻场']
rules = call('/api/state')['rules']
current = rules.get('blacklist') or []
merged = current + [name for name in extra if name not in current]
rules['blacklist'] = merged
print('blacklist', len(merged))
print(json.dumps(call('/api/rules', rules), ensure_ascii=False))
print(json.dumps(call('/api/analyze', {}), ensure_ascii=False)[:300])
