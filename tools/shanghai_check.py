import json
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
conn = sqlite3.connect(str(BASE / 'data' / 'job_pilot.sqlite3'))
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT id, data, status, score FROM jobs ORDER BY id DESC LIMIT 60").fetchall()
sh = []
for row in rows:
    job = json.loads(row['data'])
    city = str(job.get('city') or '')
    if '上海' in city:
        sh.append((row['id'], row['status'], job.get('title'), job.get('company'), city))
print('recent-60 shanghai:', len(sh))
for x in sh[:15]:
    print(' ', x)
total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
cnt = 0
for row in conn.execute("SELECT data FROM jobs"):
    if '上海' in str(json.loads(row['data']).get('city') or ''):
        cnt += 1
print('total jobs', total, 'shanghai', cnt)
