import json
import sqlite3
from collections import Counter

db = sqlite3.connect(r'D:\DesktopCode\job-pilot\data\job_pilot.sqlite3')
db.row_factory = sqlite3.Row
stats = Counter()
rows = []
for row in db.execute("SELECT * FROM jobs WHERE status='rejected'").fetchall():
    if not (row['reason'] or '').startswith('命中黑名单'):
        continue
    data = json.loads(row['data'])
    company = str(data.get('company') or '')
    if not any(x in company for x in ('某中型', '某小型', '某知名')):
        continue
    stats[(company, str(data.get('company_size') or '-'))] += 1
    rows.append((row['id'], data.get('title'), company, data.get('company_size'), data.get('salary'), data.get('city')))
for key, count in stats.most_common(12):
    print(count, key)
print('total', len(rows))
for item in rows[:12]:
    print(item)
