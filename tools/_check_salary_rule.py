import json
import sqlite3
from collections import Counter

c = sqlite3.connect(r'D:\DesktopCode\job-pilot\data\job_pilot.sqlite3')
c.row_factory = sqlite3.Row
rows = list(c.execute("SELECT * FROM jobs WHERE status='rejected'"))
print(Counter((r['reason'] or '').split('：')[0].split('；')[0] for r in rows).most_common(12))
for r in rows:
    d = json.loads(r['data'])
    salary = str(d.get('salary') or '')
    if salary.startswith(('18-30', '15-25', '15-24', '17-18', '18-25')):
        print(r['id'], d['title'][:18], salary, '->', (r['reason'] or '')[:60])
