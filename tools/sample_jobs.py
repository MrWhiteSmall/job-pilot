import json
import sqlite3

conn = sqlite3.connect(r'D:\DesktopCode\job-pilot\data\job_pilot.sqlite3')
conn.row_factory = sqlite3.Row
for job_id in (66, 2060):
    row = conn.execute('SELECT id, data FROM jobs WHERE id=?', (job_id,)).fetchone()
    if not row:
        continue
    job = json.loads(row['data'])
    print(row['id'], job.get('company'), job.get('company_size'), job.get('url'))
rows = conn.execute(
    "SELECT id, data FROM jobs WHERE status IN ('matched','sent') ORDER BY id DESC LIMIT 5"
).fetchall()
for row in rows:
    job = json.loads(row['data'])
    print('cand', row['id'], job.get('company'), job.get('company_size'), job.get('url'))
