import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine import JobEngine

BASE = Path(__file__).resolve().parent.parent
e = JobEngine(str(BASE / 'data' / 'job_pilot.sqlite3'))
rules = e.get_rules()['data']
resume = e.get_profile()['resume_text']
contacted = e.contacted_companies()

with e._connect() as conn:
    rows = conn.execute("SELECT * FROM jobs WHERE status='matched' ORDER BY score DESC").fetchall()
fresh, stale = [], []
for r in rows:
    job = dict(r)
    data = json.loads(job['data'])
    if e._company_key(data.get('company')) in contacted:
        stale.append(job)
    else:
        fresh.append(job)
print('matched', len(rows), 'fresh(company not contacted)', len(fresh), 'blocked_by_company_dedupe', len(stale))
print('fresh scores:', sorted([int(j['score'] or 0) for j in fresh], reverse=True)[:20])
for j in fresh[:12]:
    d = json.loads(j['data'])
    print(' ', j['id'], int(j['score'] or 0), (d.get('company') or '')[:18], (d.get('title') or '')[:26], (d.get('city') or '')[:12], (d.get('salary') or '-')[:10])
print('cities in rules:', rules.get('cities'))
