import sqlite3
from pathlib import Path

conn = sqlite3.connect(str(Path(__file__).resolve().parent.parent / 'data' / 'job_pilot.sqlite3'))
conn.row_factory = sqlite3.Row
rows = conn.execute('SELECT id, job_id, mode, outcome, created_at, substr(detail,1,50) AS d FROM attempts ORDER BY id DESC LIMIT 8').fetchall()
for r in rows:
    print(r['id'], r['job_id'], r['mode'], r['outcome'], r['created_at'], r['d'])
