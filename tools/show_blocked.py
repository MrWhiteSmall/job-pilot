import json
import sqlite3

conn = sqlite3.connect(r'D:\DesktopCode\job-pilot\data\job_pilot.sqlite3')
conn.row_factory = sqlite3.Row
print('--- recent logs')
for r in conn.execute('SELECT id, event, detail, created_at FROM logs ORDER BY id DESC LIMIT 10'):
    print(r['id'], r['created_at'][11:19], r['event'], '|', (r['detail'] or '')[:90])

print('--- blocked jobs')
rows = conn.execute("SELECT id, data, updated_at FROM jobs WHERE status='blocked' ORDER BY id DESC LIMIT 8").fetchall()
for r in rows:
    job = json.loads(r['data'])
    print(r['id'], r['updated_at'][:19], job.get('title'), '@', job.get('company'), job.get('url'))
