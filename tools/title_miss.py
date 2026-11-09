import json
import sqlite3

DB = r'D:\DesktopCode\job-pilot\data\job_pilot.sqlite3'
c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row
rows = c.execute(
    "SELECT id, data, reason FROM jobs WHERE status='rejected' AND reason LIKE '%职位不符合规则%' ORDER BY id"
).fetchall()
print('职位不符合规则:', len(rows))
for r in rows:
    d = json.loads(r['data'])
    print(' ', r['id'], '|', (d.get('title') or '')[:34], '|', (d.get('company') or '')[:12], '|', d.get('salary'))
