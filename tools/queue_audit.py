import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine import JobEngine

BASE = Path(__file__).resolve().parent.parent
e = JobEngine(str(BASE / 'data' / 'job_pilot.sqlite3'))
contacted = e.contacted_companies()
rules = e.get_rules()['data']

with e._connect() as conn:
    rows = [dict(r) for r in conn.execute("SELECT * FROM jobs").fetchall()]

hz, out = [], []
for r in rows:
    data = json.loads(r['data'])
    r['data'] = data
    if '杭州' in str(data.get('city') or ''):
        hz.append(r)
    else:
        out.append(r)

print('杭州', len(hz), '外地', len(out))
pending = [r for r in hz if r['status'] in ('matched', 'approved', 'new')]
blocked = [r for r in pending if e._company_key(r['data'].get('company')) in contacted]
print('未投的杭州岗位', len(pending), '其中公司已聊过（非首次沟通）', len(blocked))
print('可首次沟通的候选', len(pending) - len(blocked))
print('已沟通公司数（30 天窗口）', len(contacted))

q = e.queue(40, 'live')
print('当前队列（门槛 40）', len(q), '首条', q[0]['id'] if q else None)
print('其中分数分布', sorted([int(j['score'] or 0) for j in q])[:12])
