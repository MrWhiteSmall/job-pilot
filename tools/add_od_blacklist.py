"""把 OD/外包渠道补进黑名单，只重算受影响的岗位，不触发全库作废。"""
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DB = os.getenv('JOB_PILOT_DB') or str(ROOT / 'data' / 'job_pilot.sqlite3')

EXTRA = ['咏鹭科技', '咏鹭', 'od岗', 'od岗位', '外包岗']

from engine import JobEngine  # noqa: E402

db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row
row = db.execute('SELECT data FROM rules WHERE id=1').fetchone()
rules = json.loads(row['data'])
blacklist = rules.setdefault('blacklist', [])
added = [name for name in EXTRA if name not in blacklist]
blacklist.extend(added)
db.execute('UPDATE rules SET data=? WHERE id=1', (json.dumps(rules, ensure_ascii=False),))
db.commit()
print('blacklist added:', added, 'total', len(blacklist))

engine = JobEngine(DB)
resume = engine.get_profile()['resume_text']
current = engine.get_rules()['data']
terminal = {'sent', 'blocked', 'uncertain', 'pending'}
changed = []
for r in db.execute('SELECT id, status, data, score FROM jobs').fetchall():
    data = json.loads(r['data'])
    text = f"{data.get('title', '')}{data.get('company', '')}".lower()
    if not any(name.lower() in text for name in EXTRA):
        continue
    if r['status'] in terminal:
        changed.append((r['id'], r['status'], 'terminal'))
        continue
    score, reason = JobEngine.match_job(data, resume, current)
    if score < 0:
        db.execute('UPDATE jobs SET status=?, score=?, reason=? WHERE id=?', ('rejected', score, reason, r['id']))
        changed.append((r['id'], 'rejected', reason))
db.commit()
for item in changed:
    print(item)
print('affected', len(changed))
