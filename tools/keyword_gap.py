import json
import re
import sqlite3
from collections import Counter

DB = r'D:\DesktopCode\job-pilot\data\job_pilot.sqlite3'
c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row

rows = c.execute("SELECT id, data, status, score, reason FROM jobs WHERE status='rejected'").fetchall()
print('rejected:', len(rows))
pat = re.compile(r'应用工程师|后端|服务端|应用开发')
hits = []
for r in rows:
    d = json.loads(r['data'])
    title = d.get('title') or ''
    if pat.search(title):
        hits.append((r['id'], title, d.get('company'), d.get('salary'), (r['reason'] or '')[:20]))
print('被拒里含 应用工程师/后端/服务端/应用开发 的:', len(hits))
for h in hits[:25]:
    print('  ', h[0], '|', h[1][:30], '|', (h[2] or '')[:14], '|', h[3], '|', h[4])

print('--- 被拒原因分布（当前）')
for k, v in Counter((r['reason'] or '')[:24] for r in rows).most_common(12):
    print('  ', v, k)
