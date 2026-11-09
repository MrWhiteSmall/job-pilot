"""List everything already contacted, to eyeball false positives."""

import json
import sqlite3
from collections import Counter
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / 'data' / 'job_pilot.sqlite3'
conn = sqlite3.connect(str(DB))
rows = conn.execute(
    "SELECT j.id, j.data, a.mode, a.outcome FROM jobs j "
    "LEFT JOIN attempts a ON a.job_id=j.id AND a.mode='live' "
    "WHERE j.status IN ('sent','uncertain','blocked') ORDER BY j.id").fetchall()

suspect = []
for jid, data, mode, outcome in rows:
    job = json.loads(data)
    title = str(job.get('title', ''))
    company = str(job.get('company', ''))
    print(f'{jid:>4} {outcome or "-":<9} {title[:34]:<34} @ {company[:20]:<20} {job.get("city","")[:12]:<12} {job.get("salary","")}')

print('\n公司重复触达：')
for company, count in Counter(json.loads(d)[ 'company'] for _, d, _, _ in rows).most_common(5):
    print(' ', company, count)
