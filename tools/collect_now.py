import json, urllib.request
o = urllib.request.build_opener(urllib.request.ProxyHandler({}))
def post(p, b=None, t=600):
    r = urllib.request.Request('http://127.0.0.1:8765'+p, data=json.dumps(b or {}).encode(), headers={'Content-Type':'application/json'})
    return json.loads(o.open(r, timeout=t).read().decode())
for i in range(2):
    out = post('/api/browser/collect', {})
    print('collect', i+1, json.dumps(out, ensure_ascii=False)[:200])
print('analyze', json.dumps(post('/api/analyze', {}), ensure_ascii=False)[:120])
print('stats', json.dumps(post('/api/run', {}) if False else json.loads(o.open('http://127.0.0.1:8765/api/state', timeout=30).read().decode())['stats'], ensure_ascii=False))
