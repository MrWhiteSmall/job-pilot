import collections
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine import JobEngine

BASE = Path(__file__).resolve().parent.parent
o = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(path, body=None, timeout=1800):
    req = urllib.request.Request(
        'http://127.0.0.1:8765' + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type': 'application/json'},
        method='POST' if body is not None else 'GET',
    )
    return json.loads(o.open(req, timeout=timeout).read().decode())


state = call('/api/state')
rules = dict(state['rules'])
rules['cities'] = ['杭州']
call('/api/rules', rules)
print('cities ->', call('/api/state')['rules']['cities'])

for _ in range(60):
    if not call('/api/state')['stats']['pending']:
        break
    call('/api/analyze', {})
print('stats', json.dumps(call('/api/state')['stats'], ensure_ascii=False))

e = JobEngine(str(BASE / 'data' / 'job_pilot.sqlite3'))
rules = e.get_rules()['data']
resume = e.get_profile()['resume_text']
contacted = e.contacted_companies()

with e._connect() as conn:
    rows = [dict(r) for r in conn.execute("SELECT * FROM jobs").fetchall()]

hz = []
for r in rows:
    data = json.loads(r['data'])
    if '杭州' in str(data.get('city') or ''):
        r['data'] = data
        hz.append(r)

print('\n=== 杭州岗位 ===')
print('total', len(hz))
print('status', collections.Counter(r['status'] for r in hz).most_common())

reasons = collections.Counter()
for r in hz:
    if r['status'] == 'rejected' and r['reason']:
        reasons[r['reason'].split('：')[0].split('（')[0][:30]] += 1
print('\n拒绝原因:')
for k, n in reasons.most_common(12):
    print(f'  {n:4}  {k}')

# 公司级去重：本来合格但公司已聊过
blocked_company = [r for r in hz if e._company_key(r['data'].get('company')) in contacted]
print('\n公司已在 30 天内沟通过的杭州岗位:', len(blocked_company))

# 疑似误杀：标题像研发，但被职位不符合/非研发岗拒
dev_words = re.compile(r'开发|工程师|研发')
suspect = [r for r in hz if r['status'] == 'rejected' and dev_words.search(str(r['data'].get('title') or ''))
          and any(x in str(r['reason'] or '') for x in ('职位不符合', '职位方向不符'))]
print('\n标题像研发却被拒的:', len(suspect))
for r in suspect[:12]:
    print('  ', r['id'], str(r['data'].get('title'))[:30], '|', str(r['reason'])[:44])

# 千人以上非外资
foreign = [r for r in hz if r['status'] == 'rejected' and '千人以上' in str(r['reason'] or '')]
print('\n千人以上被判非外资:', len(foreign))
for r in foreign[:8]:
    print('  ', r['id'], str(r['data'].get('company'))[:22], str(r['data'].get('company_size'))[:12], str(r['data'].get('title'))[:22])

# 小公司无融资
tiny = [r for r in hz if r['status'] == 'rejected' and '0-20 人' in str(r['reason'] or '')]
print('\n0-20 人无融资被拒:', len(tiny))
for r in tiny[:8]:
    print('  ', r['id'], str(r['data'].get('company'))[:22], str(r['data'].get('financing'))[:12], str(r['data'].get('title'))[:22])
