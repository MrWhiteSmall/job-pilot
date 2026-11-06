import json
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / 'data' / 'job_pilot.sqlite3'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT id, data, score, status FROM jobs ORDER BY id DESC").fetchall()
for row in rows[:3]:
    data = json.loads(row['data'])
    print(row['id'], row['status'], data.get('company'), data.get('title'))
    print(json.dumps({k: v for k, v in data.items() if k in ('draft', 'salary', 'company_size', 'city')}, ensure_ascii=False, indent=1))
    print('---')
print('automation:', dict(conn.execute('SELECT * FROM automation').fetchone()))
print('statuses:', [tuple(x) for x in conn.execute('SELECT status, COUNT(*) FROM jobs GROUP BY status')])
