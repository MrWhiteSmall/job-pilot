import json
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from engine import JobEngine  # noqa: E402

e = JobEngine(str(BASE / 'data' / 'job_pilot.sqlite3'))
rules = e.get_rules()['data']
conn = sqlite3.connect(str(BASE / 'data' / 'job_pilot.sqlite3'))
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT id, data, reason FROM jobs WHERE status='rejected' AND reason LIKE '%外资%'").fetchall()
print('blocked-large', len(rows))
for row in rows:
    job = json.loads(row['data'])
    hit = JobEngine._foreign_company(job, rules.get('foreign_whitelist'))
    print(row['id'], job.get('company'), '|', job.get('company_size'), '| hit', hit)
