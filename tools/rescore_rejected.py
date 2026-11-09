"""Re-score every rejected job with the current rules and report (or apply) recoveries.

    python tools/rescore_rejected.py            # dry run: just report
    python tools/rescore_rejected.py --apply    # set recovered rows back to `new`
"""

import json
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from engine import JobEngine  # noqa: E402

APPLY = '--apply' in sys.argv
DB = BASE / 'data' / 'job_pilot.sqlite3'
engine = JobEngine(str(DB))
rules = engine.get_rules()['data']
resume = engine.get_profile().get('resume_text', '')

conn = sqlite3.connect(str(DB))
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT id, data, reason FROM jobs WHERE status='rejected'").fetchall()

recovered, old_reasons = [], {}
for row in rows:
    job = json.loads(row['data'])
    score, reason = engine.match_job(job, resume, rules)
    if score >= 0:
        recovered.append((row['id'], job.get('title'), job.get('company'), score, row['reason']))
        old_reasons[row['reason']] = old_reasons.get(row['reason'], 0) + 1

print(f'rejected={len(rows)}  recovered={len(recovered)}')
for old, count in sorted(old_reasons.items(), key=lambda kv: -kv[1]):
    print(f'  {count:>4}  原拒绝理由：{old}')
for row in recovered[:25]:
    print('   +', row)

if APPLY and recovered:
    with engine._connect() as db:
        for jid, *_ in recovered:
            db.execute("UPDATE jobs SET status='new', score=NULL, reason=NULL, analysis=NULL, updated_at=datetime('now') WHERE id=?", (jid,))
        db.execute("INSERT INTO logs(job_id, event, detail) VALUES(NULL, 'rescore', ?)",
                   (f'规则修正后重新纳入 {len(recovered)} 条岗位',))
    print(f'applied: {len(recovered)} 条改回 new，等待 /api/analyze 重新评分')
