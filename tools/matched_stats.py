import collections
import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
conn = sqlite3.connect(str(BASE / 'data' / 'job_pilot.sqlite3'))
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT score, reason, data FROM jobs WHERE status='matched'").fetchall()
print('matched', len(rows), 'score>=55', sum(1 for r in rows if (r['score'] or 0) >= 55))
print('score histogram', sorted(collections.Counter(int(r['score'] or 0) for r in rows).items()))
full = [r for r in rows if '列表摘要' not in str(json.loads(r['data']).get('description') or '')]
print('full-jd matched', len(full))
cities = collections.Counter(str(json.loads(r['data']).get('city') or '').split('·')[0] for r in rows)
print('cities', dict(cities))
