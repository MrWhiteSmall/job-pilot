import json
import re
import sqlite3
from collections import Counter

db = sqlite3.connect(r'D:\DesktopCode\job-pilot\data\job_pilot.sqlite3')
db.row_factory = sqlite3.Row
rules = json.loads(db.execute('SELECT data FROM rules ORDER BY id DESC LIMIT 1').fetchone()['data'])
blacklist = rules.get('blacklist', [])
terms = Counter()
odd = []
for row in db.execute("SELECT * FROM jobs WHERE status='rejected'").fetchall():
    if not (row['reason'] or '').startswith('命中黑名单'):
        continue
    data = json.loads(row['data'])
    text = (str(data.get('title') or '') + ' ' + str(data.get('company') or '')).lower()
    hits = [x for x in blacklist if x.lower() in text]
    for hit in hits:
        terms[hit] += 1
    if any(len(h) <= 2 for h in hits):
        odd.append((row['id'], data.get('company'), hits))
print(terms.most_common(20))
print('short-term hits:', len(odd))
for item in odd[:10]:
    print(item)
